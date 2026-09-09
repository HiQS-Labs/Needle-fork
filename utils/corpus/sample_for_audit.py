#!/usr/bin/env python3
"""Draw a stratified sample of labelled calls for a blind correctness audit.

WHY THIS EXISTS
    Every number measured about the sorter counts RESOLUTION -- did a call get *a*
    label. Nothing has measured whether the label is RIGHT (issue #1 §2 defines
    dataset validity as coverage, which cannot tell a right label from a wrong one).
    See PROJECT/1-INBOX/LABEL-CORRECTNESS-AUDIT.md and LESSONS-LEARNED.md §15.

PRIVACY -- READ BEFORE CHANGING
    The sample contains REAL COMMAND TEXT from the operator's private transcripts,
    and this repository is PUBLIC. Everything this script writes goes under `data/`,
    which is gitignored, and must NEVER be committed -- not in a relay file, not in
    a receipt, not in an issue comment. Only aggregates leave `data/`.

BLIND PROTOCOL
    `sample.jsonl` carries the call text WITHOUT the sorter's label, so an auditor
    assigns a label without anchoring on the answer. The sorter's labels are held
    back in `sorter.jsonl` and joined only at scoring time.
"""
from __future__ import annotations
import argparse, collections, json, math, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy as tx
from measure_taxonomy import iter_calls


def render(tool: str, inp: dict) -> str:
    """What the sorter actually reads, as one auditable line."""
    if tool == "Bash":
        return (inp.get("command") or "").strip()
    fp = inp.get("file_path") or inp.get("path") or ""
    pat = inp.get("pattern") or inp.get("query") or ""
    return " ".join(x for x in (fp, pat) if x).strip()


def allocate(counts: dict, target: int, floor: int) -> dict:
    """Floor per stratum, remainder proportional to sqrt(count).

    Uniform allocation would give the governance labels 2-3 rows -- they are the
    labels the Oracle exists for and the thinnest in the corpus. sqrt keeps the
    large strata represented without letting `read_file` eat the sample.
    """
    take = {k: min(v, floor) for k, v in counts.items()}
    rest = target - sum(take.values())
    if rest > 0:
        room = {k: counts[k] - take[k] for k in counts if counts[k] > take[k]}
        if room:
            w = {k: math.sqrt(counts[k]) for k in room}
            tot = sum(w.values())
            for k in sorted(room, key=lambda k: -w[k]):
                add = min(room[k], int(round(rest * w[k] / tot)))
                take[k] += add
    return {k: v for k, v in take.items() if v}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--out-dir", default="data/audit")
    ap.add_argument("--target", type=int, default=400)
    ap.add_argument("--floor", type=int, default=8,
                    help="minimum rows per label present in the corpus")
    ap.add_argument("--seed", type=int, default=20260909)
    args = ap.parse_args()

    if not args.out_dir.startswith("data/"):
        print("refusing: the sample contains real prompt text and must stay under data/",
              file=sys.stderr)
        return 2

    pool = collections.defaultdict(list)
    for path, tool, inp in iter_calls(args.source):
        label, _ = tx.label_call(tool, inp)
        text = render(tool, inp)
        if text:
            pool[label].append({"session": path, "tool": tool, "text": text})

    counts = {k: len(v) for k, v in pool.items()}
    plan = allocate(counts, args.target, args.floor)

    rng = random.Random(args.seed)
    os.makedirs(args.out_dir, exist_ok=True)
    sample, truth, n = [], [], 0
    for label in sorted(plan):
        for row in rng.sample(pool[label], plan[label]):
            rid = f"a{n:04d}"
            sample.append({"id": rid, "tool": row["tool"], "text": row["text"]})
            truth.append({"id": rid, "sorter_label": label, "session": row["session"]})
            n += 1

    rng.shuffle(sample)          # so stratum order cannot hint at the label
    for name, rows in (("sample.jsonl", sample), ("sorter.jsonl", truth)):
        with open(os.path.join(args.out_dir, name), "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

    with open(os.path.join(args.out_dir, "plan.json"), "w") as fh:
        json.dump({"seed": args.seed, "target": args.target, "floor": args.floor,
                   "label_set_version": tx.LABEL_SET_VERSION,
                   "population": counts, "allocation": plan, "drawn": n}, fh, indent=2)

    print(f"population   {sum(counts.values()):,} calls across {len(counts)} labels")
    print(f"drawn        {n} rows across {len(plan)} strata (seed {args.seed})")
    print(f"wrote        {args.out_dir}/sample.jsonl (blind), sorter.jsonl (held back), plan.json")
    print("REMINDER: data/ is gitignored. Never commit or paste these rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
