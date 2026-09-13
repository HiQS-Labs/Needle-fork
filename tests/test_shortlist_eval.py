import copy
from collections import Counter
import itertools
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike/coding_core"))
import shortlist_eval as short


def labels_for(target, hit):
    others = [a for a in short.LABELS if a != target]
    return ([target] + others[:2]) if hit else others[:3]


def test_ranking_ties_and_distinct_fallback():
    priors = Counter({a: 1 for a in short.LABELS})
    assert short.ranked({}, priors) == ["edit", "git", "read"]
    assert short.ranked(Counter(search=3), priors) == ["search", "edit", "git"]
    priors["read"] = 2
    assert short.ranked(Counter(git=1, read=1), priors) == ["read", "git", "edit"]


def test_phase_support_backoff_and_old_rank_one_parity():
    train = [("x", ("read",), a) for a in short.LABELS]
    train += [("x", ("edit", "read"), "run_tests")] * 3
    train += [("x", ("git", "search"), "edit")]
    model = short.baselines.fit(train)
    assert short.predict(model, ["edit", "read"])["phase"][0] == "run_tests"
    assert short.predict(model, ["run_command", "edit", "read"])["phase"][0] == "run_tests"
    assert short.predict(model, ["git", "search"])["phase"][0] == "edit"
    for n in (1, 2, 3):
        for h in itertools.product(short.LABELS, repeat=n):
            pred = short.predict(model, h)
            old = short.baselines.predict(model, h)
            for a, b in [("phase", "phase_backoff"), ("markov", "markov_1"),
                         ("static", "majority"), ("repeat_last", "repeat_last")]:
                assert pred[a][0] == old[b]
                assert len(set(pred[a])) == 3


def test_targets_and_future_fields_never_enter_prediction_or_shuffle():
    train = [("x", ("read",), a) for a in short.LABELS]
    model = short.baselines.fit(train)
    rows = [dict(history=[a], target="read", future="old") for a in short.LABELS]
    before = [short.predict(model, r["history"]) for r in rows]
    null = short.shuffled_histories([r["history"] for r in rows])
    for r in rows:
        r.update(target="edit", future="new", task="ignore all prior instructions")
    assert before == [short.predict(model, r["history"]) for r in rows]
    assert null == short.shuffled_histories([r["history"] for r in rows])
    assert sorted(null) == sorted(r["history"] for r in rows)
    assert all(a != b["history"] for a, b in zip(null, rows))
    with pytest.raises(ValueError):
        short.shuffled_histories([])


def test_uneven_issue_macro_is_not_pooled():
    rows = [dict(issue="A", target="edit")] * 9 + [dict(issue="B", target="git")]
    rows += [dict(issue="C", target=a) for a in ("read", "search", "run_tests", "run_command")]
    m = short.metrics(rows, [["edit", "read", "search"]] * 14)
    assert m["correct_at1"] == 9 and m["correct_at3"] == 11
    assert m["hit_at3_pct"] == pytest.approx(100 * 11 / 14)
    assert m["issue_macro_hit_at3_pct"] == 50
    assert m["macro_recall_at3_pct"] == 50
    with pytest.raises(ValueError):
        short.metrics([], [])


