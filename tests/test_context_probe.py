import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike" / "coding_core"))
import context_probe as probe
import prepare_openhands as prep


def call(call_id, command="cat a.py"):
    return {"role": "assistant", "content": "UNOBSERVED_REASONING",
            "tool_calls": [{"id": call_id, "function": {"name": "execute_bash",
                            "arguments": json.dumps({"command": command})}}]}


def result(call_id, content):
    return {"role": "tool", "tool_call_id": call_id, "name": "execute_bash", "content": content}


def source():
    return {"resolved": 1, "model_patch": "UNOBSERVED_PATCH", "instance_id": "repo__one-1",
            "trajectory_id": "trace-1", "trajectory": [
                {"role": "user", "content": "Fix parser"}, call("a"),
                result("a", "observed failure"), call("b", "pytest -q"),
                result("b", "UNOBSERVED_FUTURE_RESULT")]}


def test_context_excludes_future_and_reasoning():
    src = source()
    rows = prep.trajectory_rows(src, [], context=True)
    assert rows == [{"task": "Fix parser", "observation": "observed failure",
                     "history": ["read"], "target": "run_tests"}]
    altered = copy.deepcopy(src)
    altered["trajectory"][-1]["content"] = "completely different future"
    altered["model_patch"] = "future diff"
    assert prep.trajectory_rows(altered, [], context=True) == rows
    # Target arguments may affect the label, never the features.
    altered["trajectory"][-2] = call("b", "git status")
    changed = prep.trajectory_rows(altered, [], context=True)[0]
    assert changed["target"] == "git"
    assert probe.signature(changed) == probe.signature(rows[0])


@pytest.mark.parametrize("kind", ["wrong_id", "wrong_name", "missing", "empty", "parallel", "control"])
def test_ambiguous_observation_cannot_supply_context(kind):
    src = source()
    messages = src["trajectory"]
    if kind == "wrong_id":
        messages[2]["tool_call_id"] = "other"
    elif kind == "wrong_name":
        messages[2]["name"] = "other"
    elif kind == "missing":
        del messages[2]
    elif kind == "empty":
        messages[2]["content"] = ""
    elif kind == "parallel":
        messages[1]["tool_calls"].append(call("extra")["tool_calls"][0])
    else:
        messages.insert(3, {"role": "assistant", "tool_calls": [{"id": "control",
            "function": {"name": "think", "arguments": "{}"}}]})
    assert prep.trajectory_rows(src, [], context=True) == []


def test_prefix_and_text_caps_and_new_user_boundary():
    src = source()
    src["trajectory"][0]["content"] = "t" * 900
    src["trajectory"][2]["content"] = "o" * 3000
    row = prep.trajectory_rows(src, [], context=True)[0]
    assert len(row["task"]) == 600 and len(row["observation"]) == 2000
    src["trajectory"].insert(3, {"role": "user", "content": "Different task"})
    assert prep.trajectory_rows(src, [], context=True) == []


def find_ids():
    found = {}
    for i in range(100):
        issue = f"repo__item-{i}"
        found.setdefault(prep.split_for(issue, 20), issue)
    assert set(found) == {"train", "holdout"}
    return found


def test_deterministic_issue_selection_and_overlap_removal():
    ids = find_ids()
    a, b = source(), source()
    a.update(instance_id=ids["train"], trajectory_id="a")
    b.update(instance_id=ids["holdout"], trajectory_id="b")
    other = copy.deepcopy(a)
    other["trajectory_id"] = "other"
    other["trajectory"][0]["content"] = "new inputs must not replace first issue"
    splits, audit = probe.prepare([a, other, b])
    assert audit["duplicate_issue_or_trajectory"] == 1
    assert audit["train_input_overlap_excluded"] == 1
    assert len(splits["train"]) == 0 and len(splits["holdout"]) == 1


def example(i, task, target):
    return dict(issue=f"issue-{i}", task=task, observation="observed", history=["read"], target=target)


