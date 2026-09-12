import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "private_transition_baselines",
    Path(__file__).resolve().parents[1] / "spike/coding_core/baselines.py",
)
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


def pair(session="a", step=1, split="train", history=None, label="apply_patch", request="fix"):
    return dict(session=session, step=step, split=split,
                prior_actions=history or ["read_file"], label=label,
                recent_user_request=request)


def write_pairs(tmp_path, rows):
    path = tmp_path / "pairs.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def test_split_and_content_checks(tmp_path):
    rows = [pair(), pair(step=2, label="search_code"),
            pair(session="b", split="holdout")]
    train, holdout, audit = b.load_private_splits(write_pairs(tmp_path, rows))
    assert len(train) == len(holdout) == 1
    assert audit["excluded_train_content_overlap"] == 1
    assert audit["sessions"] == {"train": 1, "holdout": 1}
    assert train[0][2] == "search"


@pytest.mark.parametrize("rows,match", [
    ([], "empty"),
    ([pair(), pair(split="holdout", step=2)], "session overlap"),
    ([pair(), pair(), pair(session="b", split="holdout")], "duplicate event"),
    ([pair(), pair(session="b", split="holdout")], "empty"),
    ([pair(label="invented")], "unknown canonical"),
])
def test_loader_fails_closed(tmp_path, rows, match):
    with pytest.raises(ValueError, match=match):
        b.load_private_splits(write_pairs(tmp_path, rows))


def test_control_breaks_history_and_training_prompt_is_not_a_feature(tmp_path):
    rows = [pair(history=["apply_patch", "ask_user", "search_code"], request="secret"),
            pair(session="b", split="holdout", label="run_tests")]
    train, _, _ = b.load_private_splits(write_pairs(tmp_path, rows))
    assert train == [("a", ("search",), "edit")]


def fixture():
    return [("a", ("read",), "read"), ("b", ("read",), "read"),
            ("c", ("read",), "edit"), ("d", ("edit", "read"), "run_tests"),
            ("e", ("edit", "read"), "run_tests"), ("f", ("search",), "edit")]


def test_ordinary_prediction_parity_with_frozen_evaluator():
    train = fixture()
    holdout = [("z", ("read",), "edit"), ("z", ("edit", "read"), "run_tests"),
               ("y", ("git",), "read")]
    old = b.evaluate(train, holdout)["metrics"]
    new = b.evaluate_private(train, holdout)
    assert new["overall"] == {k: dict(v, rows=len(holdout)) for k, v in old.items()}
    assert new["per_session"]["overall"]["markov_1"]["sessions"] == 2


def test_excluded_prediction_backs_off_without_using_target():
    model = b.fit(fixture())
    ordinary = b.predict(model, ("read",))
    conditional = b.predict(model, ("read",), exclude_previous=True)
    assert ordinary["phase_backoff"] == "read"
    assert conditional["phase_backoff"] == "run_tests"
    # A context with only repeat outcomes falls back to training destinations.
    repeat_model = b.fit([("a", ("git",), "git"), ("b", ("git",), "git"),
                          ("c", ("read",), "edit")])
    assert b.predict(repeat_model, ("git",), True)["phase_backoff"] == "edit"
    assert all(v != "git" for v in b.predict(repeat_model, ("git",), True).values())


def test_same_family_must_pass_both_gates_and_boundary_is_inclusive():
    got = b.promotion(40, 30, {"markov_1": (45, 39), "phase_backoff": (44, 40)})
    assert not got["passed"]
    assert got["decision"] == "consider_run_endings"
    assert b.promotion(40, 30, {"markov_1": (45, 40)})["passed"]
    assert b.promotion(40, 30, {"markov_1": (44, 39)})["decision"] == "stop"


def test_no_change_rows_cannot_pass_and_receipt_has_no_identifiers():
    with pytest.raises(ValueError, match="action-change"):
        b.evaluate_private(fixture(), [("private-session", ("read",), "read")])
    report = b.evaluate_private(fixture(), [("private-session", ("read",), "edit")])
    assert "private-session" not in json.dumps(report)


def test_cli_manifest_guard_runs_before_fit(tmp_path, monkeypatch):
    source = write_pairs(tmp_path, [pair(), pair(session="b", split="holdout", request="other")])
    out = tmp_path / "receipt.json"
    manifest = tmp_path / "frozen.json"
    manifest.write_text(json.dumps({"input_sha256": b.digest(source)}))
    monkeypatch.setattr("sys.argv", ["baselines", "--private-pairs", str(source),
                                   "--private-manifest", str(manifest), "--out", str(out)])
    monkeypatch.setattr(b, "fit", lambda _: pytest.fail("must not fit wrong manifest"))
    with pytest.raises(ValueError, match="fixed evaluation manifest mismatch"):
        b.main()
    assert not out.exists()


