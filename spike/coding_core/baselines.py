#!/usr/bin/env python3
"""Fit and score simple coding-core state/transition classifiers.

Selected from #42 at 18274fc; private mode extends that evaluator without
promoting the MLX research stack. Ordinary prediction semantics are preserved.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import statistics
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


def fit(train):
    if not train:
        raise ValueError("empty training partition")
    targets = collections.Counter(target for _, _, target in train)
    destinations = collections.Counter(target for _, h, target in train if target != h[-1])
    transitions = collections.defaultdict(collections.Counter)
    phase_tables = [collections.defaultdict(collections.Counter) for _ in range(2)]
    for _, history, target in train:
        fine, coarse, previous = phase_keys(history)
        transitions[previous][target] += 1
        phase_tables[0][fine][target] += 1
        phase_tables[1][coarse][target] += 1
    return targets, destinations, transitions, phase_tables


def predict(model, history, exclude_previous=False):
    targets, destinations, transitions, phase_tables = model
    fine, coarse, previous = phase_keys(history)

    def eligible(counter):
        return {k: v for k, v in counter.items()
                if not exclude_previous or k != previous}

    fallback = eligible(destinations if exclude_previous else targets)
    if not fallback:
        raise ValueError("empty action-change destination fallback")
    majority = choose(fallback, targets)
    transition = eligible(transitions.get(previous, {}))
    markov = choose(transition, targets) if transition else majority
    phase = markov
    for table, key in zip(phase_tables, (fine, coarse)):
        counter = eligible(table.get(key, {}))
        if sum(counter.values()) >= MIN_CONTEXT_SUPPORT:
            phase = choose(counter, targets)
            break
    if exclude_previous:
        return {"destination_baseline": majority, "markov_1": markov, "phase_backoff": phase}
    return {"majority": majority, "repeat_last": previous,
            "markov_1": markov, "phase_backoff": phase}


def evaluate(train, holdout):
    if not holdout:
        raise ValueError("empty evaluation partition")
    model = fit(train)
    predictions = collections.defaultdict(list)
    for _, history, target in holdout:
        for name, prediction in predict(model, history).items():
            predictions[name].append(prediction == target)
    result = {
        "train_rows": len(train), "holdout_rows": len(holdout),
        "majority_label": choose(model[0]),
        "transition_states": len(model[2]),
        "metrics": {name: {"correct": sum(hits), "accuracy_pct": 100 * sum(hits) / len(hits)}
                    for name, hits in predictions.items()},
    }
    score = result["metrics"]["phase_backoff"]["accuracy_pct"]
    result["promotion"] = {
        "candidate": "phase_backoff", "gate_accuracy_pct": GATE_ACCURACY_PCT,
        "passed": score >= GATE_ACCURACY_PCT,
    }
    return result


def load_private_splits(path):
    """Audit before fitting. Never return request text or change evaluation membership."""
    partitions = {"train": [], "holdout": []}
    sessions = {k: set() for k in partitions}
    events = set()
    raw_counts = collections.Counter()
    content = {k: set() for k in partitions}
    with path.open() as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            split, session, step = row.get("split"), row.get("session"), row.get("step")
            history, request = row.get("prior_actions"), row.get("recent_user_request")
            if (split not in partitions or not isinstance(session, str) or not session
                    or type(step) is not int or step < 1 or not isinstance(request, str)
                    or not isinstance(history, list) or not history
                    or not all(isinstance(x, str) for x in history)):
                raise ValueError("malformed private pair")
            event = session, step
            if event in events:
                raise ValueError("duplicate event")
            events.add(event)
            sessions[split].add(session)
            raw_counts[split] += 1
            projected = []
            for action in history:
                core = project_canonical(action)
                if core is None:
                    projected.clear()
                else:
                    projected.append(core)
            target = project_canonical(row.get("label"))
            if projected and target is not None:
                signature = hashlib.sha256(json.dumps(
                    [request, history, row["label"]], ensure_ascii=False,
                    separators=(",", ":")).encode()).hexdigest()
                content[split].add(signature)
                partitions[split].append((session, tuple(projected[-12:]), target, signature))
    if sessions["train"] & sessions["holdout"]:
        raise ValueError("session overlap")
    overlap = content["train"] & content["holdout"]
    train = [r[:3] for r in partitions["train"] if r[3] not in overlap]
    holdout = [r[:3] for r in partitions["holdout"]]
    if not train or not holdout:
        raise ValueError("empty eligible partition after overlap filtering")
    audit = {
        "raw_rows": dict(raw_counts), "raw_sessions": {k: len(v) for k, v in sessions.items()},
        "sessions": {"train": len({r[0] for r in train}), "holdout": len({r[0] for r in holdout})},
        "eligible_before_filter": {k: len(v) for k, v in partitions.items()},
        "excluded_train_content_overlap": len(partitions["train"]) - len(train),
        "session_overlap": 0, "duplicate_events": 0, "remaining_content_overlap": 0,
    }
    return train, holdout, audit


def promotion(repeat_accuracy, destination_accuracy, candidates):
    gates = {}
    for name, (overall, conditional) in candidates.items():
        gates[name] = {
            "overall_margin_pp": overall - repeat_accuracy,
            "destination_margin_pp": conditional - destination_accuracy,
            "overall_passed": overall >= repeat_accuracy + 5.0,
            "destination_passed": conditional >= destination_accuracy + 10.0,
        }
        gates[name]["passed"] = gates[name]["overall_passed"] and gates[name]["destination_passed"]
    passed = any(g["passed"] for g in gates.values())
    partial = any(g["overall_passed"] or g["destination_passed"] for g in gates.values())
    return {"families": gates, "passed": passed,
            "decision": "design_prospective" if passed else "consider_run_endings" if partial else "stop"}


def evaluate_private(train, holdout):
    if not holdout:
        raise ValueError("empty evaluation partition")
    if not any(h[-1] != y for _, h, y in holdout):
        raise ValueError("empty action-change evaluation slice")
    model = fit(train)
    hits = {scope: collections.defaultdict(list)
            for scope in ("overall", "change_ordinary", "change_excluded")}
    per_session = {scope: collections.defaultdict(lambda: collections.defaultdict(list))
                   for scope in hits}
    for session, history, target in holdout:
        ordinary = predict(model, history)
        scopes = {"overall": ordinary}
        if target != history[-1]:
            scopes.update(change_ordinary=ordinary,
                          change_excluded=predict(model, history, True))
        for scope, predictions in scopes.items():
            for name, predicted in predictions.items():
                correct = predicted == target
                hits[scope][name].append(correct)
                per_session[scope][name][session].append(correct)
    result = {}
    for scope, values in hits.items():
        result[scope] = {name: {"rows": len(v), "correct": sum(v),
                                "accuracy_pct": 100 * sum(v) / len(v)} for name, v in values.items()}
    # Private receipt only: do not publish these distributions or session-level values.
    result["per_session"] = {}
    for scope, values in per_session.items():
        result["per_session"][scope] = {}
        for name, grouped in values.items():
            scores = sorted(100 * sum(v) / len(v) for v in grouped.values())
            result["per_session"][scope][name] = {
                "sessions": len(scores), "min": min(scores), "median": statistics.median(scores),
                "max": max(scores), "mean": statistics.mean(scores), "accuracy_distribution": scores,
            }
    result["train_rows"] = len(train)
    result["train_label_counts"] = dict(collections.Counter(y for _, _, y in train))
    result["holdout_label_counts"] = dict(collections.Counter(y for _, _, y in holdout))
    result["promotion"] = promotion(
        result["overall"]["repeat_last"]["accuracy_pct"],
        result["change_excluded"]["destination_baseline"]["accuracy_pct"],
        {name: (result["overall"][name]["accuracy_pct"],
                result["change_excluded"][name]["accuracy_pct"])
         for name in ("markov_1", "phase_backoff")})
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", type=Path)
    ap.add_argument("--private-pairs", type=Path,
                    help="fit private train and score fixed holdout; output must stay private")
    holdout = ap.add_mutually_exclusive_group()
    holdout.add_argument("--holdout", type=Path)
    holdout.add_argument("--oracle-pairs", type=Path,
                         help="private canonical pairs JSONL; scores holdout rows only")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.private_pairs:
        if args.train or args.holdout or args.oracle_pairs:
            ap.error("--private-pairs cannot be combined with other input modes")
        if args.out.exists():
            raise SystemExit("refusing to overwrite receipt")
        before = digest(args.private_pairs)
        train, evaluation, audit = load_private_splits(args.private_pairs)
        if len(evaluation) != 23442 or audit["sessions"]["holdout"] != 63:
            raise ValueError("fixed evaluation manifest mismatch: expected 23442 rows / 63 sessions")
        result = evaluate_private(train, evaluation)
        if before != digest(args.private_pairs):
            raise ValueError("input changed during run")
        result.update(audit=audit, input_sha256=before, code_sha256=digest(Path(__file__)),
                      evidence_status="reused development evaluation; not human acceptance")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x") as fh:
            fh.write(json.dumps(result, indent=2) + "\n")
        print(json.dumps({k: result[k] for k in ("overall", "change_ordinary", "change_excluded", "promotion")}, indent=2))
        return 0 if result["promotion"]["passed"] else 1
    if not args.train or not (args.holdout or args.oracle_pairs):
        ap.error("provide --private-pairs or --train and one evaluation source")
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
