#!/usr/bin/env python3
"""Build the Phase 2 Oracle training corpus from local Claude Code transcripts.

Reads ~/.claude/projects/**/*.jsonl and emits (context -> next action) pairs for
tool-selection training. See HiQS-Labs/Needle-fork#1.

WHY THIS EXISTS
    `rebalance.db`'s clio_prompts table records what the human typed, not what the
    agent did -- it has no tool-call column, so it cannot supply a supervision
    target. Claude Code transcripts do: tool_use records in sequence, with context.

PRIVACY -- READ BEFORE CHANGING
    The transcripts contain the operator's real sessions. This script deliberately
    does NOT copy tool *results* (file contents, command output, secrets) into the
    corpus. It keeps only:
      - the most recent user request, truncated
      - the sequence of preceding action labels
    That is what a tool-selection model needs, and it drops the highest-risk and
    highest-volume material. The output still contains real prompt text, so it
    lands in data/ (gitignored) and must never be committed. Needle-fork is PUBLIC.

TAXONOMY LIVES IN taxonomy.py, NOT HERE
    The first version of this file carried its own ordered regex list and matched it
    against the WHOLE command string, first match wins. Measured on 1,220 local Bash
    calls: 97.9% of commands are compound and 74.0% matched two or more rules, so for
    most calls the label was chosen by a rule's POSITION IN THE LIST rather than by the
    command -- `git_mutate` was collecting `grep -n ...` and `sed -n 1,120p ROUTER.md`.
    It also read only `command` and never `file_path`, which made every governance
    label undetectable: `Edit` was 11.33% of the corpus with `update_changelog`,
    `file_capture_doc` and ordinary code edits collapsed into one token.

    Both are fixed in `taxonomy.py`, which is now the single source of truth shared by
    this extractor, the trainer, the evaluator and the end-of-turn hook. Do not
    re-introduce rules here. See PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md.
"""
from __future__ import annotations
import argparse, collections, glob, hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy as tx  # noqa: E402


def iter_steps(path: str):
    """Yield ('user', text) and ('action', tool, input) in transcript order.

    The full tool input is carried through because governance labels live in
    `file_path`, not in `command`. Only the label is kept downstream -- the input
    itself never reaches the corpus.
    """
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            msg = rec.get("message") or {}
            content = msg.get("content")
            if isinstance(content, str):
                if msg.get("role") == "user" and content.strip():
                    yield ("user", content)
                continue
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text" and msg.get("role") == "user":
                    if block.get("text", "").strip():
                        yield ("user", block["text"])
                elif btype == "tool_use":
                    name = block.get("name")
                    if name:
                        yield ("action", name, block.get("input") or {})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--out-dir", default="data/corpus")
    ap.add_argument("--context-steps", type=int, default=12,
                    help="preceding actions kept per pair (default 12)")
    ap.add_argument("--user-chars", type=int, default=600,
                    help="truncation for the most recent user request (default 600)")
    ap.add_argument("--min-session-actions", type=int, default=5)
    ap.add_argument("--holdout-pct", type=int, default=15,
                    help="percent of SESSIONS held out; split is by session, never "
                         "by pair, because consecutive pairs share context")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.source, "**", "*.jsonl"), recursive=True))
    if not files:
        print(f"No transcripts under {args.source}", file=sys.stderr)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    pairs_path = os.path.join(args.out_dir, "pairs.jsonl")

    counts = collections.Counter()
    n_pairs = n_sessions = n_skipped = 0
    split_counts = collections.Counter()

    with open(pairs_path, "w") as out:
        for fp in files:
            # Session id is a hash: project paths leak repo and client names.
            sid = hashlib.sha256(fp.encode()).hexdigest()[:16]
            steps = list(iter_steps(fp))
            actions = [s for s in steps if s[0] == "action"]
            if len(actions) < args.min_session_actions:
                n_skipped += 1
                continue
            n_sessions += 1
            # Deterministic, session-level split.
            split = "holdout" if int(sid[:8], 16) % 100 < args.holdout_pct else "train"
            split_counts[split] += 1

            history: list[str] = []
            recent_user = ""
            for step in steps:
                if step[0] == "user":
                    recent_user = step[1][: args.user_chars]
                    continue
                _, tool, tool_input = step
                label, _evidence = tx.label_call(tool, tool_input)
                if history:  # a pair needs at least one step of context
                    out.write(json.dumps({
                        "session": sid,
                        "step": len(history),
                        "split": split,
                        "recent_user_request": recent_user,
                        "prior_actions": history[-args.context_steps:],
                        "label": label,
                        "tool_name": tool,
                    }) + "\n")
                    n_pairs += 1
                    counts[label] += 1
                history.append(label)

    def baseline(counter: collections.Counter, k: int) -> float:
        tot = sum(counter.values()) or 1
        return 100.0 * sum(v for _, v in counter.most_common(k)) / tot

    # #1 §3: assert non-empty. `load_jsonl` silently skips rows without a `query`
    # key, so a converter bug yields an empty training set and a run that reports
    # success against zero rows. Fail here instead.
    if n_pairs == 0:
        print("extracted 0 pairs -- refusing to write an empty corpus", file=sys.stderr)
        return 1

    coverage = tx.coverage(counts.elements())
    gov_groups = {"pdda", "prs", "xyz"}
    gov = sum(v for k, v in counts.items() if tx.LABELS_V1[k]["group"] in gov_groups)

    stats = {
        "generated_from": args.source,
        "transcripts_seen": len(files),
        "sessions_used": n_sessions,
        "sessions_skipped_too_short": n_skipped,
        "pairs": n_pairs,
        "split_sessions": dict(split_counts),
        "context_steps": args.context_steps,
        "user_chars": args.user_chars,
        "label_set_version": tx.LABEL_SET_VERSION,
        "labels": len(counts),
        "labels_defined": len(tx.LABELS_V1),
        "mapping_coverage": round(coverage, 4),
        "governance_share": round(gov / n_pairs, 4),
        "baseline_top1_pct": round(baseline(counts, 1), 2),
        "baseline_top3_pct": round(baseline(counts, 3), 2),
        "distribution": dict(counts.most_common()),
    }
    with open(os.path.join(args.out_dir, "stats.json"), "w") as fh:
        json.dump(stats, fh, indent=2)

    print(f"sessions {n_sessions} (skipped {n_skipped})   pairs {n_pairs:,}")
    print(f"split sessions: {dict(split_counts)}")
    print(f"label set {tx.LABEL_SET_VERSION}   labels in use {len(counts)}/{len(tx.LABELS_V1)}")
    print(f"MAPPING COVERAGE {100 * coverage:.2f}%   governance share {100 * gov / n_pairs:.2f}%")
    print(f"baselines to beat: top1 {stats['baseline_top1_pct']}%  "
          f"top3 {stats['baseline_top3_pct']}%")
    print(f"wrote {pairs_path} and stats.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
