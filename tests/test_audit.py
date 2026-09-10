"""Deterministic gates for the blind label-correctness audit (issue #20)."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils", "corpus"))

import sample_for_audit as sampler  # noqa: E402
import score_audit as scorer  # noqa: E402
import taxonomy as tx  # noqa: E402


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
        "seed": 7,
        "target": 4,
        "floor": 2,
        "label_set_version": tx.LABEL_SET_VERSION,
        "population": {"read_file": 90, "run_validate": 10},
        "allocation": {"read_file": 2, "run_validate": 2},
        "drawn": 4,
    }))
    return rows


def _score(tmp_path):
    return subprocess.run([
        sys.executable, SCORER,
        "--dir", str(tmp_path),
        "--auditors", "alice,bob",
        "--adjudicator", "judge",
        "--out", str(tmp_path / "raw.json"),
        "--adjudicated-out", str(tmp_path / "adjudicated.json"),
    ], capture_output=True, text=True)


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
    "defect", ["duplicate", "missing", "extra", "invalid_label", "invalid_confidence"])
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
    else:
        rows[0]["confidence"] = "maybe"
    _write_jsonl(path, rows)

    result = _score(tmp_path)
    assert result.returncode != 0
    expected = {
        "duplicate": "duplicate id",
        "missing": "id set",
        "extra": "id set",
        "invalid_label": "unknown label",
        "invalid_confidence": "invalid confidence",
    }[defect]
    assert expected in result.stderr.lower()
    assert not (tmp_path / "raw.json").exists()
    assert not (tmp_path / "adjudicated.json").exists()


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
    pool = {
        "read_file": [{"session": "s1", "tool": "Bash", "text": "cat a"}],
        "run_tests": [{"session": "s2", "tool": "Bash", "text": "pytest"}],
    }
    first = sampler.draw(pool, {"read_file": 1, "run_tests": 1}, seed=19)
    second = sampler.draw(pool, {"read_file": 1, "run_tests": 1}, seed=19)
    assert first == second
    sample, truth = first
    assert [row["id"] for row in sample] == [row["id"] for row in truth]
    assert all(not row["id"].startswith("a000") for row in sample)


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
    sorter = {
        f"x{i}": {"sorter_label": "read_file"}
        for i in range(30)
    }
    reference = {
        f"x{i}": {"label": labels[i], "confidence": "high"}
        for i in range(30)
    }
    _, confusion = scorer.score_reference(sorter, reference)
    expected = len({("read_file", labels[i]) for i in range(30)
                    if labels[i] != "read_file"})
    assert len(confusion) == expected
