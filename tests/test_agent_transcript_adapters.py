"""Synthetic contract tests for the three private-history adapters."""
import json
import sys
from pathlib import Path

import pytest


CORPUS = Path(__file__).resolve().parents[1] / "utils" / "corpus"
sys.path.insert(0, str(CORPUS))

import agy_transcript_adapter as agy  # noqa: E402
import codex_transcript_adapter as codex  # noqa: E402
import normalized_transcript as normalized  # noqa: E402
import zcode_transcript_adapter as zcode  # noqa: E402


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _codex_rows(call_id="call-one"):
    return [
        {"timestamp": "2026-01-01T00:00:00Z", "type": "session_meta",
         "payload": {"id": "codex-session"}},
        {"timestamp": "2026-01-01T00:00:01Z", "type": "response_item",
         "payload": {"type": "message", "role": "user",
                     "content": [{"type": "input_text", "text": "inspect alpha"}]}},
        {"timestamp": "2026-01-01T00:00:02Z", "type": "response_item",
         "payload": {"type": "function_call", "call_id": call_id,
                     "name": "exec_command",
                     "arguments": json.dumps({"cmd": "git status --short"})}},
        {"timestamp": "2026-01-01T00:00:03Z", "type": "response_item",
         "payload": {"type": "custom_tool_call", "call_id": "call-two",
                     "name": "apply_patch", "input": "synthetic patch"}},
    ]


def test_codex_identity_survives_relocation_and_namespace_separates(tmp_path):
    first = tmp_path / "mount-a" / "sessions" / "day" / "session.jsonl"
    second = tmp_path / "mount-b" / "sessions" / "day" / "session.jsonl"
    _write_jsonl(first, _codex_rows())
    _write_jsonl(second, _codex_rows())

    meta_a, steps_a = codex.read_transcript(
        first, tmp_path / "mount-a" / "sessions", "workstation")
    meta_b, steps_b = codex.read_transcript(
        second, tmp_path / "mount-b" / "sessions", "workstation")
    meta_other, steps_other = codex.read_transcript(
        second, tmp_path / "mount-b" / "sessions", "other")

    assert meta_a.session_id == meta_b.session_id
    assert meta_a.transcript_sha256 == meta_b.transcript_sha256
    assert [step.source_event_id for step in steps_a if step.kind == "action"] == [
        step.source_event_id for step in steps_b if step.kind == "action"]
    assert meta_a.session_id != meta_other.session_id
    assert steps_a[1].source_event_id != steps_other[1].source_event_id


def test_codex_normalizes_order_aliases_and_freeform_input(tmp_path):
    source = tmp_path / "sessions"
    path = source / "session.jsonl"
    _write_jsonl(path, _codex_rows())

    meta, steps = codex.read_transcript(path, source, "fixture")

    assert isinstance(meta, normalized.NormalizedTranscript)
    assert meta.event_format_version == normalized.EVENT_FORMAT_VERSION
    assert meta.tool_alias_version == normalized.TOOL_ALIAS_VERSION
    assert all(isinstance(step, normalized.NormalizedStep) for step in steps)
    assert [step.kind for step in steps] == ["user", "action", "action"]
    assert [step.action_ordinal for step in steps[1:]] == [0, 1]
    assert [step.canonical_tool for step in steps[1:]] == ["Bash", "Edit"]
    assert steps[1].tool_input == {"cmd": "git status --short"}
    assert steps[2].tool_input == {"raw_input": "synthetic patch"}


def test_codex_rejects_duplicate_native_call_identity(tmp_path):
    source = tmp_path / "sessions"
    path = source / "session.jsonl"
    rows = _codex_rows()
    rows[-1]["payload"]["call_id"] = "call-one"
    _write_jsonl(path, rows)

    with pytest.raises(normalized.AdapterError, match="duplicate"):
        codex.read_transcript(path, source, "fixture")


def test_codex_source_rejects_duplicate_session_identity(tmp_path):
    source = tmp_path / "sessions"
    _write_jsonl(source / "one.jsonl", _codex_rows())
    _write_jsonl(source / "two.jsonl", _codex_rows("different-call"))

    with pytest.raises(normalized.AdapterError, match="duplicate Codex session"):
        list(codex.iter_transcripts(source, "fixture"))

    invalid = _codex_rows()
    invalid[0]["payload"]["id"] = ["not", "a", "session-id"]
    _write_jsonl(source / "one.jsonl", invalid)
    (source / "two.jsonl").unlink()
    with pytest.raises(normalized.AdapterError, match="must be a string"):
        list(codex.iter_transcripts(source, "fixture"))


