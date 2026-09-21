#!/usr/bin/env python3
"""Build q3 (richer-state) rows for exactly the instances the #42/#66 pilot used (GH-77 C).

Offline research script, not part of the installed `needle` runtime. Replays the pilot's
selection — first 100 source trajectories at the pinned dataset revision, resolved only, split by
`sha256(instance_id)` before caps, 500 train / 100 holdout counted in the q1 projection — to
recover the same 11 train and 2 holdout instances, then projects those trajectories with
`prepare_openhands.trajectory_rows(..., context="q3")`: issue text (<= 2,000 chars), the history
of broad actions, and the last completed call plus its result (<= 2,000 chars). The same caps
are applied in order to the q3 rows. The q3 holdout is therefore the same two instances as the
pilot holdout but not the same 100 rows (q3 skips calls without a matched result), and the
receipt must say so.

Also fits the #48 action baselines on the q3 train rows and scores them on the q3 holdout, so
Jev's richer-state runs are compared against baselines computed on the same rows.

    python spike/coding_core/q3_rows.py --out data/coding-core/q3

Writes q3-train.jsonl, q3-holdout.jsonl (ignored data), q3-provenance.json and q3-baselines.json
(aggregates and per-row index/gold/prediction only).
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import baselines  # noqa: E402
import prepare_openhands as prep  # noqa: E402

CAPS = {"train": 500, "holdout": 100}
MAX_TRAJECTORIES = 100
HOLDOUT_PCT = 20


def select_pilot_instances(rows):
    """Replay prepare()'s loop with the q1 projection; yield (split, source) for kept instances."""
    schemas = json.loads((Path(prep.__file__).with_name("labels.json")).read_text())["schemas"]
    counts = collections.Counter()
    seen = 0
    for source in rows:
        seen += 1
        if seen > MAX_TRAJECTORIES:
            break
        if source.get("resolved") != 1:
            counts["unresolved_skipped"] += 1
            continue
        split = prep.split_for(source.get("instance_id"), HOLDOUT_PCT)
        if counts[f"rows_{split}"] >= CAPS[split]:
            if counts["rows_train"] >= CAPS["train"] and counts["rows_holdout"] >= CAPS["holdout"]:
                break
            continue
        made = prep.trajectory_rows(source, schemas)
        room = CAPS[split] - counts[f"rows_{split}"]
        taken = made[:room]
        counts[f"rows_{split}"] += len(taken)
        if taken:
            yield split, source
    counts["trajectories_seen"] = seen - (1 if seen > MAX_TRAJECTORIES else 0)
    select_pilot_instances.counts = dict(counts)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--input-jsonl", type=Path, help="offline fixture instead of HF streaming")
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists")
    audit = collections.Counter()
    q3 = {"train": [], "holdout": []}
    instances = {"train": [], "holdout": []}
    q3_full = collections.Counter()
    for split, source in select_pilot_instances(prep.source_rows(a.input_jsonl, 0)):
        made = prep.trajectory_rows(source, [], context="q3", audit=audit)
        q3_full[split] += len(made)
        room = CAPS[split] - len(q3[split])
        taken = made[:room]
        for r in taken:
            q3[split].append(dict(r, issue=source["instance_id"]))
        instances[split].append(source["instance_id"])
    if set(instances["train"]) & set(instances["holdout"]):
        raise SystemExit("instance leakage between train and holdout")
    if not q3["train"] or not q3["holdout"]:
        raise SystemExit("empty q3 split")
    a.out.mkdir(parents=True)
    paths = {}
    for split, rows in q3.items():
        paths[split] = a.out / f"q3-{split}.jsonl"
        with paths[split].open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    support = {s: dict(sorted(collections.Counter(r["target"] for r in rows).items())) for s, rows in q3.items()}
    provenance = {
        "format_version": "coding-core-q3", "dataset": prep.DATASET, "dataset_revision": prep.REVISION,
        "selection": {"max_trajectories": MAX_TRAJECTORIES, "holdout_pct": HOLDOUT_PCT, "caps": CAPS,
                      "q1_replay_counts": select_pilot_instances.counts},
        "instances": {s: len(v) for s, v in instances.items()},
        "q3_rows_before_cap": dict(q3_full), "q3_rows": {s: len(v) for s, v in q3.items()},
        "q3_audit": dict(audit), "support": support,
        "state_chars": {s: {"task_max": max(len(r["task"]) for r in rows),
                            "observation_max": max(len(r["observation"]) for r in rows),
                            "observation_median": sorted(len(r["observation"]) for r in rows)[len(rows) // 2]}
                        for s, rows in q3.items()},
        "outputs": {s: {"path": p.name, "sha256": sha256(p)} for s, p in paths.items()},
    }
    (a.out / "q3-provenance.json").write_text(json.dumps(provenance, indent=1, sort_keys=True) + "\n")

    # Baselines fitted on the q3 train rows, scored on the q3 holdout rows (same rows Jev sees).
    model = baselines.fit([(r["issue"], tuple(r["history"]), r["target"]) for r in q3["train"]])
    per_row = []
    hits = collections.Counter()
    for i, r in enumerate(q3["holdout"]):
        preds = baselines.predict(model, tuple(r["history"]))
        per_row.append({"index": i, "gold": r["target"], **preds})
        for name, label in preds.items():
            hits[name] += int(label == r["target"])
    n = len(q3["holdout"])
    result = {"train_rows": len(q3["train"]), "holdout_rows": n,
              "metrics": {name: {"correct": hits[name], "accuracy_pct": 100.0 * hits[name] / n}
                          for name in sorted(hits)},
              "holdout_sha256": sha256(paths["holdout"]), "train_sha256": sha256(paths["train"]),
              "predictions": per_row}
    (a.out / "q3-baselines.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: provenance[k] for k in ("instances", "q3_rows_before_cap", "q3_rows", "q3_audit", "support", "state_chars")}, indent=1))
    print(json.dumps(result["metrics"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
