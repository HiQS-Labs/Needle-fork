#!/usr/bin/env python3
"""Fit and score majority, repeat-last, and order-1 Markov baselines."""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import re

LAST = re.compile(r"^LAST: (\S+)$", re.MULTILINE)


def load(path: Path):
    rows = []
    with path.open() as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            answers = row.get("answers")
            match = LAST.search(row.get("query", ""))
            if not isinstance(answers, list) or len(answers) != 1 or not match:
                raise ValueError(f"{path}:{lineno}: malformed supervised row")
            label = answers[0].get("name")
            if not isinstance(label, str) or not label:
                raise ValueError(f"{path}:{lineno}: invalid target")
            rows.append((match.group(1), label))
    if not rows:
        raise ValueError(f"{path}: no examples")
    return rows


def choose(counter):
    return min(counter, key=lambda x: (-counter[x], x))


def evaluate(train, holdout):
    targets = collections.Counter(target for _, target in train)
    majority = choose(targets)
    transitions = collections.defaultdict(collections.Counter)
    for previous, target in train:
        transitions[previous][target] += 1
    predictions = {"majority": [], "repeat_last": [], "markov_1": []}
    for previous, target in holdout:
        predictions["majority"].append(majority == target)
        predictions["repeat_last"].append(previous == target)
        pred = choose(transitions[previous]) if previous in transitions else majority
        predictions["markov_1"].append(pred == target)
    return {
        "train_rows": len(train), "holdout_rows": len(holdout),
        "majority_label": majority,
        "transition_states": len(transitions),
        "metrics": {name: {"correct": sum(hits), "accuracy_pct": 100 * sum(hits) / len(hits)}
                    for name, hits in predictions.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--holdout", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result = evaluate(load(args.train), load(args.holdout))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
