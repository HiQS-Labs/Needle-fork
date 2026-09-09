"""Build frozen, NESTED evaluation manifests.

Why not reservoir sampling: reservoir with a shared seed but a different `n` yields a
DIFFERENT set, not a nested one. That is exactly the defect that made the MLX (n=60) and
native (n=200) arms disjoint -- zero overlapping rows -- and produced a phantom
"21.67% vs 3.00%" headline (#12, GPT-6 Astra).

Selection is `sha1(line)` ascending: stable under n, independent of file order, and
NESTED by construction, so frozen-200 is a strict prefix of frozen-2000 and the
diagnostic arm is a paired subset of the shippability arm.

Duplicates are kept explicit rather than silently dropped: every occurrence is recorded
with its source line number, and the unique count is reported separately so a repeated
example is never treated as an extra independent observation.
"""
import hashlib
import json
import os
from collections import Counter

SRC = "data/corpus-studio/oracle-holdout.jsonl"
OUT = "data/spike-mlx/manifests"


def main():
    labels = set(json.load(open("oracle/labels-v1.json"))["labels"])
    rows, dupes, skipped = [], 0, 0
    seen = set()
    with open(SRC) as fh:
        for lineno, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            h = hashlib.sha1(line.encode()).hexdigest()
            r = json.loads(line)
            gold = r["answers"][0]["name"] if r.get("answers") else None
            if gold not in labels:
                skipped += 1
                continue
            if h in seen:
                dupes += 1
                continue
            seen.add(h)
            rows.append((h, lineno, line))

    rows.sort(key=lambda t: t[0])
    os.makedirs(OUT, exist_ok=True)
    print(f"  source          {SRC}")
    print(f"  eligible unique {len(rows)}   (skipped {skipped} rows whose gold is not a v1 label;"
          f" {dupes} duplicate line(s) collapsed)")

    prev = None
    for n in (200, 2000):
        sel = rows[:n]
        stem = f"{OUT}/frozen-{n}"
        with open(f"{stem}.jsonl", "w") as out:
            for _, _, line in sel:
                out.write(line + "\n")
        gold = [json.loads(l)["answers"][0]["name"] for _, _, l in sel]
        c = Counter(gold)
        top1 = c.most_common(1)[0]
        top5 = c.most_common(5)
        meta = {
            "source": SRC,
            "selection": "sha1(line) ascending; dedup; gold must be a v1 label",
            "n": len(sel),
            "eligible_unique_rows": len(rows),
            "duplicate_lines_collapsed": dupes,
            "rows_skipped_gold_not_in_labels": skipped,
            "manifest_sha1": hashlib.sha1("".join(h for h, _, _ in sel).encode()).hexdigest(),
            "majority_label": top1[0],
            "majority_baseline_pct": round(100 * top1[1] / len(sel), 2),
            "distinct_gold_labels": len(c),
            "top5_labels": [k for k, _ in top5],
            "top5_coverage_pct": round(100 * sum(v for _, v in top5) / len(sel), 2),
            "rows": [{"sha1": h, "source_line": ln} for h, ln, _ in sel],
        }
        json.dump(meta, open(f"{stem}.meta.json", "w"), indent=2)
        nested = "" if prev is None else \
            ("  NESTED: superset of frozen-%d" % prev if
             {h for h, _, _ in rows[:prev]} <= {h for h, _, _ in sel} else "  !! NOT NESTED")
        print(f"  frozen-{n:<5} sha1 {meta['manifest_sha1'][:16]}  "
              f"baseline {meta['majority_baseline_pct']:.2f}% ({top1[0]})  "
              f"{meta['distinct_gold_labels']} labels  "
              f"top5 cov {meta['top5_coverage_pct']:.1f}%{nested}")
        prev = n


if __name__ == "__main__":
    main()