def test_codex_identifies_legacy_search_calls_by_record_position(tmp_path):
    source = tmp_path / "sessions"
    path = source / "session.jsonl"
    rows = _codex_rows()[:1] + [
        {"timestamp": "2026-01-01T00:00:01Z", "type": "response_item",
         "payload": {"type": "tool_search_call", "arguments": {"query": "alpha"}}},
        {"timestamp": "2026-01-01T00:00:02Z", "type": "response_item",
         "payload": {"type": "web_search_call", "action": {"query": "beta"}}},
    ]
    _write_jsonl(path, rows)

    _, steps = codex.read_transcript(path, source, "fixture")
    assert [step.native_event_id for step in steps] == ["record:1", "record:2"]
    assert [step.source_tool for step in steps] == ["tool_search", "web_search"]
    assert [step.canonical_tool for step in steps] == [None, "WebSearch"]


def _agy_path(root, session="agy-session"):
    return root / session / ".system_generated" / "logs" / "transcript.jsonl"


def _agy_rows():
    return [
        {"type": "USER_INPUT", "step_index": 0,
         "created_at": "2026-01-01T00:00:00Z", "content": "inspect beta"},
        {"type": "PLANNER_RESPONSE", "step_index": 1,
         "created_at": "2026-01-01T00:00:01Z", "content": "",
         "tool_calls": [
             {"name": "view_file", "args": {"path": "src/beta.py"}},
             {"name": "unfamiliar_tool", "args": {"value": 1}},
         ]},
    ]


def test_agy_discovers_only_canonical_transcript_and_normalizes_calls(tmp_path):
    root = tmp_path / "brain"
    canonical = _agy_path(root)
    _write_jsonl(canonical, _agy_rows())
    _write_jsonl(canonical.with_name("transcript_full.jsonl"), _agy_rows())
    _write_jsonl(
        canonical.parent / "chunks" / "transcript" / "00000000.jsonl",
        _agy_rows())

    assert list(agy.iter_transcript_paths(root)) == [str(canonical)]
    [(meta, steps)] = list(agy.iter_transcripts(root, "fixture"))
    assert isinstance(meta, normalized.NormalizedTranscript)
    assert [step.kind for step in steps] == ["user", "action", "action"]
    assert [step.native_event_id for step in steps[1:]] == ["1:0", "1:1"]
    assert [step.action_ordinal for step in steps[1:]] == [0, 1]
    assert steps[1].canonical_tool == "Read"
    assert steps[2].canonical_tool is None
    assert steps[2].source_tool == "unfamiliar_tool"


def test_agy_identity_survives_relocation(tmp_path):
    root_a = tmp_path / "mount-a" / "brain"
    root_b = tmp_path / "mount-b" / "brain"
    path_a = _agy_path(root_a)
    path_b = _agy_path(root_b)
    _write_jsonl(path_a, _agy_rows())
    _write_jsonl(path_b, _agy_rows())

    meta_a, steps_a = agy.read_transcript(path_a, root_a, "fixture")
    meta_b, steps_b = agy.read_transcript(path_b, root_b, "fixture")
    assert meta_a.session_id == meta_b.session_id
    assert meta_a.transcript_sha256 == meta_b.transcript_sha256
    assert [s.source_event_id for s in steps_a if s.kind == "action"] == [
        s.source_event_id for s in steps_b if s.kind == "action"]


def test_agy_accepts_exact_duplicate_step_but_rejects_conflict(tmp_path):
    root = tmp_path / "brain"
    path = _agy_path(root)
    rows = _agy_rows()
    _write_jsonl(path, rows)
    original_meta, _ = agy.read_transcript(path, root, "fixture")

    rows.insert(1, dict(rows[0]))
    _write_jsonl(path, rows)

    duplicate_meta, steps = agy.read_transcript(path, root, "fixture")
    assert original_meta.transcript_sha256 == duplicate_meta.transcript_sha256
    assert [step.kind for step in steps] == ["user", "action", "action"]

    rows[1] = {**rows[1], "content": "conflicting request"}
    _write_jsonl(path, rows)

    with pytest.raises(normalized.AdapterError, match="conflicting Agy step_index"):
        agy.read_transcript(path, root, "fixture")


def _zcode_turn(session, record_id, timestamp, text):
    return {
        "id": record_id, "type": "turn_started", "sessionId": session,
        "turnId": "turn-one", "sequenceNumber": 0, "timestamp": timestamp,
        "payload": {"input": text},
    }


