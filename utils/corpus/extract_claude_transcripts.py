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

TAXONOMY IS DEFERRED, NOT DECIDED
    Every pair carries BOTH labelings so training can choose without re-extracting:
      label_raw    -- Bash intents kept distinct from same-intent native tools
      label_merged -- same intent collapsed across transport (cat == Read)
    They imply different baselines to beat (top-3: ~55% raw, ~62% merged).
"""
from __future__ import annotations
import argparse, collections, glob, hashlib, json, os, re, sys

# --- Bash command -> intent. First match wins; order matters. ------------------
BASH_RULES = [
    ("run_tests",   r"\b(pytest|jest|vitest|go test|cargo test|npm (run )?test|make test|\./validate\.sh|ci-local\.sh|run-tests)"),
    ("git_inspect", r"\bgit\s+(status|log|diff|show|branch|remote|rev-parse|rev-list|describe|blame|check-ignore|ls-files)"),
    ("git_mutate",  r"\bgit\s+(add|commit|push|pull|fetch|merge|rebase|checkout|switch|reset|stash|clone|worktree|tag|cherry-pick)"),
    ("search_code", r"\b(rg|grep|ag|ack)\b"),
    ("find_files",  r"\b(find|fd|ls|tree)\b"),
    ("read_file",   r"\b(cat|head|tail|less|bat|sed -n|awk)\b"),
    ("build",       r"\b(make|cmake|cargo build|go build|npm run build|xcodebuild|clang|gcc|tsc)\b"),
    ("pkg_manage",  r"\b(pip|pip3|npm install|yarn|brew|uv|poetry|apt|gem)\b"),
    ("gh_cli",      r"\bgh\s+"),
    ("run_script",  r"\b(python3?|node|bash|sh|zsh|ruby|perl)\s+\S+\.(py|js|ts|sh|rb|pl)"),
    ("db_query",    r"\b(sqlite3|psql|mysql|bq)\b"),
    ("fs_mutate",   r"\b(mkdir|rm|mv|cp|touch|chmod|ln)\b"),
    ("sys_inspect", r"\b(ps|top|uptime|sysctl|df|du|whoami|which|uname|sw_vers|scutil|env)\b"),
    ("net",         r"\b(curl|wget|ping|ssh|scp|rsync)\b"),
]
BASH_RE = [(n, re.compile(p)) for n, p in BASH_RULES]

# Native tools whose intent duplicates a Bash bucket, for label_merged only.
MERGE_INTO = {"Read": "read_file", "Grep": "search_code", "Glob": "find_files"}


def bash_intent(cmd: str) -> str:
    for name, rx in BASH_RE:
        if rx.search(cmd):
            return name
    return "bash_other"


def label_for(tool: str, cmd: str) -> tuple[str, str]:
    """Return (label_raw, label_merged)."""
    raw = bash_intent(cmd) if tool == "Bash" else tool
    return raw, MERGE_INTO.get(raw, raw)


def iter_steps(path: str):
    """Yield ('user', text) and ('action', tool, cmd) in transcript order."""
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
                        cmd = (block.get("input") or {}).get("command") or ""
                        yield ("action", name, cmd)


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

    raw_counts, merged_counts = collections.Counter(), collections.Counter()
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
                _, tool, cmd = step
                raw, merged = label_for(tool, cmd)
                if history:  # a pair needs at least one step of context
                    out.write(json.dumps({
                        "session": sid,
                        "step": len(history),
                        "split": split,
                        "recent_user_request": recent_user,
                        "prior_actions": history[-args.context_steps:],
                        "label_raw": raw,
                        "label_merged": merged,
                        "tool_name": tool,
                    }) + "\n")
                    n_pairs += 1
                    raw_counts[raw] += 1
                    merged_counts[merged] += 1
                history.append(raw)

    def baseline(counter: collections.Counter, k: int) -> float:
        tot = sum(counter.values()) or 1
        return 100.0 * sum(v for _, v in counter.most_common(k)) / tot

    stats = {
        "generated_from": args.source,
        "transcripts_seen": len(files),
        "sessions_used": n_sessions,
        "sessions_skipped_too_short": n_skipped,
        "pairs": n_pairs,
        "split_sessions": dict(split_counts),
        "context_steps": args.context_steps,
        "user_chars": args.user_chars,
        "labels_raw": len(raw_counts),
        "labels_merged": len(merged_counts),
        "baseline_raw_top1_pct": round(baseline(raw_counts, 1), 2),
        "baseline_raw_top3_pct": round(baseline(raw_counts, 3), 2),
        "baseline_merged_top1_pct": round(baseline(merged_counts, 1), 2),
        "baseline_merged_top3_pct": round(baseline(merged_counts, 3), 2),
        "distribution_raw": dict(raw_counts.most_common()),
        "distribution_merged": dict(merged_counts.most_common()),
    }
    with open(os.path.join(args.out_dir, "stats.json"), "w") as fh:
        json.dump(stats, fh, indent=2)

    print(f"sessions {n_sessions} (skipped {n_skipped})   pairs {n_pairs:,}")
    print(f"split sessions: {dict(split_counts)}")
    print(f"labels raw={len(raw_counts)} merged={len(merged_counts)}")
    print(f"baselines to beat  raw: top1 {stats['baseline_raw_top1_pct']}%  "
          f"top3 {stats['baseline_raw_top3_pct']}%")
    print(f"                merged: top1 {stats['baseline_merged_top1_pct']}%  "
          f"top3 {stats['baseline_merged_top3_pct']}%")
    print(f"wrote {pairs_path} and stats.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
