#!/usr/bin/env python3
"""Bounded #51 CPU-only OpenHands context probe. All output stays in a fresh private directory.

Uses existing projection and action baselines; never executes source tool calls.
No dependencies beyond the standard library; no classifier or feature search.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import re
import resource
import signal
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import baselines
import prepare_openhands as prep

OFFSET, PAGES, PAGE_SIZE = 1000, 10, 100
RESPONSE_LIMIT = 32 * 1024 * 1024
CAPS = {"train": 10000, "holdout": 3000}
VOCAB_LIMIT = 20000
LABELS = prep.LABELS


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(RESPONSE_LIMIT + 1)
    if len(raw) > RESPONSE_LIMIT:
        raise ValueError("source response exceeds 32 MiB cap")
    return json.loads(raw)


def check_revision():
    got = fetch_json(f"https://huggingface.co/api/datasets/{prep.DATASET}").get("sha")
    if got != prep.REVISION:
        raise ValueError("source revision differs from frozen protocol")


def acquire(out):
    check_revision()
    count = 0
    path = out / "source.jsonl"
    with path.open("x") as fh:
        for page in range(PAGES):
            offset = OFFSET + PAGE_SIZE * page
            query = urllib.parse.urlencode(dict(dataset=prep.DATASET, config="default",
                                               split="train", offset=offset, length=PAGE_SIZE))
            payload = fetch_json("https://datasets-server.huggingface.co/rows?" + query)
            rows = payload.get("rows")
            if not isinstance(rows, list) or len(rows) != PAGE_SIZE:
                raise ValueError("source page is empty or incomplete")
            for i, wrapped in enumerate(rows):
                if (not isinstance(wrapped, dict) or wrapped.get("row_idx") != offset + i
                        or wrapped.get("truncated_cells") or not isinstance(wrapped.get("row"), dict)):
                    raise ValueError("truncated or misaligned source row")
                fh.write(json.dumps(wrapped["row"], ensure_ascii=False) + "\n")
                count += 1
            print(f"acquired {count} trajectories", flush=True)
    check_revision()
    return path


def signature(row):
    # Target/identity are deliberately absent: duplicated inputs can leak across different labels.
    text = json.dumps([row["task"], row["observation"], row["history"]],
                      ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def prepare(source):
    splits = {key: [] for key in CAPS}
    seen_issues, seen_trajectories = set(), set()
    audit = Counter()
    for row in source:
        audit["source_rows"] += 1
        if audit["source_rows"] > PAGES * PAGE_SIZE:
            raise ValueError("source exceeds frozen trajectory cap")
        if row.get("resolved") != 1:
            audit["unresolved_skipped"] += 1
            continue
        issue, trajectory = row.get("instance_id"), row.get("trajectory_id")
        if not isinstance(trajectory, str) or not trajectory:
            raise ValueError("missing trajectory ID")
        split = prep.split_for(issue, 20)
        if issue in seen_issues or trajectory in seen_trajectories:
            audit["duplicate_issue_or_trajectory"] += 1
            continue
        seen_issues.add(issue)
        seen_trajectories.add(trajectory)
        room = min(50, CAPS[split] - len(splits[split]))
        if room <= 0:
            audit["split_cap_skipped"] += 1
            continue
        made = prep.trajectory_rows(row, [], context=True, audit=audit)
        for example in made[:room]:
            splits[split].append(dict(example, issue=issue))
        audit["row_cap_excluded"] += max(0, len(made) - room)
    forbidden = {signature(row) for row in splits["holdout"]}
    before = len(splits["train"])
    splits["train"] = [row for row in splits["train"] if signature(row) not in forbidden]
    audit["train_input_overlap_excluded"] = before - len(splits["train"])
    return splits, dict(audit)


def validate(splits):
    train, evaluation = splits["train"], splits["holdout"]
    if len(train) < 1000 or len(evaluation) < 200:
        raise ValueError("insufficient examples: need 1000 train / 200 evaluation")
    issues = {s: {r["issue"] for r in rows} for s, rows in splits.items()}
    if issues["train"] & issues["holdout"]:
        raise ValueError("issue overlap")
    if len(issues["holdout"]) < 10:
        raise ValueError("need 10 evaluation issues")
    if {signature(r) for r in train} & {signature(r) for r in evaluation}:
        raise ValueError("feature-input overlap")
    for rows in splits.values():
        for r in rows:
            if (r["target"] not in LABELS or not 1 <= len(r["history"]) <= 12
                    or any(a not in LABELS for a in r["history"])
                    or not r["task"] or not r["observation"]):
                raise ValueError("invalid example")


def features(row, context):
    tokens = {f"action:{i}:{a}" for i, a in enumerate(reversed(row["history"]))}
    if context:
        for field in ("task", "observation"):
            tokens.update(field + ":" + w for w in re.findall(r"\b\w+\b", row[field].lower()))
    return tokens


def fit_nb(rows, context):
    if not rows:
        raise ValueError("empty training data")
    documents = [(features(r, context), r["target"]) for r in rows]
    frequency = Counter(t for tokens, _ in documents for t in tokens)
    vocabulary = set(sorted(frequency, key=lambda t: (-frequency[t], t))[:VOCAB_LIMIT])
    counts = {label: Counter() for label in LABELS}
    priors = Counter(y for _, y in documents)
    for tokens, label in documents:
        counts[label].update(tokens & vocabulary)
    denominators = {y: math.log(sum(counts[y].values()) + len(vocabulary)) for y in LABELS}
    # ponytail: bounded sparse counts; revisit only if the fixed CPU/memory cap fails.
    return vocabulary, counts, priors, denominators


def predict_nb(model, row, context):
    vocabulary, counts, priors, denominators = model
    tokens = features(row, context) & vocabulary
    scores = {y: math.log(priors[y] + 1) + sum(math.log(counts[y][t] + 1)
              - denominators[y] for t in sorted(tokens)) for y in LABELS}
    return min(LABELS, key=lambda y: (-scores[y], y))


def shuffle_context(rows):
    rng = random.Random(51)
    groups = defaultdict(list)
    result = [dict(row) for row in rows]
    for i, row in enumerate(rows):
        groups[row["history"][-1]].append(i)
    for indices in groups.values():
        donors = list(indices)
        rng.shuffle(donors)
        for recipient, donor in zip(indices, donors):
            for field in ("task", "observation"):
                result[recipient][field] = rows[donor][field]
    changed = sum((a["task"], a["observation"]) != (b["task"], b["observation"])
                  for a, b in zip(rows, result))
    return result, changed


def metrics(rows, predictions):
    if not rows or len(rows) != len(predictions):
        raise ValueError("empty or mismatched evaluation")
    hits = [p == r["target"] for p, r in zip(predictions, rows)]
    per_issue = defaultdict(list)
    changes = []
    labels = {}
    for r, hit in zip(rows, hits):
        per_issue[r["issue"]].append(hit)
        if r["target"] != r["history"][-1]:
            changes.append(hit)
    for label in LABELS:
        support = sum(r["target"] == label for r in rows)
        predicted = predictions.count(label)
        tp = sum(r["target"] == label and p == label for r, p in zip(rows, predictions))
        labels[label] = dict(support=support, predicted=predicted, correct=tp,
                            recall_pct=100 * tp / support if support else None,
                            f1=2 * tp / (support + predicted) if support + predicted else 0.0)
    return dict(rows=len(rows), correct=sum(hits), accuracy_pct=100 * sum(hits) / len(rows),
                macro_f1=sum(v["f1"] for v in labels.values()) / len(LABELS), labels=labels,
                change_rows=len(changes), change_accuracy_pct=100 * sum(changes) / len(changes)
                if changes else None, issues=len(per_issue),
                issue_macro_accuracy_pct=100 * sum(sum(v) / len(v) for v in per_issue.values())
                / len(per_issue))


def evaluate(splits):
    validate(splits)
    train, evaluation = splits["train"], splits["holdout"]
    baseline = baselines.fit([(r["issue"], tuple(r["history"]), r["target"]) for r in train])
    output = defaultdict(list)
    for r in evaluation:
        for name, label in baselines.predict(baseline, r["history"]).items():
            output[name].append(label)
    nb = fit_nb(train, False)
    contextual = fit_nb(train, True)
    shuffled, changed = shuffle_context(evaluation)
    output["action_nb"] = [predict_nb(nb, r, False) for r in evaluation]
    output["context_nb"] = [predict_nb(contextual, r, True) for r in evaluation]
    output["shuffled_context_nb"] = [predict_nb(contextual, r, True) for r in shuffled]
    scores = {name: metrics(evaluation, preds) for name, preds in output.items()}
    candidate = scores["context_nb"]
    strongest = max(scores[name]["accuracy_pct"] for name in
                    ("majority", "repeat_last", "markov_1", "phase_backoff", "action_nb"))
    margin = candidate["accuracy_pct"] - strongest
    shuffle_margin = candidate["accuracy_pct"] - scores["shuffled_context_nb"]["accuracy_pct"]
    coverage = 100 * changed / len(evaluation)
    passed = (margin >= 5 and shuffle_margin >= 2 and coverage >= 50
              and candidate["macro_f1"] >= scores["action_nb"]["macro_f1"])
    return dict(metrics=scores, context_shuffle_changed_rows=changed,
                context_shuffle_changed_pct=coverage, vocabulary_sizes=dict(action=len(nb[0]),
                context=len(contextual[0])), decision=dict(passed=passed,
                next="discuss_followup" if passed else "stop_this_probe",
                overall_margin_pp=margin, shuffle_margin_pp=shuffle_margin,
                shuffle_control_conclusive=coverage >= 50))


def timeout(signum, frame):
    raise TimeoutError("frozen wall-clock budget exceeded")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    # Fail before creating output; no overwrites and no arbitrary replay of substituted data.
    args.out.mkdir(parents=True, exist_ok=False)
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    started = time.monotonic()
    result = dict(status="incomplete", dataset=prep.DATASET, revision=prep.REVISION,
                  protocol=dict(offset=OFFSET, pages=PAGES, page_size=PAGE_SIZE,
                                row_caps=CAPS, per_issue_cap=50, vocab_limit=VOCAB_LIMIT,
                                shuffle_seed=51, smoothing_alpha=1),
                  evidence="public successful-trajectory label agreement; not human usefulness")
    try:
        ceiling = 2 * 1024 ** 3
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (min(ceiling, hard) if hard >= 0 else ceiling, hard))
        result["memory_limit_bytes"] = resource.getrlimit(resource.RLIMIT_AS)[0]
        path = acquire(args.out)
        result["source_sha256"] = prep.digest(path)
        splits, audit = prepare(prep._iter_jsonl(path))
        result.update(audit=audit, rows={s: len(v) for s, v in splits.items()},
                      issues={s: len({r["issue"] for r in v}) for s, v in splits.items()},
                      label_counts={s: {y: sum(r["target"] == y for r in v) for y in LABELS}
                                    for s, v in splits.items()})
        validate(splits)
        for split, rows in splits.items():
            with (args.out / (split + ".jsonl")).open("x") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        # All feature choices are frozen before this single evaluation call.
        signal.alarm(120)
        result.update(evaluate(splits), status="completed")
    except (ValueError, OSError, TimeoutError, MemoryError) as exc:
        result.update(status="refused", error=str(exc))
    finally:
        signal.alarm(0)
        result["elapsed_seconds"] = time.monotonic() - started
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["peak_rss_bytes"] = peak if sys.platform == "darwin" else peak * 1024
        result["code_sha256"] = {p.name: prep.digest(p) for p in
                                 (Path(__file__), Path(prep.__file__), Path(baselines.__file__),
                                  Path(prep.taxonomy.__file__))}
        with (args.out / "result.json").open("x") as fh:
            fh.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "rows", "decision", "error") if k in result}))
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
