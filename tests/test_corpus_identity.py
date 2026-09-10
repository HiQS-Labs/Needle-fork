"""Stable source identity and private experiment-manifest gates for issue #25."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "utils" / "corpus"
EXTRACTOR = CORPUS / "extract_claude_transcripts.py"
sys.path.insert(0, str(CORPUS))

import build_experiment_manifest as manifest_builder  # noqa: E402
import sample_for_audit as sampler  # noqa: E402
import transcript_events as events  # noqa: E402


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _transcript(path, session_id, request, suffix):
    _write_jsonl(path, [
        {
            "sessionId": session_id,
            "uuid": f"user-{suffix}",
            "message": {"role": "user", "content": request},
        },
        {
            "sessionId": session_id,
            "uuid": f"record-read-{suffix}",
            "message": {"role": "assistant", "content": [{
                "type": "tool_use", "id": f"tool-read-{suffix}", "name": "Read",
                "input": {"file_path": f"src/{suffix}.py"},
            }]},
        },
        {
            "sessionId": session_id,
            "uuid": f"record-test-{suffix}",
            "message": {"role": "assistant", "content": [{
                "type": "tool_use", "id": f"tool-test-{suffix}", "name": "Bash",
                "input": {"command": f"pytest tests/test_{suffix}.py"},
            }]},
        },
    ])


def _run_extractor(source, out_dir, namespace="fixture"):
    return subprocess.run([
        sys.executable, str(EXTRACTOR),
        "--source", str(source),
        "--source-namespace", namespace,
        "--out-dir", str(out_dir),
        "--min-session-actions", "2",
        "--holdout-pct", "0",
    ], cwd=REPO, capture_output=True, text=True)


def _prepare_pair_inputs(tmp_path):
    source = tmp_path / "source"
    _transcript(source / "project-a" / "one.jsonl", "session-one", "fix alpha", "one")
    _transcript(source / "project-b" / "two.jsonl", "session-two", "fix beta", "two")
    corpus = tmp_path / "corpus"
    result = _run_extractor(source, corpus)
    assert result.returncode == 0, result.stderr
    pairs = [json.loads(line) for line in (corpus / "pairs.jsonl").read_text().splitlines()]
    assert len(pairs) == 2
    correction = tmp_path / "correction.jsonl"
    evaluation = tmp_path / "evaluation.jsonl"
    _write_jsonl(correction, [pairs[0]])
    _write_jsonl(evaluation, [pairs[1]])
    return source, correction, evaluation, pairs


def _manifest_args(source, correction, evaluation, out, receipt=None,
                   boundary_exclusion=None, membership_source=None):
    boundary_exclusion = correction if boundary_exclusion is None else boundary_exclusion
    membership_source = correction if membership_source is None else membership_source
    legacy_prefix = "/legacy-source"
    membership_path = Path(str(membership_source) + ".membership.jsonl")
    if not membership_path.exists():
        membership_rows = []
        for line in Path(membership_source).read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            legacy_path = legacy_prefix + "/" + row["source_relpath"]
            membership_rows.append({
                **row,
                "session": hashlib.sha256(legacy_path.encode()).hexdigest()[:16],
                "split": "train",
            })
        _write_jsonl(membership_path, membership_rows)
    args = [
        "--correction", str(correction),
        "--evaluation", str(evaluation),
        "--source-root", f"fixture={source}",
        "--out", str(out),
        "--exclude-legacy", f"baseline={boundary_exclusion}",
        "--boundary", "fitting=baseline",
        "--boundary", "prior-audit=baseline",
        "--boundary", "model-selection=baseline",
        "--correction-membership-pairs", str(membership_path),
        "--correction-legacy-source-prefix", legacy_prefix,
    ]
    if receipt is not None:
        args.extend(("--receipt", str(receipt)))
    return args


def test_identity_survives_mount_prefix_and_namespace_separates_sources(tmp_path):
    first = tmp_path / "mount-a" / "projects" / "p" / "session.jsonl"
    second = tmp_path / "mount-b" / "projects" / "p" / "session.jsonl"
    _transcript(first, "stable-session", "same request", "stable")
    second.parent.mkdir(parents=True)
    second.write_bytes(first.read_bytes())

    meta_a, steps_a = events.read_transcript(first, tmp_path / "mount-a" / "projects", "studio")
    meta_b, steps_b = events.read_transcript(second, tmp_path / "mount-b" / "projects", "studio")
    meta_other, steps_other = events.read_transcript(
        second, tmp_path / "mount-b" / "projects", "mbp")

    assert meta_a.source_relpath == meta_b.source_relpath == "p/session.jsonl"
    assert meta_a.session_id == meta_b.session_id
    assert meta_a.transcript_sha256 == meta_b.transcript_sha256
    assert [step.source_event_id for step in steps_a if step.kind == "action"] == [
        step.source_event_id for step in steps_b if step.kind == "action"]
    assert meta_a.session_id != meta_other.session_id
    assert [step.source_event_id for step in steps_a if step.kind == "action"] != [
        step.source_event_id for step in steps_other if step.kind == "action"]


def test_namespaced_extractor_emits_identity_and_refuses_duplicate_session(tmp_path):
    source = tmp_path / "source"
    original = source / "a" / "session.jsonl"
    duplicate = source / "b" / "session.jsonl"
    _transcript(original, "duplicated-session", "request", "dup")
    duplicate.parent.mkdir(parents=True)
    duplicate.write_bytes(original.read_bytes())

    result = _run_extractor(source, tmp_path / "corpus")
    assert result.returncode == 2
    assert "duplicate source event identity" in result.stderr

    duplicate.unlink()
    clean = _run_extractor(source, tmp_path / "clean-corpus")
    assert clean.returncode == 0, clean.stderr
    pair = json.loads((tmp_path / "clean-corpus" / "pairs.jsonl").read_text())
    assert pair["identity_format"] == events.IDENTITY_FORMAT_VERSION
    assert pair["source_namespace"] == "fixture"
    assert len(pair["session"]) == 64
    assert len(pair["source_event_id"]) == 64
    assert len(pair["transcript_sha256"]) == 64


def test_idless_subagent_events_use_the_path_separated_session_identity(tmp_path):
    source = tmp_path / "source"
    rows = [
        {"sessionId": "shared-parent", "message": {"role": "user", "content": "request"}},
        {"sessionId": "shared-parent", "message": {"role": "assistant", "content": [{
            "type": "tool_use", "name": "Read", "input": {"file_path": "x.py"},
        }]}},
    ]
    first = source / "parent" / "session.jsonl"
    second = source / "parent" / "subagents" / "agent.jsonl"
    _write_jsonl(first, rows)
    _write_jsonl(second, rows)
    meta_a, steps_a = events.read_transcript(first, source, "fixture")
    meta_b, steps_b = events.read_transcript(second, source, "fixture")
    event_a = next(step.source_event_id for step in steps_a if step.kind == "action")
    event_b = next(step.source_event_id for step in steps_b if step.kind == "action")
    assert meta_a.session_id != meta_b.session_id
    assert event_a != event_b


def test_audit_draw_retains_event_identity_only_in_held_back_truth():
    row = {
        "session": "s" * 64,
        "tool": "Bash",
        "text": "pytest -q",
        "identity_format": events.IDENTITY_FORMAT_VERSION,
        "source_namespace": "fixture",
        "source_relpath": "p/session.jsonl",
        "transcript_sha256": "a" * 64,
        "source_event_id": "b" * 64,
        "source_event_ordinal": 1,
    }
    sample, truth = sampler.draw({"run_tests": [row]}, {"run_tests": 1}, seed=25)
    assert set(sample[0]) == {"id", "tool", "text"}
    assert truth[0]["source_event_id"] == row["source_event_id"]
    assert truth[0]["source_relpath"] == row["source_relpath"]


def test_manifest_is_reproducible_private_and_aggregate_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source, correction, evaluation, _ = _prepare_pair_inputs(tmp_path)
    out1, receipt1 = Path("data/run-one/manifest.json"), Path("receipt-one.json")
    out2, receipt2 = Path("data/run-two/manifest.json"), Path("receipt-two.json")

    args1 = _manifest_args(source, correction, evaluation, out1, receipt1)
    args2 = _manifest_args(source, correction, evaluation, out2, receipt2)
    args1.extend(("--exclude-legacy", f"legacy-correction={correction}"))
    args2.extend(("--exclude-legacy", f"legacy-correction={correction}"))
    assert manifest_builder.main(args1) == 0
    assert manifest_builder.main(args2) == 0
    assert out1.read_bytes() == out2.read_bytes()
    assert receipt1.read_bytes() == receipt2.read_bytes()

    receipt_text = receipt1.read_text()
    receipt = json.loads(receipt_text)
    assert receipt["separation"]["correction_vs_evaluation"] == {
        "content_sha256": 0, "q1_sha256": 0, "session": 0, "source_event_id": 0,
    }
    assert receipt["separation"]["evaluation_vs_exclusions"][
        "legacy-correction"] == {
            "content_sha256": 0, "q1_sha256": 0,
            "session": None, "source_event_id": None,
        }
    assert receipt["sides"]["correction"]["rows"] == 1
    assert str(tmp_path) not in receipt_text
    assert "fix alpha" not in receipt_text
    assert "pytest" not in receipt_text


def test_audit_sampler_reconstructs_only_manifest_events_and_enforces_sessions(
        tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source, correction, evaluation, _ = _prepare_pair_inputs(tmp_path)
    manifest = Path("data/manifest.json")
    assert manifest_builder.main(_manifest_args(
        source, correction, evaluation, manifest)) == 0

    common = [
        "--eligible-manifest", str(manifest),
        "--manifest-side", "correction",
        "--source-root", f"fixture={source}",
        "--target", "1",
        "--floor", "1",
        "--min-sessions", "1",
        "--max-per-session", "1",
        "--seed", "2501",
    ]
    assert sampler.main([*common, "--out-dir", "data/audit-one"]) == 0
    assert sampler.main([*common, "--out-dir", "data/audit-two"]) == 0
    for filename in ("sample.jsonl", "sorter.jsonl", "plan.json"):
        assert (Path("data/audit-one") / filename).read_bytes() == (
            Path("data/audit-two") / filename).read_bytes()
    plan = json.loads(Path("data/audit-one/plan.json").read_text())
    assert plan["eligible_manifest_sha256"] == json.loads(
        manifest.read_text())["manifest_sha256"]
    assert plan["source_namespaces"] == ["fixture"]
    assert plan["drawn_sessions"] == 1
    truth = json.loads(Path("data/audit-one/sorter.jsonl").read_text())
    eligible = json.loads(correction.read_text())
    assert truth["source_event_id"] == eligible["source_event_id"]

    blocked = Path("data/audit-short")
    assert sampler.main([
        *common, "--min-sessions", "2", "--out-dir", str(blocked),
    ]) == 2
    assert not blocked.exists()

    tampered = json.loads(manifest.read_text())
    tampered["sides"]["correction"]["rows"][0]["label"] = "run_script"
    tampered_path = Path("data/tampered-manifest.json")
    tampered_path.write_text(json.dumps(tampered))
    tampered_out = Path("data/audit-tampered")
    assert sampler.main([
        *common[:1], str(tampered_path), *common[2:],
        "--out-dir", str(tampered_out),
    ]) == 2
    assert not tampered_out.exists()


def test_manifest_audit_records_verified_events_that_have_no_auditable_text(
        tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "source"
    _transcript(source / "one.jsonl", "session-one", "fix alpha", "one")
    _transcript(source / "two.jsonl", "session-two", "fix beta", "two")
    _write_jsonl(source / "three.jsonl", [
        {
            "sessionId": "session-three",
            "uuid": "user-three",
            "message": {"role": "user", "content": "delegate work"},
        },
        {
            "sessionId": "session-three",
            "uuid": "read-three",
            "message": {"role": "assistant", "content": [{
                "type": "tool_use", "id": "tool-read-three", "name": "Read",
                "input": {"file_path": "src/three.py"},
            }]},
        },
        {
            "sessionId": "session-three",
            "uuid": "task-three",
            "message": {"role": "assistant", "content": [{
                "type": "tool_use", "id": "tool-task-three", "name": "Task",
                "input": {"description": "review"},
            }]},
        },
    ])
    corpus = tmp_path / "corpus"
    assert _run_extractor(source, corpus).returncode == 0
    pairs = [json.loads(line) for line in (corpus / "pairs.jsonl").read_text().splitlines()]
    unrenderable = next(row for row in pairs if row["tool_name"] == "Task")
    auditable = next(row for row in pairs if row["source_namespace"] == "fixture" and
                     row["tool_name"] == "Bash")
    other = next(row for row in pairs if row["session"] not in {
        unrenderable["session"], auditable["session"]})
    correction = tmp_path / "correction.jsonl"
    evaluation = tmp_path / "evaluation.jsonl"
    _write_jsonl(correction, [auditable, unrenderable])
    _write_jsonl(evaluation, [other])
    manifest = Path("data/manifest-unrenderable.json")
    assert manifest_builder.main(_manifest_args(
        source, correction, evaluation, manifest)) == 0

    out = Path("data/audit-renderable")
    assert sampler.main([
        "--eligible-manifest", str(manifest),
        "--manifest-side", "correction",
        "--source-root", f"fixture={source}",
        "--out-dir", str(out),
        "--target", "1", "--floor", "1", "--seed", "2501",
        "--min-sessions", "1", "--max-per-session", "1",
    ]) == 0
    plan = json.loads((out / "plan.json").read_text())
    assert plan["manifest_rows"] == 2
    assert plan["excluded_unrenderable"] == 1


def test_manifest_selects_legacy_training_membership_and_checks_exclusion(
        tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source, correction, evaluation, pairs = _prepare_pair_inputs(tmp_path)
    full = tmp_path / "full.jsonl"
    _write_jsonl(full, pairs)
    legacy_prefix = "/Users/example/.claude/projects"
    legacy_session = hashlib.sha256(
        (legacy_prefix + "/" + pairs[0]["source_relpath"]).encode()).hexdigest()[:16]
    membership = tmp_path / "legacy-pairs.jsonl"
    canonical_train = {**pairs[0], "session": legacy_session, "split": "train"}
    canonical_holdout = {**pairs[1], "session": "f" * 16, "split": "holdout"}
    _write_jsonl(membership, [canonical_train, canonical_holdout])
    out = Path("data/selected.json")
    receipt_path = Path("selected-receipt.json")
    args = _manifest_args(
        source, full, evaluation, out, receipt_path, boundary_exclusion=correction)
    args.extend((
        "--correction-membership-pairs", str(membership),
        "--correction-legacy-source-prefix", legacy_prefix,
    ))
    assert manifest_builder.main(args) == 0
    receipt = json.loads(receipt_path.read_text())
    assert receipt["sides"]["correction"]["rows"] == 1
    assert receipt["sides"]["correction"]["selection"]["recovered_sessions"] == 1

    appended = {**pairs[0], "step": pairs[0]["step"] + 10,
                "source_event_id": "e" * 64}
    _write_jsonl(full, [*pairs, appended])
    appended_out = Path("data/selected-with-appended.json")
    args = _manifest_args(
        source, full, evaluation, appended_out, boundary_exclusion=correction)
    args.extend((
        "--correction-membership-pairs", str(membership),
        "--correction-legacy-source-prefix", legacy_prefix,
    ))
    assert manifest_builder.main(args) == 0
    assert json.loads(appended_out.read_text())["sides"]["correction"]["summary"]["rows"] == 1

    drifted = {**pairs[0], "recent_user_request": "changed canonical context"}
    _write_jsonl(full, [drifted, pairs[1]])
    drifted_out = Path("data/selected-with-drift.json")
    args = _manifest_args(
        source, full, evaluation, drifted_out, boundary_exclusion=correction)
    args.extend((
        "--correction-membership-pairs", str(membership),
        "--correction-legacy-source-prefix", legacy_prefix,
    ))
    assert manifest_builder.main(args) == 2
    assert not drifted_out.exists()

    blocked = Path("data/blocked-by-exclusion.json")
    args = _manifest_args(source, correction, evaluation, blocked)
    args.extend(("--exclude", f"prior={evaluation}"))
    assert manifest_builder.main(args) == 2
    assert not blocked.exists()

    legacy_blocked = Path("data/blocked-by-legacy-exclusion.json")
    args = _manifest_args(source, correction, evaluation, legacy_blocked)
    args.extend(("--exclude-legacy", f"canonical={evaluation}"))
    assert manifest_builder.main(args) == 2
    assert not legacy_blocked.exists()


def test_manifest_refuses_empty_overlap_overwrite_and_source_drift(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source, correction, evaluation, _ = _prepare_pair_inputs(tmp_path)

    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    assert manifest_builder.main(_manifest_args(
        source, empty, evaluation, Path("data/empty.json"))) == 2
    assert not Path("data/empty.json").exists()

    assert manifest_builder.main(_manifest_args(
        source, correction, correction, Path("data/overlap.json"))) == 2
    assert not Path("data/overlap.json").exists()

    occupied = Path("data/occupied.json")
    occupied.parent.mkdir(parents=True)
    occupied.write_text("keep")
    assert manifest_builder.main(_manifest_args(
        source, correction, evaluation, occupied)) == 2
    assert occupied.read_text() == "keep"

    transcript = source / "project-a" / "one.jsonl"
    transcript.write_bytes(transcript.read_bytes() + b"\n")
    drift = Path("data/drift.json")
    assert manifest_builder.main(_manifest_args(
        source, correction, evaluation, drift)) == 2
    assert not drift.exists()


def test_manifest_refuses_missing_required_boundaries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source, correction, evaluation, _ = _prepare_pair_inputs(tmp_path)
    out = Path("data/missing-boundaries.json")
    complete = _manifest_args(source, correction, evaluation, out)
    args = []
    skip = False
    for value in complete:
        if skip:
            skip = False
            continue
        if value == "--boundary":
            skip = True
            continue
        args.append(value)
    assert manifest_builder.main(args) == 2
    assert not out.exists()


def test_manifest_refuses_missing_canonical_membership(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source, correction, evaluation, _ = _prepare_pair_inputs(tmp_path)
    out = Path("data/missing-membership.json")
    complete = _manifest_args(source, correction, evaluation, out)
    args = []
    skip = False
    membership_flags = {
        "--correction-membership-pairs", "--correction-legacy-source-prefix",
    }
    for value in complete:
        if skip:
            skip = False
            continue
        if value in membership_flags:
            skip = True
            continue
        args.append(value)
    assert manifest_builder.main(args) == 2
    assert not out.exists()


@pytest.mark.parametrize("field,bad", [
    ("recent_user_request", "substituted request"),
    ("prior_actions", ["run_script"]),
])
def test_manifest_refuses_q1_context_not_reconstructed_from_source(
        tmp_path, monkeypatch, field, bad):
    monkeypatch.chdir(tmp_path)
    source, correction, evaluation, pairs = _prepare_pair_inputs(tmp_path)
    pairs[0][field] = bad
    _write_jsonl(correction, [pairs[0]])
    out = Path(f"data/context-{field}.json")
    assert manifest_builder.main(_manifest_args(
        source, correction, evaluation, out)) == 2
    assert not out.exists()


@pytest.mark.parametrize("field,bad", [
    ("label_set_version", "v999"),
    ("query_format_version", "q999"),
    ("identity_format", "event-v999"),
])
def test_manifest_refuses_contract_drift(tmp_path, monkeypatch, field, bad):
    monkeypatch.chdir(tmp_path)
    source, correction, evaluation, pairs = _prepare_pair_inputs(tmp_path)
    pairs[0][field] = bad
    _write_jsonl(correction, [pairs[0]])
    out = Path(f"data/{field}.json")
    assert manifest_builder.main(_manifest_args(source, correction, evaluation, out)) == 2
    assert not out.exists()
