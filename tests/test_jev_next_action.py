"""GH-66/GH-77: the Jev next-action question stays frozen; state/wording variants render as specified."""
import json
from pathlib import Path
import sys

import pytest

CORE = Path(__file__).resolve().parents[1] / "spike" / "coding_core"
sys.path.insert(0, str(CORE))
import jev_next_action as jn  # noqa: E402
import jev_runs_summary as js  # noqa: E402
import jev_zero_shot as jz  # noqa: E402  (via jn's sys.path insert)

FROZEN_66 = "e97bc1c49bb2d983a8c997ce60e4dd35d26074a8a68397816684d4e56931f737"


def test_default_question_is_the_frozen_66_question():
    assert jz.sha256_bytes(jz.canonical(jn.QUESTIONS)) == FROZEN_66
    assert jz.sha256_bytes(jz.canonical(jn.questions("prescriptive"))) == FROZEN_66
    assert jz.sha256_bytes(jz.canonical(jn.questions("descriptive"))) != FROZEN_66
    assert "actually took next" in jn.INSTRUCTIONS_DESCRIPTIVE and "should take next" in jn.INSTRUCTIONS
    assert list(jn.QUESTIONS["next_action"]["criteria"]) == jn.LABELS


def test_q1_state_is_the_row_query_verbatim():
    row = {"query": "[coding-core-q1]\nISSUE: x\nRECENT ACTIONS (oldest->newest): read\nLAST: read",
           "answers": [{"name": "next_action", "arguments": {"action": "edit"}}]}
    assert jn.state_of(row, "q1") == row["query"]
    assert jn.gold_of(row) == "edit"
    assert jn.build_request(row)["state"] == row["query"]


def test_q3_states_render_history_then_observation():
    row = {"task": "Fix the parser", "history": ["read", "search"], "target": "edit",
           "observation": "PREVIOUS CALL: str_replace_editor {\"command\": \"view\"}\nRESULT: def parse(): ..."}
    hist = jn.state_of(row, "history")
    assert hist == "[coding-core-q3]\nISSUE: Fix the parser\nRECENT ACTIONS (oldest->newest): read, search\nLAST: search"
    rich = jn.state_of(row, "rich")
    assert rich == hist + "\n" + row["observation"]
    assert jn.gold_of(row) == "edit"
    with pytest.raises(ValueError):
        jn.state_of(row, "q2")


def _run(path, choices, gold, conf=0.3, holdout="h" * 64):
    preds = [{"index": i, "gold": g, "choice": c, "confidence": conf} for i, (c, g) in enumerate(zip(choices, gold))]
    correct = sum(1 for c, g in zip(choices, gold) if c == g)
    path.write_text(json.dumps({"rows": len(gold), "holdout_sha256": holdout, "questions_sha256": "q",
                                "input_tokens": 1, "utc_started": "t", "predictions": preds,
                                "metrics": {"macro_f1": correct / len(gold)}}))
    return path


def test_summary_reports_range_and_per_row_stability(tmp_path):
    gold = ["read", "edit", "search", "read"]
    r1 = _run(tmp_path / "r1.json", ["read", "read", "search", "edit"], gold)
    r2 = _run(tmp_path / "r2.json", ["read", "edit", "search", "edit"], gold)
    out = tmp_path / "summary.json"
    assert js.main(["--label", "t", "--runs", str(r1), str(r2), "--out", str(out)]) == 0
    s = json.loads(out.read_text())
    assert s["top1"] == {"min": 2, "max": 3, "mean": 2.5, "range": 1}
    assert s["stability"]["rows_with_any_change"] == 1 and s["stability"]["rows_stable"] == 3
    assert s["stability"]["rows_always_correct"] == 2 and s["stability"]["rows_ever_correct"] == 3


def test_summary_refuses_runs_on_different_rows(tmp_path):
    gold = ["read", "edit"]
    r1 = _run(tmp_path / "r1.json", ["read", "edit"], gold)
    r2 = _run(tmp_path / "r2.json", ["read", "edit"], gold, holdout="x" * 64)
    with pytest.raises(SystemExit, match="not on the same rows"):
        js.main(["--label", "t", "--runs", str(r1), str(r2), "--out", str(tmp_path / "s.json")])
