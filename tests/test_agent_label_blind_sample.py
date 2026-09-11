"""Contract tests for deterministic cross-agent blind label samples."""
from __future__ import annotations

import json
import os
import sys

import pytest

CORPUS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "utils", "corpus")
sys.path.insert(0, CORPUS)

import sample_agent_label_audit as sample  # noqa: E402
from normalized_transcript import (  # noqa: E402
    EVENT_FORMAT_VERSION, TOOL_ALIAS_VERSION, NormalizedStep,
    NormalizedTranscript,
)


def _transcript():
    meta = NormalizedTranscript(
        event_format_version=EVENT_FORMAT_VERSION,
        tool_alias_version=TOOL_ALIAS_VERSION,
        source_agent="zcode",
        source_namespace="fixture-zcode",
        source_relpaths=("private.jsonl",),
        session_id="session-digest",
        transcript_sha256="transcript-digest",
        native_session_id="private-session",
    )
    steps = [
        NormalizedStep(
            kind="action", source_tool="Bash", canonical_tool="Bash",
            tool_input={"command": "pytest -q PRIVATE_PATH"}, action_ordinal=0,
            source_event_id="event-1", native_event_id="native-1"),
        NormalizedStep(
            kind="action", source_tool="Read", canonical_tool="Read",
            tool_input={"file_path": "PRIVATE_PATH"}, action_ordinal=1,
            source_event_id="event-2", native_event_id="native-2"),
    ]
    return meta, steps


def test_draw_is_deterministic_blind_and_conserves_rows(monkeypatch):
    transcript = _transcript()
    monkeypatch.setattr(
        sample.coverage, "read_independent",
        lambda *_args: iter([(transcript, None, None)]))

    first = sample.build_draw("zcode", object(), "fixture-zcode", 2, 1, 37)
    second = sample.build_draw("zcode", object(), "fixture-zcode", 2, 1, 37)
    plan, blinded, truth = first

    assert first == second
    assert plan["population"] == {"read_file": 1, "run_tests": 1}
    assert plan["allocation"] == {"read_file": 1, "run_tests": 1}
    assert len(blinded) == len(truth) == plan["drawn"] == 2
    assert {row["id"] for row in blinded} == {row["id"] for row in truth}
    assert all("sorter_label" not in row for row in blinded)
    assert "PRIVATE_PATH" in "".join(row["text"] for row in blinded)
    assert "PRIVATE_PATH" not in json.dumps(plan)
    assert "private-session" not in json.dumps(first)
    assert "native-1" not in json.dumps(first)


def test_pool_rejects_duplicate_event_identity(monkeypatch):
    meta, steps = _transcript()
    duplicate = [steps[0], steps[0]]
    monkeypatch.setattr(
        sample.coverage, "read_independent",
        lambda *_args: iter([((meta, duplicate), None, None)]))

    with pytest.raises(sample.SampleError, match="duplicate normalized"):
        sample.build_pool("zcode", object(), "fixture-zcode")


def test_private_output_must_be_new_and_below_data(tmp_path):
    with pytest.raises(sample.SampleError, match="directory named data"):
        sample._private_output(tmp_path / "audit")
    existing = tmp_path / "data" / "audit"
    existing.mkdir(parents=True)
    with pytest.raises(sample.SampleError, match="already exists"):
        sample._private_output(existing)


def test_cli_failure_writes_no_partial_sample(tmp_path, monkeypatch):
    out = tmp_path / "data" / "audit"
    monkeypatch.setattr(sample.sys, "argv", [
        "sample_agent_label_audit.py", "--source", "zcode",
        "--root", str(tmp_path / "missing"), "--namespace", "fixture-zcode",
        "--target", "2", "--out-dir", str(out),
    ])

    assert sample.main() == 2
    assert not out.exists()
