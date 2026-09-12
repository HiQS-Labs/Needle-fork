import json
from pathlib import Path
import sys

import pytest

CORE = Path(__file__).resolve().parents[1] / "spike" / "coding_core"
sys.path.insert(0, str(CORE))
import baselines
import prepare_openhands as prep


def call(name, arguments):
    return {"function": {"name": name, "arguments": json.dumps(arguments)}}


@pytest.mark.parametrize(("tool", "args", "label"), [
    ("str_replace_editor", {"command": "view", "path": "a.py"}, "read"),
    ("str_replace_editor", {"command": "str_replace", "path": "a.py"}, "edit"),
    ("execute_bash", {"command": "rg needle src"}, "search"),
    ("execute_bash", {"command": "pytest -q"}, "run_tests"),
    ("execute_bash", {"command": "git status --short"}, "git"),
    ("execute_bash", {"command": "python script.py"}, "run_command"),
])
def test_tool_projection(tool, args, label):
    assert prep.project_call(call(tool, args)) == label


def test_mapper_fails_closed_and_control_fires():
    with pytest.raises(prep.InputError):
        prep.project_call(call("new_unknown_tool", {}))
    with pytest.raises(prep.InputError):
        prep.project_call(call("str_replace_editor", {"command": "future_op"}))
    assert prep.project_call(call("think", {"thought": "x"})) is None


def source(instance, actions, resolved=1):
    return {"instance_id": instance, "resolved": resolved, "trajectory": [
        {"role": "user", "content": "Fix the issue"},
        {"role": "assistant", "tool_calls": actions},
    ]}


def find_instances():
    found = {}
    for i in range(10000):
        instance = f"repo__issue-{i}"
        found.setdefault(prep.split_for(instance, 50), instance)
        if len(found) == 2:
            return found
    raise AssertionError("could not construct both split fixtures")


def test_prepare_splits_by_instance_before_caps(tmp_path):
    ids = find_instances()
    actions = [call("execute_bash", {"command": "sed -n '1p' a.py"}),
               call("execute_bash", {"command": "pytest -q"}),
               call("str_replace_editor", {"command": "str_replace"})]
    rows = [source(ids["train"], actions), source(ids["holdout"], actions)]
    out = tmp_path / "out"
    receipt = prep.prepare(rows, out, 1, 1, 50, True)
    assert receipt["counts"]["rows_train"] == receipt["counts"]["rows_holdout"] == 1
    assert receipt["instances"] == {"train": 1, "holdout": 1}
    train = json.loads((out / "pilot-train.jsonl").read_text())
    holdout = json.loads((out / "pilot-holdout.jsonl").read_text())
    assert train["answers"] == holdout["answers"] == [{"name": "run_tests"}]
    assert not (out / "pilot-train.jsonl.tmp").exists()
    with pytest.raises(prep.InputError):
        prep.prepare(rows, out, 1, 1, 50, True)


def test_unsupported_call_breaks_sequence():
    schemas = json.loads((CORE / "labels.json").read_text())["schemas"]
    rows = prep.trajectory_rows(source("x", [
        call("execute_bash", {"command": "cat a.py"}),
        call("think", {"thought": "now edit"}),
        call("str_replace_editor", {"command": "str_replace"}),
        call("execute_bash", {"command": "pytest -q"}),
    ]), schemas)
    assert len(rows) == 1
    assert rows[0]["answers"] == [{"name": "run_tests"}]
    assert "LAST: edit" in rows[0]["query"]


def test_baselines_are_fit_on_train_with_lexical_ties():
    train = [("task", ("read",), "edit"), ("task", ("edit",), "read"),
             ("task", ("read",), "edit"), ("task", ("git",), "read")]
    holdout = [("other", ("read",), "edit"), ("other", ("edit",), "edit"),
               ("other", ("unknown",), "edit")]
    got = baselines.evaluate(train, holdout)
    assert got["majority_label"] == "edit"
    assert got["metrics"]["majority"]["correct"] == 3
    assert got["metrics"]["repeat_last"]["correct"] == 1
    assert got["metrics"]["markov_1"]["correct"] == 2


def test_baseline_loader_uses_only_issue_and_prior_actions(tmp_path):
    path = tmp_path / "row.jsonl"
    path.write_text(json.dumps({
        "query": "[coding-core-q1]\nISSUE: fix tests\n"
                 "RECENT ACTIONS (oldest->newest): read, edit\nLAST: edit",
        "answers": [{"name": "run_tests"}],
        "reasoning": "SECRET_TARGET_LEAK",
    }) + "\n")
    assert baselines.load(path) == [("fix tests", ("read", "edit"), "run_tests")]


def test_phase_backoff_uses_prior_edit_and_backs_off():
    train = [
        ("a", ("read", "edit", "read"), "run_tests"),
        ("b", ("search", "edit", "read"), "run_tests"),
        ("c", ("read",), "search"),
        ("d", ("read",), "search"),
        ("e", ("search",), "search"),
    ]
    holdout = [
        ("unseen", ("edit", "read"), "run_tests"),
        ("unseen", ("unknown",), "search"),
    ]
    got = baselines.evaluate(train, holdout)
    assert got["metrics"]["phase_backoff"]["correct"] == 2
    assert got["promotion"]["gate_accuracy_pct"] == 42.0


def test_baseline_loader_rejects_empty(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    with pytest.raises(ValueError, match="no examples"):
        baselines.load(path)


def test_private_oracle_projection_breaks_at_control_actions(tmp_path):
    path = tmp_path / "pairs.jsonl"
    material = [
        {"split": "train", "session": "ignored", "recent_user_request": "x",
         "prior_actions": ["read_file"], "label": "apply_patch"},
        {"split": "holdout", "session": "s1", "recent_user_request": "fix",
         "prior_actions": ["read_file", "ask_user", "search_code", "apply_patch"],
         "label": "run_tests"},
        {"split": "holdout", "session": "s1", "recent_user_request": "fix",
         "prior_actions": ["read_file"], "label": "no_action"},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in material))
    rows, sessions = baselines.load_oracle_pairs(path)
    assert rows == [("fix", ("search", "edit"), "run_tests")]
    assert sessions == 1


def test_prepare_failure_leaves_no_partial_output(tmp_path):
    out = tmp_path / "out"
    with pytest.raises(prep.InputError, match="both splits"):
        prep.prepare([source("only-one-split", [
            call("execute_bash", {"command": "cat a.py"}),
            call("execute_bash", {"command": "pytest -q"}),
        ])], out, 10, 10, 1, True)
    assert not out.exists()
    assert not out.with_name("out.tmp").exists()


def test_prepare_receipt_records_selection_and_source(tmp_path):
    ids = find_instances()
    actions = [call("execute_bash", {"command": "cat a.py"}),
               call("execute_bash", {"command": "pytest -q"})]
    source_info = {"mode": "offline_jsonl", "input_sha256": "abc123"}
    receipt = prep.prepare(
        [source(ids["train"], actions), source(ids["holdout"], actions)],
        tmp_path / "out", 7, 3, 50, True, 9, source_info,
    )
    assert receipt["source"] == source_info
    assert receipt["selection"] == {
        "resolved_only": True,
        "max_trajectories": 9,
        "max_train": 7,
        "max_holdout": 3,
        "holdout_pct": 50,
    }
