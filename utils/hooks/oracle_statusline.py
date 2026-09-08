#!/usr/bin/env python3
"""Claude Code status line for the Oracle: the display surface for #1 §6.

Why the status line and not the Stop hook's output: a Stop hook's stdout goes
to the debug log, and its blocking `reason` is fed to Claude, not shown to the
operator. The status line is re-run after every assistant message (and on a
timer if `refreshInterval` is set), reads JSON on stdin, and prints whatever it
likes -- persistent, non-blocking, always visible. It reads the recommendation
the detached worker wrote and never runs a model itself.

Line 1: the usual model / dir / branch / context. Line 2: the Oracle.
"""
from __future__ import annotations
import json, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oracle_config as C

DIM, BOLD, CYAN, YEL, GRN, RST = "\033[2m", "\033[1m", "\033[36m", "\033[33m", "\033[32m", "\033[0m"

def main() -> int:
    try:
        d = json.load(sys.stdin)
    except Exception:
        d = {}
    model = (d.get("model") or {}).get("display_name", "?")
    cwd = (d.get("workspace") or {}).get("current_dir") or d.get("cwd") or ""
    ctx = (d.get("context_window") or {}).get("used_percentage")
    try:
        branch = subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, timeout=1).stdout.strip()
    except Exception:
        branch = ""
    line1 = f"{BOLD}{model}{RST} {DIM}{os.path.basename(cwd)}{RST}"
    if branch: line1 += f" {DIM}⎇ {branch}{RST}"
    if ctx is not None: line1 += f" {DIM}· ctx {ctx}%{RST}"
    print(line1)

    cfg = C.load()
    if not cfg.get("show", True):
        return 0
    sid = d.get("session_id") or ""
    last = os.path.join(C.LAST_DIR, f"{sid}.json")
    pend = os.path.join(C.PENDING_DIR, f"{sid}.json")
    now = time.time()
    if os.path.exists(pend) and (not os.path.exists(last) or os.path.getmtime(pend) > os.path.getmtime(last)):
        print(f"{CYAN}🔮 oracle{RST} {DIM}thinking…{RST}")
        return 0
    try:
        rec = json.load(open(last))
    except Exception:
        return 0
    if now - os.path.getmtime(last) > float(cfg.get("fresh_seconds", 1800)):
        return 0
    recs = rec.get("recommendations") or []
    if rec.get("error"):
        print(f"{CYAN}🔮 oracle{RST} {DIM}error — see data/oracle/last/{RST}")
    elif not recs:
        print(f"{CYAN}🔮 oracle{RST} {DIM}no suggestion (abstained){RST}")
    else:
        parts = [f"{YEL}{r['label']}{RST}" + (f" {DIM}— {r['why']}{RST}" if r.get("why") else "")
                 for r in recs]
        print(f"{CYAN}🔮 oracle{RST} " + f" {DIM}|{RST} ".join(parts)
              + f"  {DIM}/oracle-vote up|down [label]{RST}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
