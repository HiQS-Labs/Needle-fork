"""Deterministic gates for the blind label-correctness audit (issue #20)."""
import collections
import hashlib
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


def _upgrade_fixture_to_v3(tmp_path, design=sampler.SAMPLING_DESIGN):
    plan_path = tmp_path / "plan.json"
    plan = json.loads(plan_path.read_text())
    plan.update({
        "audit_format_version": 3,
        "identity_format": IDENTITY_FORMAT_VERSION,
        "source_namespace": "fixture",
        "sampling_design": design,
    })
    if design == sampler.TARGETED_DESIGN:
        plan.update({
            "min_sessions": 2,
            "max_per_session": 2,
            "drawn_sessions": 2,
            "observed_max_per_session": 2,
        })
    plan_path.write_text(json.dumps(plan))
    sorter_path = tmp_path / "sorter.jsonl"
    rows = [json.loads(line) for line in sorter_path.read_text().splitlines()]
    for ordinal, row in enumerate(rows):
        row.update({
            "identity_format": IDENTITY_FORMAT_VERSION,
            "source_namespace": "fixture",
            "source_relpath": f"p/{ordinal}.jsonl",
            "session": f"{ordinal // 2 + 101:064x}",
            "transcript_sha256": f"{ordinal + 1:064x}",
            "source_event_id": f"{ordinal + 11:064x}",
            "source_event_ordinal": ordinal,
        })
    _write_jsonl(sorter_path, rows)
    return plan, rows


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


def test_targeted_session_draw_reports_sample_statistics_only(tmp_path):
    _audit_fixture(tmp_path)
    _upgrade_fixture_to_v3(tmp_path, sampler.TARGETED_DESIGN)

    result = _score(tmp_path)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "adjudicated.json").read_text())
    raw = json.loads((tmp_path / "raw.json").read_text())
    assert report["adjudicated"]["agreement"] == 0.75
    assert report["population_weighted"] is None
    assert raw["auditors"]["alice"]["population_weighted"] is None
    assert raw["disagreement"]["population_weighted"] is None
    assert "not estimated" in raw["measurement_contract"]["population_statistics"]
    assert all("wilson_ci95" not in row for row in report["per_label"].values())
    assert all(
        "wilson_ci95" not in row
        for auditor in raw["auditors"].values()
        for row in auditor["per_label"].values())


@pytest.mark.parametrize("relpath", ["", "/absolute.jsonl", "../escape.jsonl", 7])
def test_v3_scorer_rejects_an_invalid_source_relpath(tmp_path, relpath):
    _audit_fixture(tmp_path)
    _, rows = _upgrade_fixture_to_v3(tmp_path)
    rows[0]["source_relpath"] = relpath
    _write_jsonl(tmp_path / "sorter.jsonl", rows)

    result = _score(tmp_path)
    assert result.returncode != 0
    assert "invalid source_relpath" in result.stderr


@pytest.mark.parametrize(
    ("field", "value", "message"), [
        ("drawn_sessions", 1, "plan.drawn_sessions"),
        ("observed_max_per_session", 1, "plan.observed_max_per_session"),
        ("min_sessions", 3, "below min_sessions"),
        ("max_per_session", 1, "above max_per_session"),
    ])
def test_targeted_v3_scorer_rechecks_the_declared_session_contract(
        tmp_path, field, value, message):
    _audit_fixture(tmp_path)
    plan, _ = _upgrade_fixture_to_v3(tmp_path, sampler.TARGETED_DESIGN)
    plan[field] = value
    (tmp_path / "plan.json").write_text(json.dumps(plan))

    result = _score(tmp_path)
    assert result.returncode != 0
    assert message in result.stderr


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
        "sampling_design": sampler.SAMPLING_DESIGN,
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


