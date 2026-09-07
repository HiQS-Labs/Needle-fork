#!/usr/bin/env python3
"""Convert `data/corpus/pairs.jsonl` into the JSONL `needle finetune` consumes (#1 §3).

    python3 utils/corpus/build_oracle_jsonl.py                    # -> data/corpus/oracle-train.jsonl, oracle-holdout.jsonl
    python3 utils/corpus/build_oracle_jsonl.py --check-max-len    # also refuse rows that would truncate

Every row goes through `serialize.to_finetune_row`, the same function the end-of-turn
hook uses, so training-time and hook-time queries cannot drift (#1 §6).

Two hazards #1 names are guarded here, not left to the trainer:

  * `finetune.load_jsonl` silently skips rows without `query`, so a converter bug yields
    an empty training set and a run that reports success against zero rows. This script
    refuses to write an empty split.
  * `finetune._encode` truncates `ids[:max_len]` from the END -- the target side -- so an
    over-long row trains toward nothing. `--check-max-len` renders every row exactly as
    the trainer will and fails if any exceeds the cap. It needs the real tokenizer (a
    one-time HF download); without it the check is skipped LOUDLY, not silently.

Output stays in data/ (gitignored). Needle-fork is PUBLIC; the rows contain real prompt text.
"""
from __future__ import annotations
import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serialize as ser  # noqa: E402
import taxonomy as tx  # noqa: E402


def _render_len(row: dict, tokenizer, render_example) -> int:
    prompt, target = render_example(row)
    return len(tokenizer.encode(prompt)) + len(tokenizer.encode(target)) + 2  # BOS/EOS


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs", default="data/corpus/pairs.jsonl")
    ap.add_argument("--out-dir", default="data/corpus")
    ap.add_argument("--schemas", default=ser.SCHEMAS_PATH)
    ap.add_argument("--context-steps", type=int, default=ser.DEFAULT_CONTEXT_STEPS)
    ap.add_argument("--user-chars", type=int, default=ser.DEFAULT_USER_CHARS)
    ap.add_argument("--check-max-len", nargs="?", const=ser.TRAIN_MAX_LEN, type=int,
                    default=None, help=f"render every row with the real tokenizer and "
                    f"refuse if any exceeds N tokens (default N={ser.TRAIN_MAX_LEN})")
    args = ap.parse_args()

    if not os.path.exists(args.pairs):
        print(f"missing {args.pairs} -- run extract_claude_transcripts.py first", file=sys.stderr)
        return 1
    schemas = ser.load_schemas(args.schemas)
    os.makedirs(args.out_dir, exist_ok=True)

    # Write to .tmp and rename only on success: a crash mid-run must not leave 0-byte
    # split files behind, because `load_jsonl` would train on them as zero rows.
    final = {s: os.path.join(args.out_dir, f"oracle-{s}.jsonl") for s in ("train", "holdout")}
    outs = {s: open(p + ".tmp", "w") for s, p in final.items()}
    n = collections.Counter()
    labels = collections.Counter()
    longest = 0
    tokenizer = render_example = None
    if args.check_max_len:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
            from needle.model.finetune import render_example as _re  # noqa: E402
            from needle.model.tokenizer import get_tokenizer  # noqa: E402
            tokenizer, render_example = get_tokenizer(), _re
        except Exception as exc:  # loud, not silent
            print(f"!! --check-max-len requested but tokenizer/trainer unavailable: {exc}",
                  file=sys.stderr)
            print("!! rows written WITHOUT the truncation check", file=sys.stderr)

    with open(args.pairs) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            pair = json.loads(line)
            if "label" not in pair:
                print("!! pairs.jsonl predates taxonomy v1 (no `label` field; has "
                      f"{sorted(k for k in pair if k.startswith('label'))}) -- re-run "
                      "utils/corpus/extract_claude_transcripts.py first", file=sys.stderr)
                return 2
            row = ser.to_finetune_row(pair, schemas, args.context_steps, args.user_chars)
            if tokenizer is not None:
                L = _render_len(row, tokenizer, render_example)
                longest = max(longest, L)
                if L > args.check_max_len:
                    print(f"!! row would truncate: {L} tokens > {args.check_max_len} "
                          f"(session {pair['session']} step {pair['step']})", file=sys.stderr)
                    return 2
            split = pair.get("split", "train")
            outs[split].write(json.dumps(row, ensure_ascii=False) + "\n")
            n[split] += 1
            labels[pair["label"]] += 1
    for fh in outs.values():
        fh.close()

    for s in final:
        if n[s] == 0:
            print(f"!! split {s!r} has 0 rows -- refusing (#1 §3 empty-input hazard)", file=sys.stderr)
            return 2
    for s, p in final.items():
        os.replace(p + ".tmp", p)

    stats = {
        "query_format": ser.QUERY_FORMAT_VERSION,
        "label_set_version": tx.LABEL_SET_VERSION,
        "rows": dict(n),
        "labels_present": len(labels),
        "abstain_rows": labels.get("no_action", 0),
        "context_steps": args.context_steps,
        "user_chars": args.user_chars,
        "max_len_checked": args.check_max_len if tokenizer is not None else None,
        "longest_rendered_tokens": longest if tokenizer is not None else None,
        "schemas": len(schemas),
    }
    with open(os.path.join(args.out_dir, "oracle-stats.json"), "w") as fh:
        json.dump(stats, fh, indent=2)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
