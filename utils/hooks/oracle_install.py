#!/usr/bin/env python3
"""Wire the Oracle into ~/.claude/settings.json -- idempotent, backed up, dry-run by default.

    oracle_install.py            # show what WOULD change
    oracle_install.py --apply    # back up settings.json, then write
    oracle_install.py --remove   # take the Oracle entries out again

Adds a Stop hook (the detached-worker hook, 5 s timeout -- it returns in ~0.25 s)
and a statusLine (refreshInterval 5, so the detached result appears within seconds
of the turn ending). Never touches any other hook or setting. The status line
replaces any existing statusLine entry; say so before applying if one exists.
"""
from __future__ import annotations
import argparse, json, os, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
HOOK_CMD = f'"{PY}" "{os.path.join(HERE, "oracle_stop_hook.py")}"'
STATUS_CMD = f'"{PY}" "{os.path.join(HERE, "oracle_statusline.py")}"'
SETTINGS = os.path.expanduser("~/.claude/settings.json")
MARK = "oracle_stop_hook.py"

def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(); g.add_argument("--apply", action="store_true"); g.add_argument("--remove", action="store_true")
    a = ap.parse_args()
    try:
        cur = json.load(open(SETTINGS))
    except FileNotFoundError:
        cur = {}
    new = json.loads(json.dumps(cur))
    hooks = new.setdefault("hooks", {})
    stop = [h for h in hooks.get("Stop", []) if MARK not in json.dumps(h)]
    if not a.remove:
        stop.append({"hooks": [{"type": "command", "command": HOOK_CMD, "timeout": 5}]})
    if stop: hooks["Stop"] = stop
    elif "Stop" in hooks: del hooks["Stop"]
    if not hooks: del new["hooks"]
    if a.remove:
        if "oracle_statusline.py" in json.dumps(new.get("statusLine", {})): new.pop("statusLine", None)
    else:
        if new.get("statusLine") and "oracle_statusline.py" not in json.dumps(new["statusLine"]):
            print("NOTE: an existing statusLine will be replaced:", json.dumps(new["statusLine"]))
        new["statusLine"] = {"type": "command", "command": STATUS_CMD, "refreshInterval": 5}
    if new == cur:
        print("no change"); return 0
    print("--- would write to", SETTINGS, "---")
    print(json.dumps({k: new[k] for k in ("hooks", "statusLine") if k in new}, indent=2))
    if not a.apply and not a.remove:
        print("\n(dry run; pass --apply)"); return 0
    if os.path.exists(SETTINGS):
        bak = f"{SETTINGS}.bak-{time.strftime('%Y%m%d-%H%M%S')}"; shutil.copy2(SETTINGS, bak); print("backup:", bak)
    tmp = SETTINGS + ".tmp"
    with open(tmp, "w") as fh: json.dump(new, fh, indent=2); fh.write("\n")
    os.replace(tmp, SETTINGS); print("written. Restart Claude Code (or /hooks) to load.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
