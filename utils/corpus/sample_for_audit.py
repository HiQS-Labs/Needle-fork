#!/usr/bin/env python3
"""Draw a stratified sample of labelled calls for a blind correctness audit.

WHY THIS EXISTS
    Every number measured about the sorter counts RESOLUTION -- did a call get *a*
    label. Nothing has measured whether the label is RIGHT (issue #1 §2 defines
    dataset validity as coverage, which cannot tell a right label from a wrong one).
    See PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md and LESSONS-LEARNED.md §15.

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
import argparse, collections, hashlib, json, math, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy as tx
from measure_taxonomy import iter_call_records, iter_calls
from transcript_events import IDENTITY_FORMAT_VERSION, validate_namespace


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
    if not counts or any(v <= 0 for v in counts.values()):
        raise ValueError("population strata must be non-empty positive counts")
    if target <= 0 or floor <= 0:
        raise ValueError("target and floor must be positive")
    if target > sum(counts.values()):
        raise ValueError("target exceeds the renderable population")

    take = {k: min(v, floor) for k, v in counts.items()}
    minimum = sum(take.values())
    if target < minimum:
        raise ValueError(f"target {target} is below the {minimum}-row stratum floor")
    rest = target - sum(take.values())
    while rest:
        room = {k: counts[k] - take[k] for k in counts if counts[k] > take[k]}
        if not room:
            raise ValueError("allocation exhausted the population before reaching target")
        weights = {k: math.sqrt(counts[k]) for k in room}
        total_weight = sum(weights.values())
        quotas = {k: rest * weights[k] / total_weight for k in room}
        grants = {k: min(room[k], int(quotas[k])) for k in room}
        granted = sum(grants.values())
        if not granted:
            # Largest-remainder tie break is deterministic by label.
            k = max(room, key=lambda x: (quotas[x], weights[x], x))
            grants[k] = 1
            granted = 1
        for k, amount in grants.items():
            take[k] += amount
        rest -= granted
    return {k: v for k, v in take.items() if v}


def draw(pool: dict, plan: dict, seed: int) -> tuple[list[dict], list[dict]]:
    """Select rows deterministically, then assign IDs that reveal no stratum order."""
    rng = random.Random(seed)
    selected = []
    for label in sorted(plan):
        for row in rng.sample(pool[label], plan[label]):
            selected.append((label, row))
    rng.shuffle(selected)

    sample, truth, ids = [], [], set()
    for ordinal, (label, row) in enumerate(selected):
        stable_event = row.get("source_event_id")
        identity = (["event", stable_event] if stable_event else
                    ["legacy", row["session"], row["tool"], row["text"]])
        material = json.dumps([seed, ordinal, identity], ensure_ascii=False,
                              separators=(",", ":"))
        rid = "a" + hashlib.sha256(material.encode()).hexdigest()[:16]
        if rid in ids:
            raise ValueError("blind row ID collision")
        ids.add(rid)
        sample.append({"id": rid, "tool": row["tool"], "text": row["text"]})
        truth_row = {"id": rid, "sorter_label": label, "session": row["session"]}
        for key in ("identity_format", "source_namespace", "source_relpath",
                    "transcript_sha256", "source_event_id", "source_event_ordinal"):
            if key in row:
                truth_row[key] = row[key]
        truth.append(truth_row)
    return sample, truth


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--source-namespace",
                    help="opt into v3 audit rows with mount-invariant source identity")
    ap.add_argument("--out-dir", default="data/audit")
    ap.add_argument("--target", type=int, default=400)
    ap.add_argument("--floor", type=int, default=8,
                    help="minimum rows per label present in the corpus")
    ap.add_argument("--seed", type=int, default=20260909)
    args = ap.parse_args(argv)

    data_root = os.path.realpath("data")
    output_dir = os.path.realpath(args.out_dir)
    try:
        inside_data = os.path.commonpath([data_root, output_dir]) == data_root
    except ValueError:
        inside_data = False
    if not inside_data or output_dir == data_root:
        print("refusing: the sample contains real prompt text and must stay under data/",
              file=sys.stderr)
        return 2
    occupied = sorted(os.listdir(args.out_dir)) if os.path.isdir(args.out_dir) else []
    if occupied:
        print(f"refusing to overwrite an existing audit ({', '.join(occupied)}); "
              "choose a new --out-dir", file=sys.stderr)
        return 2

    pool = collections.defaultdict(list)
    try:
        if args.source_namespace:
            validate_namespace(args.source_namespace)
            records = iter_call_records(args.source, args.source_namespace)
            for record in records:
                label, _ = tx.label_call(record["tool"], record["input"])
                text = render(record["tool"], record["input"])
                if text:
                    pool[label].append({
                        "session": record["session"],
                        "tool": record["tool"],
                        "text": text,
                        "identity_format": IDENTITY_FORMAT_VERSION,
                        "source_namespace": record["source_namespace"],
                        "source_relpath": record["source_relpath"],
                        "transcript_sha256": record["transcript_sha256"],
                        "source_event_id": record["source_event_id"],
                        "source_event_ordinal": record["source_event_ordinal"],
                    })
        else:
            for path, tool, inp in iter_calls(args.source):
                label, _ = tx.label_call(tool, inp)
                text = render(tool, inp)
                if text:
                    pool[label].append({"session": path, "tool": tool, "text": text})
    except (OSError, ValueError) as exc:
        print(f"refusing: cannot identify source calls: {exc}", file=sys.stderr)
        return 2

    counts = {k: len(v) for k, v in pool.items()}
    try:
        plan = allocate(counts, args.target, args.floor)
    except ValueError as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return 2

    os.makedirs(args.out_dir, exist_ok=True)
    sample, truth = draw(pool, plan, args.seed)
    n = len(sample)
    for name, rows in (("sample.jsonl", sample), ("sorter.jsonl", truth)):
        with open(os.path.join(args.out_dir, name), "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

    with open(os.path.join(args.out_dir, "plan.json"), "w") as fh:
        plan_doc = {"audit_format_version": 3 if args.source_namespace else 2,
                   "seed": args.seed, "target": args.target, "floor": args.floor,
                   "label_set_version": tx.LABEL_SET_VERSION,
                   "population": counts, "allocation": plan, "drawn": n}
        if args.source_namespace:
            plan_doc.update({"identity_format": IDENTITY_FORMAT_VERSION,
                             "source_namespace": args.source_namespace})
        json.dump(plan_doc, fh, indent=2)

    print(f"population   {sum(counts.values()):,} calls across {len(counts)} labels")
    print(f"drawn        {n} rows across {len(plan)} strata (seed {args.seed})")
    print(f"wrote        {args.out_dir}/sample.jsonl (blind), sorter.jsonl (held back), plan.json")
    print("REMINDER: data/ is gitignored. Never commit or paste these rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
