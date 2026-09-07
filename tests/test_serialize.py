"""#1 §3/§6: the query serializer is one function, and training and the hook agree."""
import json
import os
import sys

import pytest

_UTILS = os.path.join(os.path.dirname(__file__), "..", "utils")
sys.path.insert(0, os.path.join(_UTILS, "corpus"))
sys.path.insert(0, os.path.join(_UTILS, "hooks"))

import serialize as ser  # noqa: E402
import taxonomy as tx  # noqa: E402
import oracle_stop_hook as hook  # noqa: E402

PAIR = {"session": "abc", "step": 3, "split": "train",
        "recent_user_request": "fix the failing   test\nand push",
        "prior_actions": ["read_file", "search_code", "git_inspect"],
        "label": "run_tests", "tool_name": "Bash"}


def test_query_is_deterministic_and_versioned():
    a = ser.serialize_query(PAIR["recent_user_request"], PAIR["prior_actions"])
    b = ser.serialize_query(PAIR["recent_user_request"], PAIR["prior_actions"])
    assert a == b
    assert a.startswith(ser.QUERY_MARKER + "\n")
    assert "REQUEST: fix the failing test and push" in a  # whitespace collapsed, one line
    assert a.endswith("LAST: git_inspect")


def test_reasoning_cites_a_span_inside_the_query():
    q = ser.serialize_query(PAIR["recent_user_request"], PAIR["prior_actions"])
    r = ser.templated_reasoning(PAIR["prior_actions"], PAIR["label"])
    assert "LAST: git_inspect" in q and "LAST: git_inspect" in r


def test_context_window_and_truncation():
    acts = ["read_file"] * 20 + ["apply_patch"]
    q = ser.serialize_query("x" * 5000, acts, context_steps=12, user_chars=600)
    assert q.count("read_file") == 11 and q.endswith("LAST: apply_patch")
    assert len(q.split("REQUEST: ")[1].split("\n")[0]) == 600


def test_rejects_non_v1_labels_and_empty_history():
    with pytest.raises(ValueError):
        ser.serialize_query("hi", [])
    with pytest.raises(ValueError):
        ser.serialize_query("hi", ["Bash"])  # raw tool name, not a v1 label


def test_row_matches_finetune_contract():
    schemas = ser.load_schemas()
    row = ser.to_finetune_row(PAIR, schemas)
    assert set(row) == {"query", "tools", "answers", "reasoning", "system"}
    assert row["answers"] == [{"name": "run_tests"}]      # labels take no arguments
    assert row["tools"] is schemas and len(schemas) == len(tx.LABELS_V1)
    assert {s["name"] for s in schemas} == set(tx.LABELS_V1)
    json.dumps(row)  # serializable as a JSONL line


def test_no_action_is_the_abstain_slice():
    row = ser.to_finetune_row({**PAIR, "label": "no_action"}, ser.load_schemas())
    assert row["answers"] == []


def test_hook_and_trainer_produce_identical_queries(tmp_path):
    """The §6 invariant: one serializer, byte-identical output from a live transcript."""
    lines = [
        {"message": {"role": "user", "content": "fix the failing test and push"}},
        {"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "tests/test_x.py"}}]}},
        {"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "cd /r && rg -n foo src"}}]}},
        {"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "git status"}}]}},
    ]
    p = tmp_path / "t.jsonl"
    p.write_text("".join(json.dumps(l) + "\n" for l in lines))
    request, history = hook.context_from_transcript(str(p))
    assert history == ["read_file", "search_code", "git_inspect"]
    via_hook = ser.serialize_query(request, history)
    via_trainer = ser.to_finetune_row(
        {**PAIR, "recent_user_request": request, "prior_actions": history}, ser.load_schemas())["query"]
    assert via_hook == via_trainer


def test_schema_version_matches_taxonomy():
    doc = json.load(open(ser.SCHEMAS_PATH))
    assert doc["label_set_version"] == tx.LABEL_SET_VERSION


def test_token_budget_full_schemas_need_2048():
    """Measured 2026-09-07: 44 full schemas = 1,383 tokens > 1024. Guard the decision."""
    try:
        from needle.model.tokenizer import get_tokenizer
        tok = get_tokenizer()
    except Exception as exc:
        pytest.skip(f"tokenizer unavailable: {exc}")
    schemas_json = json.dumps(ser.load_schemas(), separators=(",", ":"), ensure_ascii=False)
    n = len(tok.encode(schemas_json))
    assert n > 1024, "if this ever fits 1024, revisit TRAIN_MAX_LEN"
    assert n + 300 < ser.TRAIN_MAX_LEN, "schemas + a q1 query must fit the training cap"
