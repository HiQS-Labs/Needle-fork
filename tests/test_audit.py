"""Deterministic gates for the blind label-correctness audit (issue #20)."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils", "corpus"))

import sample_for_audit as sampler  # noqa: E402
import analyze_audit_causes as cause_analyzer  # noqa: E402
import score_audit as scorer  # noqa: E402
import taxonomy as tx  # noqa: E402
from transcript_events import IDENTITY_FORMAT_VERSION  # noqa: E402


REPO = os.path.join(os.path.dirname(__file__), "..")
SCORER = os.path.join(REPO, "utils", "corpus", "score_audit.py")


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def _audit_fixture(tmp_path):
    rows = [
        {"id": "x1", "tool": "Bash", "text": "one"},
        {"id": "x2", "tool": "Bash", "text": "two"},
        {"id": "x3", "tool": "Bash", "text": "three"},
        {"id": "x4", "tool": "Bash", "text": "four"},
    ]
    _write_jsonl(tmp_path / "sample.jsonl", rows)
    _write_jsonl(tmp_path / "sorter.jsonl", [
        {"id": "x1", "sorter_label": "read_file", "session": "s1"},
        {"id": "x2", "sorter_label": "read_file", "session": "s1"},
        {"id": "x3", "sorter_label": "run_validate", "session": "s2"},
        {"id": "x4", "sorter_label": "run_validate", "session": "s2"},
    ])
    _write_jsonl(tmp_path / "alice.jsonl", [
        {"id": "x1", "label": "read_file", "confidence": "high"},
        {"id": "x2", "label": "run_tests", "confidence": "low"},
        {"id": "x3", "label": "run_validate", "confidence": "high"},
        {"id": "x4", "label": "run_validate", "confidence": "high"},
    ])
    _write_jsonl(tmp_path / "bob.jsonl", [
        {"id": "x1", "label": "read_file", "confidence": "high"},
        {"id": "x2", "label": "read_file", "confidence": "low"},
        {"id": "x3", "label": "run_validate", "confidence": "high"},
        {"id": "x4", "label": "run_validate", "confidence": "high"},
    ])
    _write_jsonl(tmp_path / "judge.jsonl", [
        {"id": "x2", "label": "run_tests", "confidence": "high"},
    ])
    (tmp_path / "plan.json").write_text(json.dumps({
        "audit_format_version": 2,
        "seed": 7,
        "target": 4,
        "floor": 2,
        "label_set_version": tx.LABEL_SET_VERSION,
        "population": {"read_file": 90, "run_validate": 10},
        "allocation": {"read_file": 2, "run_validate": 2},
        "drawn": 4,
    }))
    return rows


def _score(tmp_path, extra=()):
    command = [
        sys.executable, SCORER,
        "--dir", str(tmp_path),
        "--auditors", "alice,bob",
        "--adjudicator", "judge",
        "--out", str(tmp_path / "raw.json"),
        "--adjudicated-out", str(tmp_path / "adjudicated.json"),
    ]
    command.extend(extra)
    return subprocess.run(command, capture_output=True, text=True)


def test_scorer_adjudicates_and_weights_the_stratified_sample(tmp_path):
    _audit_fixture(tmp_path)
    result = _score(tmp_path)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "adjudicated.json").read_text())
    raw = json.loads((tmp_path / "raw.json").read_text())
    assert report["adjudicated"]["correct"] == 3
    assert report["adjudicated"]["n"] == 4
    assert report["adjudicated"]["agreement"] == 0.75
    assert "sample_wilson_ci95" not in report["adjudicated"]
    assert report["population_weighted"]["all"]["estimate"] == 0.55
    assert report["reference"]["disagreements_adjudicated"] == 1
    assert raw["disagreement"]["population_weighted"]["estimate"] == 0.55


@pytest.mark.parametrize(
    "defect", [
        "duplicate", "missing", "extra", "invalid_label", "invalid_confidence",
        "null_confidence",
    ])
def test_scorer_rejects_malformed_submissions_without_a_report(tmp_path, defect):
    _audit_fixture(tmp_path)
    path = tmp_path / "alice.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if defect == "duplicate":
        rows.append(rows[0])
    elif defect == "missing":
        rows.pop()
    elif defect == "extra":
        rows.append({"id": "extra", "label": "read_file", "confidence": "high"})
    elif defect == "invalid_label":
        rows[0]["label"] = "not_a_label"
    elif defect == "invalid_confidence":
        rows[0]["confidence"] = "maybe"
    else:
        rows[0]["confidence"] = None
    _write_jsonl(path, rows)

    result = _score(tmp_path)
    assert result.returncode != 0
    expected = {
        "duplicate": "duplicate id",
        "missing": "id set",
        "extra": "id set",
        "invalid_label": "unknown label",
        "invalid_confidence": "invalid confidence",
        "null_confidence": "non-null confidence",
    }[defect]
    assert expected in result.stderr.lower()
    assert not (tmp_path / "raw.json").exists()
    assert not (tmp_path / "adjudicated.json").exists()


def test_scorer_requires_v2_or_an_explicit_legacy_override(tmp_path):
    _audit_fixture(tmp_path)
    plan_path = tmp_path / "plan.json"
    plan = json.loads(plan_path.read_text())
    del plan["audit_format_version"]
    plan_path.write_text(json.dumps(plan))

    result = _score(tmp_path)
    assert result.returncode != 0
    assert "audit format is none, expected 2 or 3" in result.stderr.lower()
    assert not (tmp_path / "raw.json").exists()

    result = _score(tmp_path, ["--allow-legacy-plan"])
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "raw.json").read_text())
    assert report["measurement_contract"]["plan_format"].startswith("legacy-unversioned")


def test_scorer_accepts_v3_only_with_complete_unique_source_identity(tmp_path):
    _audit_fixture(tmp_path)
    plan_path = tmp_path / "plan.json"
    plan = json.loads(plan_path.read_text())
    plan.update({
        "audit_format_version": 3,
        "identity_format": IDENTITY_FORMAT_VERSION,
        "source_namespace": "fixture",
    })
    plan_path.write_text(json.dumps(plan))
    sorter_path = tmp_path / "sorter.jsonl"
    rows = [json.loads(line) for line in sorter_path.read_text().splitlines()]
    for ordinal, row in enumerate(rows):
        row.update({
            "identity_format": IDENTITY_FORMAT_VERSION,
            "source_namespace": "fixture",
            "source_relpath": f"p/{ordinal}.jsonl",
            "session": f"{ordinal + 101:064x}",
            "transcript_sha256": f"{ordinal + 1:064x}",
            "source_event_id": f"{ordinal + 11:064x}",
            "source_event_ordinal": ordinal,
        })
    _write_jsonl(sorter_path, rows)
    assert _score(tmp_path).returncode == 0

    rows[-1]["source_event_id"] = rows[0]["source_event_id"]
    _write_jsonl(sorter_path, rows)
    result = _score(tmp_path)
    assert result.returncode != 0
    assert "duplicate source_event_id" in result.stderr


def test_scorer_refuses_duplicate_auditor_paths(tmp_path):
    _audit_fixture(tmp_path)
    result = _score(tmp_path, [
        "--auditors", f"alice,{tmp_path / 'alice.jsonl'}",
    ])
    assert result.returncode != 0
    assert "resolve to the same file" in result.stderr
    assert not (tmp_path / "raw.json").exists()


def test_scorer_refuses_an_output_that_aliases_an_input(tmp_path):
    _audit_fixture(tmp_path)
    result = _score(tmp_path, ["--out", str(tmp_path / "alice.jsonl")])
    assert result.returncode != 0
    assert "must not overwrite audit inputs" in result.stderr
    assert not (tmp_path / "adjudicated.json").exists()


def test_scorer_emits_null_for_an_empty_governance_subset(tmp_path):
    _audit_fixture(tmp_path)
    for filename, key in (
        ("sorter.jsonl", "sorter_label"),
        ("alice.jsonl", "label"),
        ("bob.jsonl", "label"),
    ):
        path = tmp_path / filename
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for row in rows:
            if row[key] == "run_validate":
                row[key] = "run_tests"
        _write_jsonl(path, rows)
    plan_path = tmp_path / "plan.json"
    plan = json.loads(plan_path.read_text())
    plan["population"]["run_tests"] = plan["population"].pop("run_validate")
    plan["allocation"]["run_tests"] = plan["allocation"].pop("run_validate")
    plan_path.write_text(json.dumps(plan))

    result = _score(tmp_path)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "adjudicated.json").read_text())
    assert report["governance"] == {"n": 0, "correct": 0, "agreement": None}
    assert report["population_weighted"]["governance"] is None


def test_scorer_rejects_a_sorter_that_disagrees_with_the_saved_allocation(tmp_path):
    _audit_fixture(tmp_path)
    plan_path = tmp_path / "plan.json"
    plan = json.loads(plan_path.read_text())
    plan["allocation"] = {"read_file": 1, "run_validate": 3}
    plan_path.write_text(json.dumps(plan))

    result = _score(tmp_path)
    assert result.returncode != 0
    assert "strata do not match" in result.stderr
    assert not (tmp_path / "raw.json").exists()
    assert not (tmp_path / "adjudicated.json").exists()


def test_allocation_hits_the_requested_target_or_refuses_it():
    counts = {"large": 10_000, "medium": 100, "tiny": 3}
    allocation = sampler.allocate(counts, target=80, floor=8)
    assert sum(allocation.values()) == 80
    assert all(0 < allocation[k] <= counts[k] for k in counts)
    with pytest.raises(ValueError):
        sampler.allocate(counts, target=2, floor=8)
    with pytest.raises(ValueError):
        sampler.allocate(counts, target=sum(counts.values()) + 1, floor=8)


def test_blind_ids_are_stable_and_do_not_encode_sorted_strata():
    labels = ("apply_patch", "read_file", "run_tests")
    pool = {
        label: [
            {"session": f"{label}-{i}", "tool": "Bash", "text": f"{label} {i}"}
            for i in range(3)
        ]
        for label in labels
    }
    plan = {label: 3 for label in labels}
    first = sampler.draw(pool, plan, seed=19)
    second = sampler.draw(pool, plan, seed=19)
    assert first == second
    sample, truth = first
    assert [row["id"] for row in sample] == [row["id"] for row in truth]
    assert all(not row["id"].startswith("a000") for row in sample)
    emitted_labels = [row["sorter_label"] for row in truth]
    assert emitted_labels != sorted(emitted_labels)


def test_sampler_refuses_to_mix_a_new_draw_with_stale_answers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "data" / "audit"
    out.mkdir(parents=True)
    (out / "old-auditor.jsonl").write_text("stale\n")
    assert sampler.main(["--source", "missing", "--out-dir", "data/audit"]) == 2


def test_sampler_refuses_a_path_that_escapes_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert sampler.main([
        "--source", "missing",
        "--out-dir", "data/../public-audit",
    ]) == 2
    assert not (tmp_path / "public-audit").exists()


def test_scorer_refuses_to_alias_raw_and_adjudicated_outputs(tmp_path):
    _audit_fixture(tmp_path)
    output = tmp_path / "same.json"
    result = subprocess.run([
        sys.executable, SCORER,
        "--dir", str(tmp_path),
        "--auditors", "alice,bob",
        "--adjudicator", "judge",
        "--out", str(output),
        "--adjudicated-out", str(output),
    ], capture_output=True, text=True)
    assert result.returncode != 0
    assert "must be different files" in result.stderr
    assert not output.exists()


def test_confusion_output_is_complete_not_top_25_only():
    labels = list(tx.LABELS_V1)
    count = len(labels)
    assert count > 25
    sorter = {
        f"x{i}": {"sorter_label": "read_file"}
        for i in range(count)
    }
    reference = {
        f"x{i}": {"label": labels[i], "confidence": "high"}
        for i in range(count)
    }
    _, confusion = scorer.score_reference(sorter, reference)
    expected = len({("read_file", labels[i]) for i in range(count)
                    if labels[i] != "read_file"})
    assert len(confusion) == expected


def _cause_row(**changes):
    row = {
        "id": "x2",
        "sorter_label": "read_file",
        "reference_label": "run_tests",
        "cause": "taxonomy_boundary",
        "confidence": "high",
        "observed_mechanism": "The frozen definitions do not settle this synthetic boundary.",
        "falsifier": "A predeclared definition selects one label uniquely.",
    }
    row.update(changes)
    return row


def _cause_fixture(tmp_path):
    _audit_fixture(tmp_path)
    path = tmp_path / "sample.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    next(row for row in rows if row["id"] == "x2")["text"] = "cat two"
    _write_jsonl(path, rows)


def test_cause_analyzer_reproduces_weighted_error_and_sensitivity(tmp_path):
    _cause_fixture(tmp_path)
    causes = tmp_path / "causes.jsonl"
    _write_jsonl(causes, [_cause_row(cause="rule_defect", confidence="low")])
    report = cause_analyzer.analyze(
        str(tmp_path), ("alice", "bob"), "judge", str(causes))
    assert report["errors"] == {"rows": 1, "population_error_estimate": 0.45}
    assert report["by_cause"]["rule_defect"]["rows"] == 1
    assert report["low_confidence_as_unresolved"]["unresolved"][
        "population_error_contribution"] == 0.45
    assert report["reviewed_correction_seed"]["rows"] == 0

    _write_jsonl(causes, [_cause_row(cause="rule_defect", confidence="high")])
    report = cause_analyzer.analyze(
        str(tmp_path), ("alice", "bob"), "judge", str(causes))
    assert report["reviewed_correction_seed"]["rows"] == 1
    assert report["reviewed_correction_seed"]["population_error_contribution"] == 0.45


@pytest.mark.parametrize("defect", ["missing", "extra", "pair", "cause", "observation", "falsifier"])
def test_cause_analyzer_rejects_incomplete_or_unverifiable_rows(tmp_path, defect):
    _cause_fixture(tmp_path)
    rows = [_cause_row()]
    if defect == "missing":
        rows = []
    elif defect == "extra":
        rows.append(_cause_row(id="x1", sorter_label="read_file", reference_label="read_file"))
    elif defect == "pair":
        rows[0]["reference_label"] = "read_file"
    elif defect == "cause":
        rows[0]["cause"] = "guess"
    elif defect == "observation":
        rows[0]["observed_mechanism"] = ""
    else:
        rows[0]["falsifier"] = ""
    causes = tmp_path / "causes.jsonl"
    _write_jsonl(causes, rows)
    with pytest.raises(scorer.AuditError):
        cause_analyzer.analyze(
            str(tmp_path), ("alice", "bob"), "judge", str(causes))


def test_multi_action_cause_requires_visible_competing_labels(tmp_path):
    _cause_fixture(tmp_path)
    causes = tmp_path / "causes.jsonl"
    _write_jsonl(causes, [_cause_row(cause="multi_action_policy")])
    with pytest.raises(scorer.AuditError, match="requires the reference"):
        cause_analyzer.analyze(
            str(tmp_path), ("alice", "bob"), "judge", str(causes))


def test_cause_analyzer_accepts_a_zero_error_audit(tmp_path):
    _cause_fixture(tmp_path)
    path = tmp_path / "alice.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    next(row for row in rows if row["id"] == "x2").update(
        label="read_file", confidence="high")
    _write_jsonl(path, rows)
    (tmp_path / "judge.jsonl").write_text("")
    causes = tmp_path / "causes.jsonl"
    causes.write_text("")

    report = cause_analyzer.analyze(
        str(tmp_path), ("alice", "bob"), "judge", str(causes))
    assert report["errors"] == {"rows": 0, "population_error_estimate": 0.0}
    assert report["by_cause"] == {}
    assert report["reviewed_correction_seed"]["share_of_estimated_error"] is None
