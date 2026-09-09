#!/usr/bin/env python3
"""Measure the v1 taxonomy against local Claude Code transcripts.

Reports the numbers issue #1 §2 makes a GATE, not a statistic:
  - mapping coverage  (fraction of calls resolving to a real intent label)
  - per-label support, split governance vs coding
  - the static top-1 / top-3 majority baselines the model must beat
  - the rule-ambiguity rate that invalidated the first-pass labels

Read-only: prints aggregates and writes a JSON summary. It never copies prompt
text, commands or file contents, so its output is safe to commit. Sample
evidence strings are NOT included for that reason -- use --show-evidence for a
local-only spot check and do not commit that output.

    python3 utils/corpus/measure_taxonomy.py --out TESTS-RESULTS/<campaign>/raw-metrics.json
"""
from __future__ import annotations
import re
import argparse, collections, glob, json, math, os, platform, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy as tx  # noqa: E402


def iter_calls(source: str):
    """Yield (session_path, tool_name, tool_input) for every tool_use record."""
    for fp in sorted(glob.glob(os.path.join(source, "**", "*.jsonl"), recursive=True)):
        with open(fp, errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                content = (rec.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name"):
                        yield fp, block["name"], block.get("input") or {}


def ambiguity_rate(commands: list[str]) -> dict:
    """How often the FIRST-PASS whole-string rules were decided by list order.

    This is the number that invalidated the 16bce0b labels: a command matching
    two or more rules had its label chosen by the rule's position in the list.
    """
    multi = sum(1 for c in commands if sum(1 for _, rx in tx.BASH_RE if rx.search(c)) > 1)
    compound = sum(1 for c in commands if any(t in c for t in ("&&", ";", "|")))
    n = len(commands) or 1
    return {"bash_commands": len(commands),
            "multi_rule_pct": round(100 * multi / n, 2),
            "compound_pct": round(100 * compound / n, 2)}


def _sanitise_source(path: str) -> str:
    """`~/.claude/projects`-style shape, with no local mount path."""
    p = path.replace(os.path.expanduser("~"), "~")
    m = re.search(r"(\.claude/projects.*)$", p)
    return "~/" + m.group(1) if m else os.path.basename(p.rstrip("/"))


def probe_machine() -> dict:
    def sh(*cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            return ""
    chip = sh("sysctl", "-n", "machdep.cpu.brand_string")
    # ANE core count is not exposed by sysctl; it is a property of the chip
    # generation, so it is looked up rather than probed. Phase 3/4 needs it in
    # the record because the ANE is the target runtime.
    ane = next((n for k, n in (("M4 Max", 16), ("M4 Pro", 16), ("M4", 16),
                               ("M3", 16), ("M2", 16), ("M1", 16)) if k in chip), None)
    # The operator's computer name is identifying and adds nothing a model or
    # chip does not. Receipts are committed to a PUBLIC repo (CodeRabbit, PR #19).
    return {"machine": sh("sysctl", "-n", "hw.model") or platform.machine(),
            "chip": chip,
            "cores": {"total": int(sh("sysctl", "-n", "hw.ncpu") or 0),
                      "performance": int(sh("sysctl", "-n", "hw.perflevel0.logicalcpu") or 0),
                      "efficiency": int(sh("sysctl", "-n", "hw.perflevel1.logicalcpu") or 0),
                      "ane": ane},
            "memory_gb": round(int(sh("sysctl", "-n", "hw.memsize") or 0) / 1e9, 1),
            "os_version": sh("sw_vers", "-productVersion") or platform.platform(),
            "python": platform.python_version()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--out", help="write a raw-metrics.json receipt here")
    ap.add_argument("--min-support-rate", type=float, default=tx.SUPPORT_FLOOR_RATE,
                    help="labels below this SHARE of calls are FLAGGED FOR SUPPLEMENTATION "
                         "(issue #1 §3b/§3c), never deleted or merged on the floor alone -- see the "
                         "decision record in taxonomy.py. A rate, not a count, so the gate does not "
                         "change meaning with sample size")
    ap.add_argument("--show-evidence", action="store_true",
                    help="LOCAL ONLY: print matched command text per label; never commit it")
    args = ap.parse_args()

    t0 = time.perf_counter()
    counts, sessions, bash_cmds = collections.Counter(), collections.Counter(), []
    evidence = collections.defaultdict(list)
    for path, tool, inp in iter_calls(args.source):
        label, ev = tx.label_call(tool, inp)
        counts[label] += 1
        sessions[path] += 1
        if tool == "Bash":
            bash_cmds.append(inp.get("command") or "")
        if args.show_evidence and len(evidence[label]) < 5:
            evidence[label].append(ev)
    t_label = time.perf_counter() - t0

    total = sum(counts.values())
    if not total:
        print(f"No tool calls under {args.source}", file=sys.stderr)
        return 1

    ranked = counts.most_common()
    top1 = 100 * ranked[0][1] / total
    top3 = 100 * sum(v for _, v in ranked[:3]) / total
    gov_groups = {"pdda", "prs", "xyz"}
    gov = sum(v for k, v in counts.items() if tx.LABELS_V1[k]["group"] in gov_groups)
    # ceil, not int: with int(), 0.1% of 74,909 is 74 -- which is 0.0988%, BELOW the
    # stated floor. The gate must mean 'at least this share'.
    floor = max(1, math.ceil(args.min_support_rate * total))
    thin = sorted(k for k in tx.LABELS_V1 if counts[k] < floor)

    print(f"source            {args.source}")
    print(f"sessions          {len(sessions)}")
    print(f"tool calls        {total:,}")
    print(f"label set         {tx.LABEL_SET_VERSION}  ({len(tx.LABELS_V1)} labels)")
    print(f"MAPPING COVERAGE  {100 * (1 - counts['unmapped'] / total):.2f}%   (gate: unmapped share)")
    print(f"governance share  {100 * gov / total:.2f}%  ({gov:,} calls)")
    print(f"baseline top-1    {top1:.2f}%   ({ranked[0][0]})")
    print(f"baseline top-3    {top3:.2f}%   ({', '.join(k for k, _ in ranked[:3])})")
    print(f"ambiguity         {ambiguity_rate(bash_cmds)}")
    print(f"labelling wall    {t_label:.2f}s")
    print()
    cum = 0
    for k, v in ranked:
        cum += v
        print(f"  {k:24s} {tx.LABELS_V1[k]['group']:8s} {v:6,d} {100*v/total:6.2f}%  cum {100*cum/total:6.2f}%")
    print(f"\nbelow support floor ({args.min_support_rate:.2%} = {floor} calls) -- FLAGGED FOR "
          f"SUPPLEMENTATION (§3b/§3c), not for deletion: {', '.join(thin) or 'none'}")

    if args.show_evidence:
        print("\n--- LOCAL EVIDENCE (do not commit) ---")
        for k, _ in ranked:
            for e in evidence[k]:
                print(f"  {k:22s} {e[:100]}")

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        receipt = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **probe_machine(),
            "git_commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                         capture_output=True, text=True).stdout.strip(),
            "branch": subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                     capture_output=True, text=True).stdout.strip(),
            "target": "taxonomy-v1-measurement",
            "benchmark": "label_call over local Claude Code transcripts",
            # Repo is public: record the source shape, not the operator's home path.
            # Only the shape of the source, never the mount path: a
            # `/Volumes/...` prefix names the operator's local volume.
            "source": _sanitise_source(args.source),
            "sessions": len(sessions),
            "tool_calls": total,
            "label_set_version": tx.LABEL_SET_VERSION,
            "label_count": len(tx.LABELS_V1),
            "mapping_coverage": round(1 - counts["unmapped"] / total, 4),
            "governance_share": round(gov / total, 4),
            "baseline_top1_pct": round(top1, 2),
            "baseline_top3_pct": round(top3, 2),
            "ambiguity": ambiguity_rate(bash_cmds),
            "wall_clock_seconds": round(time.perf_counter() - t0, 3),
            "timing_breakdown": {"read_and_label_seconds": round(t_label, 3)},
            "throughput": {"calls_per_second": round(total / t_label, 1) if t_label else None},
            "labels_below_min_support": thin,
            "min_support_rate": args.min_support_rate,
            "min_support_calls": floor,
            "min_support_action": tx.SUPPORT_FLOOR_ACTION,
            "distribution": dict(ranked),
            "status": "ok",
        }
        with open(args.out, "w") as fh:
            json.dump(receipt, fh, indent=2)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
