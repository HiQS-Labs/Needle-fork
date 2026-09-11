"""Contract tests for aggregate cross-agent label-coverage auditing."""
from __future__ import annotations

import os
import sys

import pytest

CORPUS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "utils", "corpus")
sys.path.insert(0, CORPUS)

import audit_agent_label_coverage as audit  # noqa: E402
from normalized_transcript import (  # noqa: E402
    AdapterError, EVENT_FORMAT_VERSION, TOOL_ALIAS_VERSION, NormalizedStep,
    NormalizedTranscript,
)


def _meta(session: str = "session-digest") -> NormalizedTranscript:
    return NormalizedTranscript(
        event_format_version=EVENT_FORMAT_VERSION,
        tool_alias_version=TOOL_ALIAS_VERSION,
        source_agent="codex",
        source_namespace="test-codex",
        source_relpaths=("private.jsonl",),
        session_id=session,
        transcript_sha256="transcript-digest",
        native_session_id="private-native-session",
    )


def _action(ordinal: int, source_tool: str, canonical_tool: str | None,
            tool_input: dict) -> NormalizedStep:
    return NormalizedStep(
        kind="action",
        source_tool=source_tool,
        canonical_tool=canonical_tool,
        tool_input=tool_input,
        action_ordinal=ordinal,
        source_event_id=f"event-{ordinal}",
        native_event_id=f"native-{ordinal}",
    )


def test_audit_is_aggregate_deterministic_and_conserves_actions(monkeypatch):
    secret = "PRIVATE_COMMAND_VALUE"
    steps = [
        NormalizedStep(kind="user", text="PRIVATE_PROMPT_VALUE"),
        _action(0, "exec_command", "Bash", {"command": "pytest -q"}),
        _action(1, "unknown_private_tool", None, {"secret": secret}),
    ]
    monkeypatch.setattr(
        audit, "read_independent",
        lambda *_args: iter([((_meta(), steps), None, None)]),
    )

    first = audit.audit("codex", object(), "test-codex")
    second = audit.audit("codex", object(), "test-codex")
    encoded = audit.encode_result(first)

    assert encoded == audit.encode_result(second)
    assert first["actions"] == 2
    assert first["mapped_actions"] == 1
    assert first["labels"] == {"run_tests": 1, "unmapped": 1}
    assert first["eligible_pairs"] == 1
    assert secret not in encoded
    assert "PRIVATE_PROMPT_VALUE" not in encoded
    assert "private-native-session" not in encoded
    assert "native-0" not in encoded
    assert first["input_shapes"] == [
        {"source_tool": "exec_command", "keys": ["command"], "count": 1},
        {"source_tool": "unknown_private_tool", "keys": ["secret"], "count": 1},
    ]


def test_audit_rejects_zero_action_input(monkeypatch):
    monkeypatch.setattr(
        audit, "read_independent",
        lambda *_args: iter([
            ((_meta(), [NormalizedStep(kind="user", text="hello")]), None, None)
        ]),
    )
    with pytest.raises(audit.AuditError, match="zero actions"):
        audit.audit("codex", object(), "test-codex")


def test_audit_rejects_duplicate_session_identity(monkeypatch):
    steps = [_action(0, "exec_command", "Bash", {"command": "pytest"})]
    monkeypatch.setattr(
        audit, "read_independent",
        lambda *_args: iter([
            ((_meta(), steps), None, None), ((_meta(), steps), None, None)
        ]),
    )
    with pytest.raises(audit.AuditError, match="duplicate normalized session"):
        audit.audit("codex", object(), "test-codex")


def test_zcode_source_error_discards_earlier_sessions(monkeypatch):
    steps = [_action(0, "Bash", "Bash", {"command": "pytest"})]

    def broken_source(*_args):
        yield _meta(), steps
        raise AdapterError("later session is malformed")

    monkeypatch.setattr(audit.zcode, "iter_transcripts", broken_source)
    with pytest.raises(audit.AuditError, match="zcode source rejected"):
        list(audit.read_independent("zcode", object(), "test-zcode"))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("actions", 3, "label conservation"),
        ("mapped_actions", 2, "mapped/unmapped conservation"),
        ("aliased_actions", 3, "aliased action count"),
        ("eligible_pairs", 3, "eligible pair count"),
    ],
)
def test_validate_result_rejects_corrupt_accounting(monkeypatch, field, value, message):
    steps = [
        _action(0, "exec_command", "Bash", {"command": "pytest"}),
        _action(1, "unknown", None, {}),
    ]
    monkeypatch.setattr(
        audit, "read_independent",
        lambda *_args: iter([((_meta(), steps), None, None)]),
    )
    result = audit.audit("codex", object(), "test-codex")
    result[field] = value
    with pytest.raises(audit.AuditError, match=message):
        audit.validate_result(result)


def test_cli_failure_does_not_create_receipt(tmp_path):
    out = tmp_path / "result.json"
    # Exercise the public failure path without relying on private source fixtures.
    old_argv = sys.argv
    try:
        sys.argv = [
            "audit_agent_label_coverage.py", "--source", "codex",
            "--root", str(tmp_path / "missing"), "--namespace", "test-codex",
            "--out", str(out),
        ]
        assert audit.main() == 2
    finally:
        sys.argv = old_argv
    assert not out.exists()
