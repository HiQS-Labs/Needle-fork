#!/usr/bin/env python3
"""Fit and score simple coding-core state/transition classifiers."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "utils" / "corpus"))
import taxonomy  # noqa: E402

ISSUE = re.compile(r"^ISSUE: (.+)$", re.MULTILINE)
RECENT = re.compile(r"^RECENT ACTIONS \(oldest->newest\): (.+)$", re.MULTILINE)
LAST = re.compile(r"^LAST: (\S+)$", re.MULTILINE)
GATE_ACCURACY_PCT = 42.0
MIN_CONTEXT_SUPPORT = 2
CODE_PROJECTION = {
    "read_file": "read", "search_code": "search", "find_files": "search",
    "apply_patch": "edit", "run_tests": "run_tests", "run_build": "run_tests",
    "run_linter": "run_tests",
}
BREAK_GROUP = "control"


def load(path: Path):
    rows = []
    with path.open() as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            answers = row.get("answers")
            query = row.get("query", "")
            issue = ISSUE.search(query)
            recent = RECENT.search(query)
            last = LAST.search(query)
            if (not isinstance(answers, list) or len(answers) != 1
                    or not issue or not recent or not last):
                raise ValueError(f"{path}:{lineno}: malformed supervised row")
            label = answers[0].get("name")
            if not isinstance(label, str) or not label:
                raise ValueError(f"{path}:{lineno}: invalid target")
            history = tuple(recent.group(1).split(", "))
            if not history or any(not action for action in history) or history[-1] != last.group(1):
                raise ValueError(f"{path}:{lineno}: inconsistent recent actions")
            rows.append((issue.group(1), history, label))
    if not rows:
        raise ValueError(f"{path}: no examples")
    return rows


def project_canonical(label):
    if label not in taxonomy.LABELS_V1:
        raise ValueError(f"unknown canonical label: {label!r}")
    if taxonomy.LABELS_V1[label]["group"] == BREAK_GROUP:
        return None
    if taxonomy.LABELS_V1[label]["group"] == "git":
        return "git"
    return CODE_PROJECTION.get(label, "run_command")


def load_oracle_pairs(path: Path):
    rows = []
    sessions = set()
    with path.open() as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("split") != "holdout":
                continue
            history = row.get("prior_actions")
            issue = row.get("recent_user_request")
            session = row.get("session")
            if (not isinstance(history, list) or not all(isinstance(x, str) for x in history)
                    or not isinstance(issue, str) or not isinstance(session, str)):
                raise ValueError(f"{path}:{lineno}: malformed Oracle pair")
            projected = []
            for action in history:
                core = project_canonical(action)
                if core is None:
                    projected.clear()
                else:
                    projected.append(core)
            target = project_canonical(row.get("label"))
            if projected and target is not None:
                rows.append((issue, tuple(projected[-12:]), target))
                sessions.add(session)
    if not rows:
        raise ValueError(f"{path}: no eligible holdout examples")
    return rows, len(sessions)


def choose(counter, priors=None):
    priors = priors or {}
    return min(counter, key=lambda x: (-counter[x], -priors.get(x, 0), x))


def phase_keys(history):
    last = history[-1]
    edited_before_last = "edit" in history[:-1]
    penultimate = history[-2] if len(history) > 1 else None
    return (last, edited_before_last, penultimate), (last, edited_before_last), last


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(train, holdout):
    targets = collections.Counter(target for _, _, target in train)
    majority = choose(targets)
    transitions = collections.defaultdict(collections.Counter)
    phase_tables = [collections.defaultdict(collections.Counter) for _ in range(2)]
    for _, history, target in train:
        fine, coarse, previous = phase_keys(history)
        transitions[previous][target] += 1
        phase_tables[0][fine][target] += 1
        phase_tables[1][coarse][target] += 1
    predictions = {"majority": [], "repeat_last": [], "markov_1": [], "phase_backoff": []}
    for _, history, target in holdout:
        fine, coarse, previous = phase_keys(history)
        predictions["majority"].append(majority == target)
        predictions["repeat_last"].append(previous == target)
        markov = choose(transitions[previous], targets) if previous in transitions else majority
        predictions["markov_1"].append(markov == target)
        phase = markov
        for table, key in zip(phase_tables, (fine, coarse)):
            if sum(table[key].values()) >= MIN_CONTEXT_SUPPORT:
                phase = choose(table[key], targets)
                break
        predictions["phase_backoff"].append(phase == target)
    result = {
        "train_rows": len(train), "holdout_rows": len(holdout),
        "majority_label": majority,
        "transition_states": len(transitions),
        "metrics": {name: {"correct": sum(hits), "accuracy_pct": 100 * sum(hits) / len(hits)}
                    for name, hits in predictions.items()},
    }
    score = result["metrics"]["phase_backoff"]["accuracy_pct"]
    result["promotion"] = {
        "candidate": "phase_backoff", "gate_accuracy_pct": GATE_ACCURACY_PCT,
        "passed": score >= GATE_ACCURACY_PCT,
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", type=Path, required=True)
    holdout = ap.add_mutually_exclusive_group(required=True)
    holdout.add_argument("--holdout", type=Path)
    holdout.add_argument("--oracle-pairs", type=Path,
                         help="private canonical pairs JSONL; scores holdout rows only")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.oracle_pairs:
        evaluation, session_count = load_oracle_pairs(args.oracle_pairs)
        evaluation_info = {"kind": "private_oracle_projection", "sessions": session_count}
        evaluation_path = args.oracle_pairs
    else:
        evaluation = load(args.holdout)
        evaluation_info = {"kind": "coding_core_jsonl"}
        evaluation_path = args.holdout
    result = evaluate(load(args.train), evaluation)
    if args.oracle_pairs:
        private_gate = result["metrics"]["markov_1"]["accuracy_pct"] + 5.0
        result["promotion"] = {
            "candidate": "phase_backoff", "gate_accuracy_pct": private_gate,
            "margin_over_markov_pct": 5.0,
            "passed": result["metrics"]["phase_backoff"]["accuracy_pct"] >= private_gate,
        }
    result["evaluation"] = evaluation_info
    result["inputs"] = {
        "train_sha256": digest(args.train),
        "holdout_sha256": digest(evaluation_path),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["promotion"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
