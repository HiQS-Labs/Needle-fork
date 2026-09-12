import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
MODULE = ROOT / "utils/corpus/build_grounded_augmentation.py"
spec = importlib.util.spec_from_file_location("grounded", MODULE)
grounded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grounded)
FIXTURES = ROOT / "tests/fixtures/gh41"


def _inputs(tmp_path):
    seeds = grounded.read_jsonl(FIXTURES / "seeds.jsonl")
    digests = {row["source_id"]: grounded.digest(row) for row in seeds}
    candidates = grounded.read_jsonl(FIXTURES / "candidates.jsonl")
    for row in candidates:
        row["source_sha256"] = digests[row["source_id"]]
        row["config_sha256"] = grounded.digest({"generator": row["generator"]})
    seed_path, candidate_path = tmp_path / "seeds.jsonl", tmp_path / "candidates.jsonl"
    seed_path.write_text("".join(json.dumps(r) + "\n" for r in seeds), encoding="utf-8")
    candidate_path.write_text("".join(json.dumps(r) + "\n" for r in candidates), encoding="utf-8")
    return seed_path, candidate_path, candidates


def test_valid_fixture_is_nonempty_deterministic_and_private(tmp_path):
    seeds, candidates, rows = _inputs(tmp_path)
    first = grounded.compose(seeds, candidates, tmp_path / "out-a", "run")
    candidate_data = candidates.read_text(encoding="utf-8").splitlines()
    candidates.write_text("\n".join(reversed(candidate_data)) + "\n", encoding="utf-8")
    second = grounded.compose(seeds, candidates, tmp_path / "out-b", "run")
    assert len(rows) > 0
    for name in ("training.jsonl", "manifest.json", "report.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    report = json.loads((first / "report.json").read_text())
    assert report["records"] == len(rows) and report["pairs"] == 1
    assert "recent_user_request" not in report and "source_id" not in report


def test_empty_input_refuses_without_run(tmp_path):
    seeds, candidates, _ = _inputs(tmp_path)
    candidates.write_text("")
    with pytest.raises(grounded.ContractError, match="candidate input is empty"):
        grounded.compose(seeds, candidates, tmp_path / "out", "run")
    assert not (tmp_path / "out/run").exists()


def test_non_train_candidate_refuses(tmp_path):
    seeds, candidates, rows = _inputs(tmp_path)
    rows[0]["split"] = "validation"
    candidates.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(grounded.ContractError, match="generated training data"):
        grounded.compose(seeds, candidates, tmp_path / "out", "run")
    assert not (tmp_path / "out/run").exists()


def test_seed_byte_drift_refuses(tmp_path):
    seeds, candidates, _ = _inputs(tmp_path)
    changed = grounded.read_jsonl(seeds)
    changed[0]["reviewed_by"] = "different-reviewer"
    seeds.write_text("".join(json.dumps(r) + "\n" for r in changed))
    with pytest.raises(grounded.ContractError, match="source digest mismatch"):
        grounded.compose(seeds, candidates, tmp_path / "out", "run")
    assert not (tmp_path / "out/run").exists()


def test_candidate_label_must_be_grounded_by_seed(tmp_path):
    seeds, candidates, rows = _inputs(tmp_path)
    rows[0]["label"] = "run_tests"
    candidates.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(grounded.ContractError, match="not grounded by seed"):
        grounded.compose(seeds, candidates, tmp_path / "out", "run")
    assert not (tmp_path / "out/run").exists()


def test_counterfactual_pair_invariants(tmp_path):
    seeds, candidates, rows = _inputs(tmp_path)
    rows[1]["recent_user_request"] += " Also change another field."
    candidates.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(grounded.ContractError, match="changes more than declared span"):
        grounded.compose(seeds, candidates, tmp_path / "out", "run")
    assert not (tmp_path / "out/run").exists()


def test_counterfactual_extra_field_drift_refuses(tmp_path):
    seeds, candidates, rows = _inputs(tmp_path)
    rows[0]["undeclared"] = "drift"
    candidates.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(grounded.ContractError, match="undeclared field drift"):
        grounded.compose(seeds, candidates, tmp_path / "out", "run")
    assert not (tmp_path / "out/run").exists()


def test_duplicate_normalized_request_refuses(tmp_path):
    seeds, candidates, rows = _inputs(tmp_path)
    duplicate = dict(rows[2], record_id="duplicate", recent_user_request="Thank   you, no more work.\n")
    candidates.write_text("".join(json.dumps(r) + "\n" for r in rows + [duplicate]))
    with pytest.raises(grounded.ContractError, match="duplicate normalized request"):
        grounded.compose(seeds, candidates, tmp_path / "out", "run")
    assert not (tmp_path / "out/run").exists()


def test_forbidden_identity_refuses(tmp_path):
    seeds, candidates, _ = _inputs(tmp_path)
    forbidden = tmp_path / "forbidden.json"
    forbidden.write_text(json.dumps({"source_ids": ["reviewed-2"]}))
    with pytest.raises(grounded.ContractError, match="forbidden source identity"):
        grounded.compose(seeds, candidates, tmp_path / "out", "run", forbidden)
    assert not (tmp_path / "out/run").exists()


def test_fault_before_publish_leaves_no_final_run(tmp_path):
    seeds, candidates, _ = _inputs(tmp_path)
    with pytest.raises(grounded.ContractError, match="injected failure"):
        grounded.compose(seeds, candidates, tmp_path / "out", "run", fail_before_publish=True)
    assert not (tmp_path / "out/run").exists()


def test_canonical_serializer_is_called(monkeypatch, tmp_path):
    seeds, candidates, rows = _inputs(tmp_path)
    calls = []
    original = grounded.serialize.to_finetune_row

    def observed(pair, schemas):
        calls.append(pair["record_id"])
        return original(pair, schemas)

    monkeypatch.setattr(grounded.serialize, "to_finetune_row", observed)
    grounded.compose(seeds, candidates, tmp_path / "out", "run")
    assert calls == sorted(r["record_id"] for r in rows)


def test_noncanonical_serializer_output_refuses(monkeypatch, tmp_path):
    seeds, candidates, _ = _inputs(tmp_path)
    monkeypatch.setattr(grounded.serialize, "to_finetune_row", lambda pair, schemas: {"query": "wrong"})
    with pytest.raises(grounded.ContractError, match="invalid trainer row"):
        grounded.compose(seeds, candidates, tmp_path / "out", "run")
    assert not (tmp_path / "out/run").exists()


@pytest.mark.parametrize("mutate,message", [
    (lambda row: row.pop("taxonomy_version"), "candidate missing taxonomy_version"),
    (lambda row: row.update(pair_id=[]), "counterfactual requires pair_id"),
    (lambda row: row["controlled_change"].update(before=[]), "controlled spans must be strings"),
])
def test_malformed_counterfactual_refuses_without_publish(tmp_path, mutate, message):
    seeds, candidates, rows = _inputs(tmp_path)
    mutate(rows[0])
    candidates.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(grounded.ContractError, match=message):
        grounded.compose(seeds, candidates, tmp_path / "out", "run")
    assert not (tmp_path / "out/run").exists()


def test_cli_malformed_contract_exits_two_without_publish(tmp_path):
    seeds, candidates, rows = _inputs(tmp_path)
    rows[0].pop("taxonomy_version")
    candidates.write_text("".join(json.dumps(r) + "\n" for r in rows))
    output = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, str(MODULE), "--seeds", str(seeds), "--candidates", str(candidates),
         "--output-parent", str(output), "--run-id", "run"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert result.stderr.startswith("grounded augmentation refused: candidate missing taxonomy_version")
    assert not (output / "run").exists()
