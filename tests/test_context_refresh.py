import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike" / "coding_core"))
import context_refresh as refresh
import context_probe as probe
import prepare_openhands as prep
from test_context_probe import source


def fixture_sources():
    ids = {"train": [], "holdout": []}
    for n in range(50):
        issue = f"fixture-{n}"
        ids[prep.split_for(issue, 20)].append(issue)
    a, old, fresh = ids["train"][0], ids["holdout"][0], ids["holdout"][1]
    rows = []
    for issue in (a, old, fresh):
        row = source()
        row.update(instance_id=issue, trajectory_id=issue)
        row["trajectory"][0]["content"] = issue
        rows.append(row)
    return rows, {a}, {old}


def test_fresh_selection_excludes_both_old_partitions_and_duplicates():
    rows, train_ids, old_ids = fixture_sources()
    duplicate = copy.deepcopy(rows[-1])
    duplicate["trajectory_id"] = "another"
    duplicate["trajectory"][0]["content"] = "must not replace first resolved"
    splits, audit = refresh.prepare(rows + [duplicate], train_ids, old_ids)
    assert len(splits["train"]) == len(splits["holdout"]) == 1
    assert splits["train"][0]["q2"]["issue"] in train_ids
    assert splits["holdout"][0]["q2"]["issue"] not in train_ids | old_ids
    assert audit["duplicate_issue_or_trajectory"] == 1
    assert splits["holdout"][0]["q2"]["task"] != "must not replace first resolved"


def test_overlap_in_either_view_is_removed_from_training():
    rows, train_ids, old_ids = fixture_sources()
    rows[-1]["trajectory"] = copy.deepcopy(rows[0]["trajectory"])
    splits, audit = refresh.prepare(rows, train_ids, old_ids)
    assert splits["train"] == []
    assert audit["train_overlap_excluded"] == 1
    with pytest.raises(ValueError):
        refresh.validate(splits, train_ids | old_ids)


def test_selection_and_shuffle_never_consult_targets():
    rows, train_ids, old_ids = fixture_sources()
    splits, _ = refresh.prepare(rows, train_ids, old_ids)
    rows = splits["holdout"]
    chosen = refresh.select(rows)
    changed = copy.deepcopy(rows)
    for pair in changed:
        pair["q2"]["target"] = pair["q3"]["target"] = "git"
    assert [p["q2"]["issue"] for p in refresh.select(changed)] == [p["q2"]["issue"] for p in chosen]
    packet = [dict(case_id=f"case-{n}", task=str(n), observation=str(n), history=["read"])
              for n in range(4)]
    shuffled, count = refresh.shuffle(packet)
    assert count == 4
    assert all(a["history"] == b["history"] and a["task"] != b["task"]
               for a, b in zip(packet, shuffled))
    assert sorted(r["task"] for r in shuffled) == sorted(r["task"] for r in packet)
    assert packet[0]["task"] == "0"


def test_empty_and_old_issue_validation_fails():
    with pytest.raises(ValueError):
        refresh.validate({"train": [], "holdout": []}, set())
    splits = {}
    for split, count in (("train", 1000), ("holdout", 200)):
        splits[split] = [dict(q2=dict(issue=f"{split}-{i % 40}", task=f"{split}-{i}",
                                         observation="q2", history=["read"], target="edit"),
                              q3=dict(issue=f"{split}-{i % 40}", task=f"{split}-{i}",
                                      observation="q3", history=["read"], target="edit"))
                         for i in range(count)]
    refresh.validate(splits, {"train-0"})
    with pytest.raises(ValueError, match="fresh issues"):
        refresh.validate(splits, {"holdout-0"})
    contaminated = copy.deepcopy(splits)
    contaminated["holdout"][0]["q3"] = dict(splits["train"][0]["q2"], issue="holdout-0")
    with pytest.raises(ValueError, match="cross-view"):
        refresh.validate(contaminated, set())


def test_packets_do_not_include_targets_or_identity():
    rows, train_ids, old_ids = fixture_sources()
    splits, _ = refresh.prepare(rows, train_ids, old_ids)
    packets = refresh.packets(refresh.select(splits["holdout"]))
    for arm in ("q2", "q3", "shuffled"):
        assert set(packets[arm][0]) == {"case_id", "task", "observation", "history"}
        assert "target" not in json.dumps(packets[arm])


def test_existing_output_refused(tmp_path):
    with pytest.raises(FileExistsError):
        refresh.main(["--out", str(tmp_path), "--source-run", "missing", "--old-run", "missing"])