def test_scorer_accepts_a_v3_audit_from_multiple_declared_namespaces(tmp_path):
    _audit_fixture(tmp_path)
    plan_path = tmp_path / "plan.json"
    plan = json.loads(plan_path.read_text())
    plan.update({
        "audit_format_version": 3,
        "identity_format": IDENTITY_FORMAT_VERSION,
        "source_namespaces": ["fixture-a", "fixture-b"],
        "sampling_design": sampler.SAMPLING_DESIGN,
    })
    plan_path.write_text(json.dumps(plan))
    sorter_path = tmp_path / "sorter.jsonl"
    rows = [json.loads(line) for line in sorter_path.read_text().splitlines()]
    for ordinal, row in enumerate(rows):
        row.update({
            "identity_format": IDENTITY_FORMAT_VERSION,
            "source_namespace": f"fixture-{'a' if ordinal % 2 == 0 else 'b'}",
            "source_relpath": f"p/{ordinal}.jsonl",
            "session": f"{ordinal + 101:064x}",
            "transcript_sha256": f"{ordinal + 1:064x}",
            "source_event_id": f"{ordinal + 11:064x}",
            "source_event_ordinal": ordinal,
        })
    _write_jsonl(sorter_path, rows)
    assert _score(tmp_path).returncode == 0

    rows[-1]["source_namespace"] = "undeclared"
    _write_jsonl(sorter_path, rows)
    result = _score(tmp_path)
    assert result.returncode != 0
    assert "wrong source_namespace" in result.stderr


def test_scorer_rejects_a_non_string_source_namespace(tmp_path):
    _audit_fixture(tmp_path)
    plan_path = tmp_path / "plan.json"
    plan = json.loads(plan_path.read_text())
    plan.update({
        "audit_format_version": 3,
        "identity_format": IDENTITY_FORMAT_VERSION,
        "source_namespaces": ["fixture", {"not": "a namespace"}],
        "sampling_design": sampler.SAMPLING_DESIGN,
    })
    plan_path.write_text(json.dumps(plan))

    result = _score(tmp_path)
    assert result.returncode != 0
    assert "source namespaces must be a non-empty unique list" in result.stderr.lower()
    assert "traceback" not in result.stderr.lower()
    assert not (tmp_path / "raw.json").exists()


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


def test_session_constrained_draw_is_exact_stable_and_fail_closed():
    pool = {
        label: [
            {
                "session": f"session-{i % 5}",
                "tool": "Bash",
                "text": f"{label} {i}",
                "source_event_id": hashlib.sha256(f"{label}-{i}".encode()).hexdigest(),
            }
            for i in range(10)
        ]
        for label in ("read_file", "run_tests")
    }
    plan = {"read_file": 4, "run_tests": 4}
    first = sampler.draw(pool, plan, seed=2501, min_sessions=4, max_per_session=2)
    second = sampler.draw(pool, plan, seed=2501, min_sessions=4, max_per_session=2)
    assert first == second
    session_counts = collections.Counter(row["session"] for row in first[1])
    assert len(first[0]) == 8
    assert len(session_counts) >= 4
    assert max(session_counts.values()) <= 2
    assert collections.Counter(row["sorter_label"] for row in first[1]) == plan

    with pytest.raises(ValueError, match="below required 6"):
        sampler.draw(pool, plan, seed=2501, min_sessions=6, max_per_session=2)
    with pytest.raises(ValueError, match="permit only 5 rows"):
        sampler.draw(pool, plan, seed=2501, min_sessions=0, max_per_session=1)


def test_session_constrained_draw_finds_terras_feasible_counterexample():
    pool = {
        "A": [{"session": "s1", "tool": "Bash", "text": "a"}],
        "B": [
            {"session": "s1", "tool": "Bash", "text": "b1"},
            {"session": "s2", "tool": "Bash", "text": "b2"},
            {"session": "s3", "tool": "Bash", "text": "b3"},
        ],
    }
    _, truth = sampler.draw(
        pool, {"A": 1, "B": 2}, seed=0, min_sessions=3, max_per_session=1)
    assert {row["session"] for row in truth} == {"s1", "s2", "s3"}


def test_v3_scorer_refuses_a_plan_without_the_srs_design_contract(tmp_path):
    _audit_fixture(tmp_path)
    plan_path = tmp_path / "plan.json"
    plan = json.loads(plan_path.read_text())
    plan.update({
        "audit_format_version": 3,
        "identity_format": IDENTITY_FORMAT_VERSION,
        "source_namespace": "fixture",
    })
    plan_path.write_text(json.dumps(plan))

    result = _score(tmp_path)
    assert result.returncode != 0
    assert "sampling design" in result.stderr.lower()
    assert not (tmp_path / "raw.json").exists()


