#!/usr/bin/env python3
"""What the feedback loop has learned: precision per label from real usage.

Two sources, reported separately and combined:
  implicit -- the Stop hook compares each recommendation to the label of what
              the operator actually did next. Zero effort, every turn.
  explicit -- /oracle-vote up|down [label].

This is the number that answers "do these labels create too much noise?" (Q3)
with data instead of opinion, and the rows are already in the trainer's
(query, label) shape for the next fine-tune. Aggregates only; never prints
query text.
"""
from __future__ import annotations
import collections, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oracle_config as C

def main() -> int:
    rows = []
    try:
        for line in open(C.FEEDBACK):
            line = line.strip()
            if line: rows.append(json.loads(line))
    except OSError:
        print("no feedback yet"); return 0
    per = collections.defaultdict(lambda: {"shown": 0, "hit": 0, "up": 0, "down": 0})
    imp = {"n": 0, "hit": 0, "abstain": 0}; exp = {"up": 0, "down": 0}
    for r in rows:
        preds = r.get("predicted") or []
        if r["source"] == "implicit":
            imp["n"] += 1
            if not preds: imp["abstain"] += 1; continue
            hit = r.get("actual") in preds
            imp["hit"] += hit
            for p in preds: per[p]["shown"] += 1; per[p]["hit"] += (p == r.get("actual"))
        else:
            exp[r["vote"]] += 1
            for p in preds: per[p][r["vote"]] += 1
    n_ans = imp["n"] - imp["abstain"]
    print(f"implicit : {imp['n']} turns, {imp['abstain']} abstained, "
          f"precision when shown {100*imp['hit']/max(n_ans,1):.1f}% ({imp['hit']}/{n_ans})")
    print(f"explicit : {exp['up']} up, {exp['down']} down\n")
    print(f"{'label':<24}{'shown':>6}{'hit':>6}{'prec':>7}{'up':>4}{'down':>5}")
    for lab, v in sorted(per.items(), key=lambda kv: -kv[1]["shown"]):
        prec = f"{100*v['hit']/v['shown']:.0f}%" if v["shown"] else "--"
        print(f"  {lab:<22}{v['shown']:>6}{v['hit']:>6}{prec:>7}{v['up']:>4}{v['down']:>5}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
