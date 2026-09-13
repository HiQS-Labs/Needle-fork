#!/usr/bin/env python3
"""#62: one frozen, CPU-only shortlist kill test; no serving or model calls.

Reuses training counters without changing old top-one behavior. Locks predictions
before scoring. Replays only locked predictions, never fits/tunes a second model.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import baselines
import context_probe as probe
import context_refresh as refresh

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "TESTS-RESULTS/2026-09-12-context-refresh/manifest.json"
LABELS = tuple(sorted(probe.LABELS))
CONTROLS = ("static", "markov", "repeat_last")
ARMS = CONTROLS + ("phase", "shuffled_phase")
SEED = "shortlist-v1"
MAX_BYTES = 64 * 1024 ** 2  # per split; observed inputs together ~45 MiB


def read_json(path):
    return json.loads(path.read_text())


def load_data(directory, manifest):
    """Expected hashes come from the retained trusted manifest, not the input."""
    if manifest.get("format") != "coding-core-q3-paired-v1":
        raise ValueError("wrong paired format")
    splits = {}
    identities = set()
    for split in ("train", "holdout"):
        path = directory / (split + ".jsonl")
        if not 0 < path.stat().st_size <= MAX_BYTES:
            raise ValueError("empty or oversized split")
        if baselines.digest(path) != manifest["hashes"][path.name]:
            raise ValueError("trusted input hash mismatch")
        rows = []
        with path.open() as fh:
            for line in fh:
                p = json.loads(line)
                a, b = p["q2"], p["q3"]
                if any(a[f] != b[f] for f in ("issue", "history", "target")):
                    raise ValueError("paired view mismatch")
                identity = (p["source_line"], p["transition_index"])
                if (any(type(x) is not int for x in identity) or identity[0] < 1
                        or identity[1] < 0 or identity in identities):
                    raise ValueError("duplicate or invalid row identity")
                identities.add(identity)
                if not isinstance(a["issue"], str) or not a["issue"]:
                    raise ValueError("empty issue identity")
                rows.append(p)
                if len(rows) > manifest["counts"][split]["rows"]:
                    raise ValueError("row count exceeds manifest")
                probe.check_memory()
        q2 = [p["q2"] for p in rows]
        counts = dict(rows=len(rows), issues=len({r["issue"] for r in q2}),
                      labels=dict(Counter(r["target"] for r in q2)))
        if counts != manifest["counts"][split] or set(counts["labels"]) != set(LABELS):
            raise ValueError("count or label support mismatch")
        splits[split] = rows
    # Reuse the existing schema, issue/feature separation and cross-view guards.
    refresh.validate(splits, {p["q2"]["issue"] for p in splits["train"]})
    return {s: [p["q2"] for p in rows] for s, rows in splits.items()}


def ranked(counter, priors):
    order = sorted(counter, key=lambda x: (-counter[x], -priors.get(x, 0), x))
    fallback = sorted(priors, key=lambda x: (-priors[x], x))
    return list(dict.fromkeys(order + fallback))[:3]


def predict(model, history):
    targets, _, transitions, tables = model
    fine, coarse, last = baselines.phase_keys(history)
    counter = transitions.get(last, {}) or targets
    phase = counter
    for table, key in zip(tables, (fine, coarse)):
        candidate = table.get(key, {})
        if sum(candidate.values()) >= baselines.MIN_CONTEXT_SUPPORT:
            phase = candidate
            break
    static = ranked(targets, targets)
    return dict(static=static, markov=ranked(counter, targets),
                repeat_last=list(dict.fromkeys([last] + ranked(targets, targets)))[:3],
                phase=ranked(phase, targets))


def shuffled_histories(histories):
    if len(histories) < 2:
        raise ValueError("shuffle needs at least two histories")
    order = sorted(range(len(histories)), key=lambda i: hashlib.sha256(
        f"{SEED}:{i}".encode()).hexdigest())
    result = list(histories)
    for i, j in zip(order, order[1:] + order[:1]):
        result[i] = histories[j]
    return result


def validate_predictions(rows, predictions):
    if not rows or len(predictions) != len(rows):
        raise ValueError("empty or incomplete predictions")
    for item in predictions:
        if set(item) != set(ARMS):
            raise ValueError("wrong arms")
        for labels in item.values():
            if (not isinstance(labels, list) or len(labels) != 3
                    or len(set(labels)) != 3 or not set(labels) <= set(LABELS)):
                raise ValueError("invalid three-label shortlist")


def metrics(rows, predictions):
    if not rows or len(rows) != len(predictions):
        raise ValueError("empty or incomplete metric input")
    issues = defaultdict(lambda: [0, 0])
    support, correct = Counter(), Counter()
    hit1 = hit3 = 0
    for r, labels in zip(rows, predictions):
        hit = int(r["target"] in labels)
        hit1 += int(r["target"] == labels[0])
        hit3 += hit
        issues[r["issue"]][0] += hit
        issues[r["issue"]][1] += 1
        support[r["target"]] += 1
        correct[r["target"]] += hit
    issue_mean = sum(Fraction(a, b) for a, b in issues.values()) / len(issues)
    recall = {a: Fraction(correct[a], support[a]) if support[a] else Fraction(0)
              for a in LABELS}
    return dict(rows=len(rows), issues=len(issues), correct_at1=hit1, correct_at3=hit3,
                hit_at1_pct=100 * hit1 / len(rows), hit_at3_pct=100 * hit3 / len(rows),
                issue_macro_hit_at3_pct=float(100 * issue_mean),
                macro_recall_at3_pct=float(100 * sum(recall.values()) / len(LABELS)),
                per_label={a: dict(rows=support[a], correct_at3=correct[a],
                                   recall_at3_pct=float(100 * recall[a]) if support[a] else None)
                           for a in LABELS}, per_issue=dict(issues))


def issue_mean(m):
    return sum(Fraction(a, b) for a, b in m["per_issue"].values()) / m["issues"]


def macro_recall(m):
    return sum(Fraction(v["correct_at3"], v["rows"]) if v["rows"] else Fraction(0)
               for v in m["per_label"].values()) / len(LABELS)


def compare(candidate, control):
    if set(candidate["per_issue"]) != set(control["per_issue"]):
        raise ValueError("different scored issues")
    result = Counter(wins=0, ties=0, losses=0)
    for issue, (hits, n) in candidate["per_issue"].items():
        other, size = control["per_issue"][issue]
        if n != size:
            raise ValueError("different scored rows")
        result["wins" if hits > other else "losses" if hits < other else "ties"] += 1
    return dict(result)


def summarize(rows, predictions):
    validate_predictions(rows, predictions)
    overall = {a: metrics(rows, [p[a] for p in predictions]) for a in ARMS}
    changes = [i for i, r in enumerate(rows) if r["target"] != r["history"][-1]]
    if not changes:
        raise ValueError("empty action-change slice")
    change = {a: metrics([rows[i] for i in changes], [predictions[i][a] for i in changes])
              for a in ARMS}
    best = min(CONTROLS, key=lambda a: (-issue_mean(overall[a]), -macro_recall(overall[a]), a))
    candidate, control = overall["phase"], overall[best]
    comparisons = {a: compare(candidate, overall[a]) for a in CONTROLS}
    margin = 100 * (issue_mean(candidate) - issue_mean(control))
    recall_margin = 100 * (macro_recall(candidate) - macro_recall(control))
    # #62: these are exploratory kill gates, NOT human acceptance or a serving gate.
    gates = dict(lift=margin >= 5, macro_recall=recall_margin >= 0,
                 issue_wins=comparisons[best]["wins"] > comparisons[best]["losses"])
    return dict(overall=overall, action_changes=change, issue_comparisons=comparisons,
                strongest_control=best, margin_pp=float(margin),
                macro_recall_margin_pp=float(recall_margin), gates=gates,
                passed=all(gates.values()),
                decision="consider_interaction_study_only" if all(gates.values()) else "park",
                evidence="reused public development data; not human usefulness")


def public_metrics(result):
    return {k: ({a: {f: v for f, v in m.items() if f != "per_issue"}
                 for a, m in value.items()} if k in ("overall", "action_changes") else value)
            for k, value in result.items()}


def score_locked(data, out):
    lock = read_json(out / "lock.json")
    if baselines.digest(MANIFEST) != lock["manifest_sha256"]:
        raise ValueError("manifest changed after prediction lock")
    if baselines.digest(out / "predictions.json") != lock["predictions_sha256"]:
        raise ValueError("predictions changed after lock")
    splits = load_data(data, read_json(MANIFEST))
    return summarize(splits["holdout"], read_json(out / "predictions.json"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args(argv)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("600-second cap")))
    signal.alarm(600)
    start = time.monotonic()
    try:
        if args.replay:
            result = public_metrics(score_locked(args.data, args.out))
            saved = read_json(args.out / "metrics.json")
            if result != saved:
                raise ValueError("score replay mismatch")
            print("Locked score replay matches")
            return 0
        args.out.mkdir(parents=True, exist_ok=False)
        guard = probe.configure_memory()
        manifest = read_json(MANIFEST)
        splits = load_data(args.data, manifest)
        model = baselines.fit([(r["issue"], tuple(r["history"]), r["target"])
                               for r in splits["train"]])
        histories = [r["history"] for r in splits["holdout"]]
        shuffled = shuffled_histories(histories)
        predictions = []
        for history, null_history in zip(histories, shuffled):
            p = predict(model, history)
            old = baselines.predict(model, history)
            if any(p[a][0] != old[b] for a, b in (
                    ("phase", "phase_backoff"), ("static", "majority"),
                    ("markov", "markov_1"), ("repeat_last", "repeat_last"))):
                raise ValueError("old rank-one parity mismatch")
            predictions.append(dict(p, shuffled_phase=predict(model, null_history)["phase"]))
            probe.check_memory()
        validate_predictions(splits["holdout"], predictions)
        refresh.write_json(args.out / "predictions.json", predictions)
        refresh.write_json(args.out / "lock.json", dict(
            manifest_sha256=baselines.digest(MANIFEST),
            predictions_sha256=baselines.digest(args.out / "predictions.json"),
            code_sha256={name: baselines.digest(Path(__file__).parent / name) for name in (
                "shortlist_eval.py", "baselines.py", "context_refresh.py", "context_probe.py")},
            shuffle_seed=SEED, shuffle_changed=sum(a != b for a, b in zip(histories, shuffled)),
            rows=len(histories), rank_one_parity=True, memory=guard))
        del splits, model
        result = score_locked(args.data, args.out)
        refresh.write_json(args.out / "private-metrics.json", result)
        refresh.write_json(args.out / "metrics.json", public_metrics(result))
        refresh.write_json(args.out / "resources.json", dict(
            runtime_seconds=time.monotonic() - start, peak_rss_bytes=probe.peak_rss()))
        print(json.dumps(public_metrics(result), indent=2))
        return 0 if result["passed"] else 1
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