def test_sampler_refuses_to_mix_a_new_draw_with_stale_answers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "data" / "audit"
    out.mkdir(parents=True)
    (out / "old-auditor.jsonl").write_text("stale\n")
    assert sampler.main(["--source", "missing", "--out-dir", "data/audit"]) == 2


def test_non_manifest_targeted_draw_records_a_scoreable_session_contract(
        tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sampler, "iter_calls", lambda _: iter([
        ("session-a", "Bash", {"command": "cat one"}),
        ("session-b", "Bash", {"command": "cat two"}),
    ]))
    assert sampler.main([
        "--source", "fixture", "--out-dir", "data/audit",
        "--target", "2", "--floor", "1",
        "--min-sessions", "2", "--max-per-session", "1",
    ]) == 0
    plan = json.loads((tmp_path / "data/audit/plan.json").read_text())
    assert plan["sampling_design"] == sampler.TARGETED_DESIGN
    assert plan["drawn_sessions"] == plan["min_sessions"] == 2
    assert plan["observed_max_per_session"] == plan["max_per_session"] == 1


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
    assert report["errors"] == {
        "rows": 1, "sample_error_rate": 0.25,
        "population_error_estimate": 0.45,
    }
    assert report["by_cause"]["rule_defect"]["rows"] == 1
    assert report["low_confidence_as_unresolved"]["unresolved"][
        "population_error_contribution"] == 0.45
    assert report["reviewed_correction_seed"]["rows"] == 0

    _write_jsonl(causes, [_cause_row(cause="rule_defect", confidence="high")])
    report = cause_analyzer.analyze(
        str(tmp_path), ("alice", "bob"), "judge", str(causes))
    assert report["reviewed_correction_seed"]["rows"] == 1
    assert report["reviewed_correction_seed"]["population_error_contribution"] == 0.45


def test_targeted_cause_analysis_reports_counts_without_population_claims(tmp_path):
    _cause_fixture(tmp_path)
    _upgrade_fixture_to_v3(tmp_path, sampler.TARGETED_DESIGN)
    causes = tmp_path / "causes.jsonl"
    _write_jsonl(causes, [_cause_row(cause="rule_defect", confidence="high")])

    report = cause_analyzer.analyze(
        str(tmp_path), ("alice", "bob"), "judge", str(causes))
    assert report["errors"] == {
        "rows": 1, "sample_error_rate": 0.25,
        "population_error_estimate": None,
    }
    assert report["by_cause"]["rule_defect"]["sample_error_contribution"] == 0.25
    assert "population_error_contribution" not in report["by_cause"]["rule_defect"]
    assert report["reviewed_correction_seed"]["share_of_sample_errors"] == 1.0
    assert "not a population estimate" in report["reviewed_correction_seed"]["limitation"]


def test_cause_analyzer_uses_the_complete_v3_sorter_identity_gate(tmp_path):
    _cause_fixture(tmp_path)
    plan_path = tmp_path / "plan.json"
    plan = json.loads(plan_path.read_text())
    plan.update({
        "audit_format_version": 3,
        "identity_format": IDENTITY_FORMAT_VERSION,
        "source_namespace": "fixture",
        "sampling_design": sampler.SAMPLING_DESIGN,
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
            "source_event_id": "f" * 64,
            "source_event_ordinal": ordinal,
        })
    _write_jsonl(sorter_path, rows)
    causes = tmp_path / "causes.jsonl"
    _write_jsonl(causes, [_cause_row()])

    with pytest.raises(scorer.AuditError, match="duplicate source_event_id"):
        cause_analyzer.analyze(
            str(tmp_path), ("alice", "bob"), "judge", str(causes))


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
    assert report["errors"] == {
        "rows": 0, "sample_error_rate": 0.0,
        "population_error_estimate": 0.0,
    }
    assert report["by_cause"] == {}
    assert report["reviewed_correction_seed"]["share_of_estimated_error"] is None