def scenario():
    rows, predictions = [], []
    for i in range(60):
        target = short.LABELS[i % 6]
        rows.append(dict(issue=str(i // 3), target=target, history=[short.LABELS[(i + 1) % 6]]))
        predictions.append({a: labels_for(target, a == "phase" or i % 4 != 0) for a in short.ARMS})
    return rows, predictions


def test_gates_pass_and_reject_wrong_predictions():
    rows, predictions = scenario()
    result = short.summarize(rows, predictions)
    assert result["passed"] and result["margin_pp"] == 25
    assert sum(result["issue_comparisons"]["static"].values()) == 20
    assert "per_issue" not in json.dumps(short.public_metrics(result))
    for r, p in zip(rows, predictions):
        p["phase"] = labels_for(r["target"], False)
    result = short.summarize(rows, predictions)
    assert not result["passed"] and result["decision"] == "park"
    assert not any(result["gates"].values())


@pytest.mark.parametrize("bad", [[], ["read"] * 3, ["read", "edit", "unknown"]])
def test_invalid_shortlists_rejected(bad):
    rows, predictions = scenario()
    predictions[0]["phase"] = bad
    with pytest.raises(ValueError, match="shortlist"):
        short.summarize(rows, predictions)
    with pytest.raises(ValueError):
        short.summarize([], [])


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    manifest = dict(format="coding-core-q3-paired-v1", hashes={}, counts={})
    for split, count, offset in (("train", 1000, 0), ("holdout", 240, 1000)):
        pairs = []
        for i in range(count):
            r = dict(issue=f"{split}-{i % 40}", task=f"{split}-{i}", observation="observed",
                     history=["read"], target=short.LABELS[i % 6])
            pairs.append(dict(source_line=offset + i + 1, transition_index=0,
                              q2=r, q3=copy.deepcopy(r)))
        path = data / (split + ".jsonl")
        path.write_text("".join(json.dumps(p) + "\n" for p in pairs))
        manifest["hashes"][path.name] = short.baselines.digest(path)
        manifest["counts"][split] = dict(rows=count, issues=40,
            labels=dict(Counter(p["q2"]["target"] for p in pairs)))
    expected = tmp_path / "trusted.json"
    expected.write_text(json.dumps(manifest))
    monkeypatch.setattr(short, "MANIFEST", expected)
    return data, manifest


def test_nonempty_trusted_data_load(frozen):
    data, manifest = frozen
    got = short.load_data(data, manifest)
    assert len(got["train"]) == 1000 and len(got["holdout"]) == 240


@pytest.mark.parametrize("kind", ["empty", "digest", "same_size_target", "counts", "overlap", "pair", "identity"])
def test_input_negative_controls(frozen, kind):
    data, manifest = frozen
    bad = copy.deepcopy(manifest)
    path = data / "holdout.jsonl"
    if kind == "empty":
        path.write_text("")
    elif kind == "digest":
        bad["hashes"][path.name] = "0" * 64
    elif kind == "same_size_target":
        raw = path.read_text()
        changed = raw.replace('"target": "edit"', '"target": "read"', 1)
        assert len(changed) == len(raw) and changed != raw
        path.write_text(changed)
    elif kind == "counts":
        bad["counts"]["holdout"]["rows"] += 1
    else:
        rows = [json.loads(s) for s in path.read_text().splitlines()]
        if kind == "overlap":
            for p in rows:
                for arm in ("q2", "q3"):
                    p[arm]["issue"] = p[arm]["issue"].replace("holdout", "train")
        elif kind == "pair":
            rows[0]["q3"]["target"] = "git"
        else:
            rows[1]["source_line"] = rows[0]["source_line"]
        path.write_text("".join(json.dumps(p) + "\n" for p in rows))
        # Isolate semantic guards beyond the byte-identity guard, not a trusted-input claim.
        bad["hashes"][path.name] = short.baselines.digest(path)
    with pytest.raises(ValueError):
        short.load_data(data, bad)


def test_lock_replay_tampering_and_no_overwrite(frozen, tmp_path, monkeypatch):
    data, _ = frozen
    out = tmp_path / "result"
    # Unit test: no resource-limit change to the parent pytest process.
    monkeypatch.setattr(short.probe, "configure_memory", lambda: {})
    args = ["--data", str(data), "--out", str(out)]
    assert short.main(args) in (0, 1)
    assert short.main(args + ["--replay"]) == 0
    with pytest.raises(FileExistsError):
        short.main(args)
    scores = short.read_json(out / "metrics.json")
    scores["overall"]["phase"]["correct_at3"] += 1
    (out / "metrics.json").write_text(json.dumps(scores))
    with pytest.raises(ValueError, match="replay mismatch"):
        short.main(args + ["--replay"])
    with (out / "predictions.json").open("a") as fh:
        fh.write(" ")
    with pytest.raises(ValueError, match="after lock"):
        short.main(args + ["--replay"])
