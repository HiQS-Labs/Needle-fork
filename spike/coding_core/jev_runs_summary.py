#!/usr/bin/env python3
"""Summarise repeated Jev runs on the same rows: noise floor and per-row stability (GH-77).

    python spike/coding_core/jev_runs_summary.py --label A-stability \
        --runs run-1/results.json run-2/results.json ... [--reference orig/results.json] --out summary.json

All runs must share `holdout_sha256` and row count. Reports per-run top-1 / macro-F1, the range,
per-row stability (rows whose answer differs across runs, distinct answers per row), the >= 0.8
confidence subset per run, and a majority-vote top-1 across the runs. Prints a markdown table.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path


def load(path: Path) -> dict:
    r = json.loads(path.read_text())
    r["_path"] = str(path)
    return r


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True)
    ap.add_argument("--runs", type=Path, nargs="+", required=True)
    ap.add_argument("--reference", type=Path, help="a run to report per-row agreement against (e.g. the #66 original)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    runs = [load(p) for p in a.runs]
    ref = load(a.reference) if a.reference else None
    everything = runs + ([ref] if ref else [])
    hashes = {r["holdout_sha256"] for r in everything}
    sizes = {r["rows"] for r in everything}
    if len(hashes) != 1 or len(sizes) != 1:
        raise SystemExit(f"runs are not on the same rows: hashes {hashes} sizes {sizes}")
    n = sizes.pop()
    gold = [p["gold"] for p in runs[0]["predictions"]]
    for r in everything:
        if [p["gold"] for p in r["predictions"]] != gold:
            raise SystemExit(f"{r['_path']}: gold labels differ")
    choices = [[p["choice"] for p in r["predictions"]] for r in runs]
    confs = [[float(p["confidence"]) for p in r["predictions"]] for r in runs]
    top1 = [sum(1 for c, g in zip(ch, gold) if c == g) for ch in choices]
    f1 = [r["metrics"]["macro_f1"] for r in runs]
    high = [[i for i, c in enumerate(cf) if c >= 0.8] for cf in confs]
    high_correct = [sum(1 for i in h if choices[k][i] == gold[i]) for k, h in enumerate(high)]
    distinct = [len({ch[i] for ch in choices}) for i in range(n)]
    vote = []
    for i in range(n):
        counter = collections.Counter(ch[i] for ch in choices)
        vote.append(counter.most_common(1)[0][0])
    summary = {
        "label": a.label, "runs": len(runs), "rows": n,
        "holdout_sha256": runs[0]["holdout_sha256"],
        "wording": sorted({r.get("wording", "prescriptive") for r in runs}),
        "state": sorted({r.get("state", "q1") for r in runs}),
        "questions_sha256": sorted({r["questions_sha256"] for r in runs}),
        "per_run": [{"path": r["_path"], "top1": t, "macro_f1": round(m, 4), "high_conf_rows": len(h),
                     "high_conf_correct": hc, "input_tokens": r["input_tokens"], "utc_started": r["utc_started"]}
                    for r, t, m, h, hc in zip(runs, top1, f1, high, high_correct)],
        "top1": {"min": min(top1), "max": max(top1), "mean": round(statistics.mean(top1), 2),
                 "range": max(top1) - min(top1)},
        "macro_f1": {"min": round(min(f1), 4), "max": round(max(f1), 4), "mean": round(statistics.mean(f1), 4)},
        "stability": {"rows_with_any_change": sum(1 for d in distinct if d > 1),
                      "rows_stable": sum(1 for d in distinct if d == 1),
                      "distinct_answers_per_row": dict(sorted(collections.Counter(distinct).items())),
                      "rows_always_correct": sum(1 for i in range(n) if all(ch[i] == gold[i] for ch in choices)),
                      "rows_ever_correct": sum(1 for i in range(n) if any(ch[i] == gold[i] for ch in choices))},
        "majority_vote_top1": sum(1 for v, g in zip(vote, gold) if v == g),
        "prediction_counts_mean": {lab: round(statistics.mean(sum(1 for c in ch if c == lab) for ch in choices), 1)
                                   for lab in sorted({c for ch in choices for c in ch})},
    }
    if ref:
        rch = [p["choice"] for p in ref["predictions"]]
        rt = sum(1 for c, g in zip(rch, gold) if c == g)
        summary["reference"] = {
            "path": ref["_path"], "top1": rt,
            "same_choice_as_reference_per_run": [sum(1 for c, r0 in zip(ch, rch) if c == r0) for ch in choices],
            "top1_range_including_reference": [min(top1 + [rt]), max(top1 + [rt])],
        }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(f"### {a.label} — {len(runs)} runs × {n} rows")
    print("| run | top-1 | macro-F1 | ≥0.8 rows | ≥0.8 correct |\n|---|---:|---:|---:|---:|")
    for k, r in enumerate(summary["per_run"], 1):
        print(f"| {k} | {r['top1']} | {r['macro_f1']:.3f} | {r['high_conf_rows']} | {r['high_conf_correct']} |")
    s = summary["stability"]
    print(f"\ntop-1 {summary['top1']['min']}–{summary['top1']['max']} (mean {summary['top1']['mean']}, range {summary['top1']['range']}); "
          f"rows with any change {s['rows_with_any_change']}/{n}; distinct answers per row {s['distinct_answers_per_row']}; "
          f"always correct {s['rows_always_correct']}, ever correct {s['rows_ever_correct']}; majority vote {summary['majority_vote_top1']}")
    if ref:
        print(f"reference top-1 {summary['reference']['top1']}; same choice as reference per run {summary['reference']['same_choice_as_reference_per_run']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