def test_cli_refuses_existing_receipt_before_reading_input(tmp_path, monkeypatch):
    out = tmp_path / "receipt.json"
    out.write_text("preserve")
    monkeypatch.setattr("sys.argv", ["baselines", "--private-pairs", "absent.jsonl", "--out", str(out)])
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        b.main()
    assert out.read_text() == "preserve"


def test_empty_conditional_terminal_fails():
    with pytest.raises(ValueError, match="empty action-change destination fallback"):
        b.predict(b.fit([("a", ("read",), "read")]), ("read",), True)


def test_same_size_substituted_private_input_is_rejected(tmp_path, monkeypatch):
    import types

    source = write_pairs(tmp_path, [pair(), pair(session="b", split="holdout", request="other")])
    manifest = tmp_path / "frozen.json"
    manifest.write_text(json.dumps({"input_sha256": b.digest(source)}))
    # Same rows, sessions and string length; only content changes after freezing.
    source.write_text(source.read_text().replace('"other"', '"OTHER"'))
    monkeypatch.setattr(b.argparse.ArgumentParser, "parse_args", lambda _: types.SimpleNamespace(
        private_pairs=source, private_manifest=manifest, train=None, holdout=None,
        oracle_pairs=None, out=tmp_path / "result.json"))
    # Isolate manifest validation from separately tested projection/counting.
    monkeypatch.setattr(b, "load_private_splits", lambda _: (
        [None] * 45127, [None] * 23442,
        {"sessions": {"train": 296, "holdout": 63}, "excluded_train_content_overlap": 1}))
    monkeypatch.setattr(b, "evaluate_private", lambda *_: pytest.fail("substituted input reached fitting"))
    with pytest.raises(ValueError, match="fixed private input digest mismatch"):
        b.main()


@pytest.mark.parametrize("train_count,train_sessions,excluded", [(45126, 296, 1), (45127, 295, 1), (45127, 296, 0)])
def test_frozen_training_counts_are_checked(tmp_path, monkeypatch, train_count, train_sessions, excluded):
    source = write_pairs(tmp_path, [pair()])
    manifest = tmp_path / "frozen.json"
    manifest.write_text(json.dumps({"input_sha256": b.digest(source)}))
    monkeypatch.setattr("sys.argv", ["baselines", "--private-pairs", str(source),
                                   "--private-manifest", str(manifest), "--out", str(tmp_path / "out.json")])
    monkeypatch.setattr(b, "load_private_splits", lambda _: (
        [None] * train_count, [None] * 23442,
        {"sessions": {"train": train_sessions, "holdout": 63}, "excluded_train_content_overlap": excluded}))
    monkeypatch.setattr(b, "evaluate_private", lambda *_: pytest.fail("changed counts reached fitting"))
    with pytest.raises(ValueError, match="fixed evaluation manifest mismatch"):
        b.main()


def test_private_mode_requires_retained_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["baselines", "--private-pairs", "absent.jsonl",
                                   "--out", str(tmp_path / "out.json")])
    with pytest.raises(SystemExit) as exc:
        b.main()
    assert exc.value.code == 2


def test_matching_manifest_and_counts_reach_evaluation(tmp_path, monkeypatch):
    source = write_pairs(tmp_path, [pair()])
    manifest = tmp_path / "frozen.json"
    manifest.write_text(json.dumps({"input_sha256": b.digest(source)}))
    out = tmp_path / "result.json"
    monkeypatch.setattr("sys.argv", ["baselines", "--private-pairs", str(source),
                                   "--private-manifest", str(manifest), "--out", str(out)])
    monkeypatch.setattr(b, "load_private_splits", lambda _: (
        [None] * 45127, [None] * 23442,
        {"sessions": {"train": 296, "holdout": 63}, "excluded_train_content_overlap": 1}))
    calls = []
    def evaluate(*_):
        calls.append(True)
        return {"overall": {}, "change_ordinary": {}, "change_excluded": {},
                "promotion": {"passed": False}}
    monkeypatch.setattr(b, "evaluate_private", evaluate)
    assert b.main() == 1  # Valid execution; mocked experimental gate still fails.
    assert calls == [True]
    assert json.loads(out.read_text())["input_sha256"] == b.digest(source)
