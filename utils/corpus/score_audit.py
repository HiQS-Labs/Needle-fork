#!/usr/bin/env python3
"""Score the sorter against hand-audited labels.

Reports PRECISION per stratum with Wilson intervals, and the confusion pairs that
say WHICH rules steal from which -- the direct evidence about rule ordering.

Reads data/audit/{sorter,<auditor>}.jsonl. Writes aggregates only; the sample text
itself never leaves data/.
"""
from __future__ import annotations
import argparse, collections, json, math, os, sys


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def load(path: str) -> dict:
    return {json.loads(l)["id"]: json.loads(l) for l in open(path)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/audit")
    ap.add_argument("--auditors", default="claude,agy")
    ap.add_argument("--out", help="write an aggregate receipt here")
    args = ap.parse_args()

    sorter = load(os.path.join(args.dir, "sorter.jsonl"))
    auditors = {}
    for a in args.auditors.split(","):
        p = os.path.join(args.dir, f"{a}.jsonl")
        if os.path.exists(p):
            auditors[a] = load(p)
        else:
            print(f"note: {a} has not submitted ({p} missing)", file=sys.stderr)
    if not auditors:
        print("no auditor files", file=sys.stderr)
        return 1

    report = {"auditors": {}, "disagreement": None, "confusion": {}}
    for name, ans in auditors.items():
        per = collections.defaultdict(lambda: [0, 0])     # label -> [right, total]
        conf = collections.Counter()
        low = 0
        for rid, s in sorter.items():
            if rid not in ans:
                continue
            gold, got = ans[rid]["label"], s["sorter_label"]
            per[got][1] += 1
            if gold == got:
                per[got][0] += 1
            else:
                conf[(got, gold)] += 1
            low += ans[rid].get("confidence") == "low"
        n = sum(v[1] for v in per.values())
        k = sum(v[0] for v in per.values())
        lo, hi = wilson(k, n)
        report["auditors"][name] = {
            "n": n, "agree": k, "precision": round(k / n, 4),
            "ci95": [round(lo, 4), round(hi, 4)],
            "low_confidence_rows": low,
            "per_label": {lb: {"n": v[1], "agree": v[0], "precision": round(v[0] / v[1], 4),
                               "ci95": [round(x, 4) for x in wilson(v[0], v[1])]}
                          for lb, v in sorted(per.items())},
        }
        report["confusion"][name] = [
            {"sorter": a, "auditor": b, "n": c} for (a, b), c in conf.most_common(25)]
        print(f"\n=== auditor: {name} ===")
        print(f"  agreement with sorter  {k}/{n} = {100*k/n:.1f}%  (95% CI {100*lo:.1f}-{100*hi:.1f}%)")
        print(f"  rows the auditor marked low confidence: {low}")
        print("  weakest strata (n>=5):")
        weak = sorted(((lb, v) for lb, v in per.items() if v[1] >= 5), key=lambda x: x[1][0] / x[1][1])
        for lb, v in weak[:10]:
            print(f"    {lb:24s} {v[0]:3d}/{v[1]:3d} = {100*v[0]/v[1]:5.1f}%")
        print("  top confusions (sorter said -> auditor said):")
        for (a, b), c in conf.most_common(10):
            print(f"    {a:24s} -> {b:24s} {c}")

    if len(auditors) == 2:
        a, b = list(auditors)
        both = [r for r in sorter if r in auditors[a] and r in auditors[b]]
        same = sum(auditors[a][r]["label"] == auditors[b][r]["label"] for r in both)
        lo, hi = wilson(same, len(both))
        report["disagreement"] = {"n": len(both), "agree": same,
                                  "inter_rater": round(same / len(both), 4),
                                  "ci95": [round(lo, 4), round(hi, 4)]}
        print(f"\n=== inter-rater ({a} vs {b}) ===")
        print(f"  {same}/{len(both)} = {100*same/len(both):.1f}%  (95% CI {100*lo:.1f}-{100*hi:.1f}%)")
        print("  NOTE: auditor disagreement bounds how precisely the sorter can be scored at all.")

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
