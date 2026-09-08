#!/usr/bin/env python3
"""Explicit feedback on the last Oracle recommendation (#1 §6's feedback loop).

    oracle_vote.py up                     the suggestion was right
    oracle_vote.py down                   it was wrong (label unknown)
    oracle_vote.py down <correct_label>   it was wrong, and this is what I did instead
    oracle_vote.py --session <id> ...     vote on a specific session (default: newest)

Appends one row to data/oracle/feedback.jsonl. Explicit votes complement the
IMPLICIT scoring the Stop hook does automatically (comparing the recommendation
to what the operator actually did next); a vote is for the cases the transcript
cannot see -- "right, but I did it differently" or "wrong, and here is why".
"""
from __future__ import annotations
import argparse, glob, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oracle_config as C

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("vote", choices=["up", "down"])
    ap.add_argument("correct_label", nargs="?", default=None)
    ap.add_argument("--session", default=None)
    ap.add_argument("--note", default=None)
    a = ap.parse_args()
    labels = set(json.load(open(C.load()["labels"]))["labels"])
    if a.correct_label and a.correct_label not in labels:
        print(f"unknown label {a.correct_label!r}; valid: {', '.join(sorted(labels))}")
        return 2
    if a.session:
        path = os.path.join(C.LAST_DIR, f"{a.session}.json")
    else:
        cands = sorted(glob.glob(os.path.join(C.LAST_DIR, "*.json")), key=os.path.getmtime)
        path = cands[-1] if cands else ""
    try:
        rec = json.load(open(path))
    except Exception:
        print("no recommendation on record to vote on"); return 1
    recs = rec.get("recommendations") or []
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source": "explicit",
           "session_id": rec.get("session_id"), "prompt_id": rec.get("prompt_id"),
           "cact": rec.get("cact"), "query": rec.get("query"),
           "predicted": [r["label"] for r in recs], "vote": a.vote,
           "correct_label": a.correct_label, "note": a.note}
    C.ensure_dirs()
    with open(C.FEEDBACK, "a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    shown = ", ".join(row["predicted"]) or "(abstained)"
    print(f"recorded {a.vote} for [{shown}]" + (f" → {a.correct_label}" if a.correct_label else ""))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
