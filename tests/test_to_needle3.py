"""GH-66: pilot rows -> Needle 3 one-enum-tool fine-tune rows."""
import json
from pathlib import Path
import sys

import pytest

CORE = Path(__file__).resolve().parents[1] / "spike" / "coding_core"
sys.path.insert(0, str(CORE))
import to_needle3 as conv  # noqa: E402

LABELS, DESCRIPTIONS = conv.load_labels()
TOOL = conv.next_action_tool(LABELS, DESCRIPTIONS)


def pilot_row(label, query="[coding-core-q1]\nISSUE: x\nRECENT ACTIONS (oldest->newest): read\nLAST: read"):
    return {"query": query, "tools": [{"name": n} for n in LABELS],
            "answers": [{"name": label}], "reasoning": f"LAST: read -> {label}",
            "system": "Given the issue and recent coding actions, predict the single best next broad action."}


def test_enum_covers_exactly_the_six_labels():
    enum = TOOL["parameters"]["properties"]["action"]["enum"]
    assert enum == LABELS == sorted(LABELS)
    assert set(enum) == set(json.loads((CORE / "labels.json").read_text())["labels"])
    assert TOOL["parameters"]["required"] == ["action"]
    for name in LABELS:  # every label's meaning travels in the constant tool text
        assert DESCRIPTIONS[name].rstrip(".") in TOOL["parameters"]["properties"]["action"]["description"]


@pytest.mark.parametrize("label", LABELS)
def test_row_keeps_query_and_system_and_reshapes_the_answer(label):
    out = conv.convert_row(pilot_row(label), LABELS, TOOL)
    assert out["query"] == pilot_row(label)["query"]
    assert out["system"] == pilot_row(label)["system"]
    assert out["tools"] == [TOOL]
    assert out["answers"] == [{"name": "next_action", "arguments": {"action": label}}]
    assert "reasoning" not in out


def test_unknown_label_is_refused():
    with pytest.raises(conv.InputError, match="unknown label"):
        conv.convert_row(pilot_row("deploy"), LABELS, TOOL)


def test_abstention_and_multi_answer_rows_are_refused():
    row = pilot_row("read")
    row["answers"] = []
    with pytest.raises(conv.InputError, match="exactly one answer"):
        conv.convert_row(row, LABELS, TOOL)
    row["answers"] = [{"name": "read"}, {"name": "edit"}]
    with pytest.raises(conv.InputError, match="exactly one answer"):
        conv.convert_row(row, LABELS, TOOL)


def test_row_count_is_preserved_and_support_reported(tmp_path):
    src = tmp_path / "pilot"
    src.mkdir()
    rows = [pilot_row(l) for l in ("read", "read", "edit", "git", "search", "run_tests", "run_command")]
    for split, take in (("train", rows), ("holdout", rows[:3])):
        (src / f"pilot-{split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in take))
    out = tmp_path / "out"
    assert conv.main([str(src), "--out", str(out), "--skip-token-stats"]) == 0
    report = json.loads((out / "preflight.json").read_text())
    assert report["splits"]["train"]["converted_rows"] == 7
    assert report["splits"]["holdout"]["converted_rows"] == 3
    assert report["splits"]["train"]["support"] == {"edit": 1, "git": 1, "read": 2, "run_command": 1,
                                                    "run_tests": 1, "search": 1}
    assert report["splits"]["train"]["labels_with_zero_training_rows"] == []
    assert report["preflight_failures"] == []
    written = [json.loads(l) for l in (out / "needle3-train.jsonl").read_text().splitlines()]
    assert len(written) == 7 and all(w["tools"] == [TOOL] for w in written)


def test_zero_training_support_is_a_preflight_failure(tmp_path):
    src = tmp_path / "pilot"
    src.mkdir()
    rows = [pilot_row(l) for l in ("read", "edit", "search", "run_tests", "run_command")]  # no git
    for split in ("train", "holdout"):
        (src / f"pilot-{split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    out = tmp_path / "out"
    assert conv.main([str(src), "--out", str(out), "--skip-token-stats"]) == 1
    assert json.loads((out / "preflight.json").read_text())["preflight_failures"] == ["train: zero-support labels git"]


def test_bad_row_fails_closed(tmp_path):
    src = tmp_path / "pilot"
    src.mkdir()
    (src / "pilot-train.jsonl").write_text(json.dumps(pilot_row("read")) + "\n" + json.dumps(pilot_row("nope")) + "\n")
    (src / "pilot-holdout.jsonl").write_text(json.dumps(pilot_row("read")) + "\n")
    assert conv.main([str(src), "--out", str(tmp_path / "out"), "--skip-token-stats"]) == 2