def test_context_has_signal_and_vocab_is_train_only():
    train = [example(i, "red" if i % 2 else "blue", "edit" if i % 2 else "run_tests")
             for i in range(100)]
    action, context = probe.fit_nb(train, False), probe.fit_nb(train, True)
    red, blue = example(101, "red SECRET_EVAL_TOKEN", "edit"), example(102, "blue", "run_tests")
    assert probe.predict_nb(context, red, True) == "edit"
    assert probe.predict_nb(context, blue, True) == "run_tests"
    assert probe.predict_nb(action, red, False) == probe.predict_nb(action, blue, False)
    assert "task:secret_eval_token" not in context[0]
    assert all(not t.startswith("task:") for t in action[0])
    assert probe.features(dict(red, target="git", issue="other"), True) == probe.features(red, True)


def test_shuffle_preserves_history_labels_and_last_action_strata():
    rows = [example(i, str(i), "edit") for i in range(40)]
    for row in rows[20:]:
        row["history"] = ["git"]
    shuffled, changed = probe.shuffle_context(rows)
    assert changed >= 20
    assert probe.shuffle_context(rows) == (shuffled, changed)
    for a, b in zip(rows, shuffled):
        assert a["history"] == b["history"] and a["target"] == b["target"]
        assert (int(b["task"]) < 20) == (a["history"][-1] == "read")


def test_empty_and_sparse_inputs_refuse():
    with pytest.raises(ValueError, match="insufficient"):
        probe.validate({"train": [], "holdout": []})
    with pytest.raises(ValueError, match="empty"):
        probe.fit_nb([], True)
    with pytest.raises(ValueError, match="empty"):
        probe.metrics([], [])
    with pytest.raises(ValueError, match="mismatched"):
        probe.metrics([example(1, "t", "edit")], [])


def test_metrics_missing_slices_and_label_denominators():
    row = example(1, "t", "read")
    got = probe.metrics([row], ["read"])
    assert got["accuracy_pct"] == 100
    assert got["change_rows"] == 0 and got["change_accuracy_pct"] is None
    assert got["labels"]["git"]["recall_pct"] is None
    assert got["macro_f1"] == pytest.approx(1 / 6)


def test_validation_rejects_issue_overlap_and_exact_input_overlap():
    train = [example(i, f"train {i}", "edit") for i in range(1000)]
    held = [example(i + 1000, f"held {i}", "edit") for i in range(200)]
    probe.validate({"train": train, "holdout": held})
    held[0]["issue"] = train[0]["issue"]
    with pytest.raises(ValueError, match="issue overlap"):
        probe.validate({"train": train, "holdout": held})
    held[0]["issue"] = "held-only"
    held[0]["task"] = train[0]["task"]
    with pytest.raises(ValueError, match="feature-input overlap"):
        probe.validate({"train": train, "holdout": held})


def test_complete_synthetic_comparison_and_control():
    def rows(start, count):
        return [example(i, ("red" if i % 2 else "blue") + f" unique{i}",
                        "edit" if i % 2 else "run_tests") for i in range(start, start + count)]
    got = probe.evaluate({"train": rows(0, 1000), "holdout": rows(1000, 200)})
    assert got["metrics"]["context_nb"]["correct"] == 200
    assert got["metrics"]["action_nb"]["correct"] == 100
    assert got["metrics"]["shuffled_context_nb"]["correct"] < 150
    assert got["decision"]["passed"]


def test_revision_fails_closed(monkeypatch):
    monkeypatch.setattr(probe, "fetch_json", lambda _: {"sha": "substituted"})
    with pytest.raises(ValueError, match="revision"):
        probe.check_revision()


def test_download_size_fails_closed(monkeypatch):
    import io
    monkeypatch.setattr(probe, "RESPONSE_LIMIT", 16)
    monkeypatch.setattr(probe.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b" " * 17))
    with pytest.raises(ValueError, match="cap"):
        probe.fetch_json("https://example.invalid")


def test_cli_retains_refusal_and_refuses_overwrite(tmp_path, monkeypatch):
    out = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", ["probe", "--out", str(out)])
    monkeypatch.setattr(probe.resource, "setrlimit", lambda *_: None)
    def refuse(_):
        raise ValueError("controlled source refusal")
    monkeypatch.setattr(probe, "acquire", refuse)
    assert probe.main() == 2
    saved = (out / "result.json").read_bytes()
    assert json.loads(saved)["status"] == "refused"
    with pytest.raises(FileExistsError):
        probe.main()
    assert (out / "result.json").read_bytes() == saved