def _zcode_call(session, record_id, call_id, timestamp, tool="Read", sequence=0):
    return {
        "id": record_id, "type": "tool_call_scheduled", "sessionId": session,
        "turnId": "turn-one", "sequenceNumber": sequence, "timestamp": timestamp,
        "payload": {"toolCallId": call_id, "toolName": tool,
                    "input": {"file_path": "src/gamma.py"}},
    }


def test_zcode_groups_files_by_session_and_orders_by_timestamp(tmp_path):
    root = tmp_path / "cli"
    _write_jsonl(root / "later.jsonl", [
        _zcode_call("z-session", "record-a", "call-two",
                    "2026-01-01T00:00:02Z", "Mystery", sequence=2),
        {"id": "ledger", "type": "streaming_tool_ledger_updated",
         "sessionId": "z-session", "timestamp": "2026-01-01T00:00:04Z",
         "payload": {"toolCallId": "call-two", "status": "tool_result_committed"}},
    ])
    _write_jsonl(root / "earlier.jsonl", [
        _zcode_call("z-session", "record-z", "call-one",
                    "2026-01-01T00:00:02Z", sequence=1),
        _zcode_turn("z-session", "record-user", "2026-01-01T00:00:01Z",
                    "inspect gamma"),
    ])

    [(meta, steps)] = list(zcode.iter_transcripts(root, "fixture"))
    assert isinstance(meta, normalized.NormalizedTranscript)
    assert meta.source_relpaths == ("earlier.jsonl", "later.jsonl")
    assert [step.kind for step in steps] == ["user", "action", "action"]
    assert [step.native_event_id for step in steps[1:]] == ["call-one", "call-two"]
    assert [step.action_ordinal for step in steps[1:]] == [0, 1]
    assert steps[1].canonical_tool == "Read"
    assert steps[2].canonical_tool is None


def test_zcode_rejects_duplicate_tool_call_identity(tmp_path):
    root = tmp_path / "cli"
    _write_jsonl(root / "one.jsonl", [
        _zcode_call("z-session", "record-one", "same-call",
                    "2026-01-01T00:00:01Z"),
        _zcode_call("z-session", "record-two", "same-call",
                    "2026-01-01T00:00:02Z"),
    ])

    with pytest.raises(normalized.AdapterError, match="duplicate"):
        list(zcode.iter_transcripts(root, "fixture"))


def test_zcode_rejects_invalid_sequence_number(tmp_path):
    root = tmp_path / "cli"
    row = _zcode_call(
        "z-session", "record-one", "call-one", "2026-01-01T00:00:01Z")
    row["sequenceNumber"] = None
    _write_jsonl(root / "one.jsonl", [row])

    with pytest.raises(normalized.AdapterError, match="sequenceNumber"):
        list(zcode.iter_transcripts(root, "fixture"))


def test_zcode_identity_survives_relocation_and_json_key_order(tmp_path):
    root_a = tmp_path / "mount-a" / "cli"
    root_b = tmp_path / "mount-b" / "cli"
    row = _zcode_call(
        "z-session", "record-one", "call-one", "2026-01-01T00:00:01Z")
    reordered = {key: row[key] for key in reversed(row)}
    _write_jsonl(root_a / "events.jsonl", [row])
    _write_jsonl(root_b / "events.jsonl", [reordered])

    [(meta_a, steps_a)] = list(zcode.iter_transcripts(root_a, "fixture"))
    [(meta_b, steps_b)] = list(zcode.iter_transcripts(root_b, "fixture"))
    assert meta_a.session_id == meta_b.session_id
    assert meta_a.transcript_sha256 == meta_b.transcript_sha256
    assert steps_a[0].source_event_id == steps_b[0].source_event_id


def test_invalid_json_fails_with_source_line(tmp_path):
    source = tmp_path / "sessions"
    path = source / "broken.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_codex_rows()[0]) + "\nnot-json\n")

    with pytest.raises(normalized.AdapterError, match=r"broken.jsonl:2: invalid JSON"):
        codex.read_transcript(path, source, "fixture")


def test_codex_and_zcode_reject_missing_source_roots(tmp_path):
    missing = tmp_path / "not-mounted"
    for iterator in (codex.iter_transcripts, zcode.iter_transcripts):
        with pytest.raises(normalized.AdapterError, match="source root"):
            list(iterator(missing, "fixture"))
