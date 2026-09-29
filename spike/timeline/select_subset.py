#!/usr/bin/env python3
"""Stage 2a: choose a prototype subset (~50 episodes) for GitHub enrichment.
Prefers sessions with a strong link (conf>=0.7), a joined transcript, >=3 prompts; caps per repo.
Reads <out>/sessions.jsonl, writes <out>/gh_request.json."""
import json, os, collections, argparse
from common import add_out_arg, resolve_out

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("n", nargs="?", type=int, default=50, help="number of sessions (default 50)")
    ap.add_argument("--per-repo", type=int, default=10, help="max sessions per repo (default 10)")
    ap.add_argument("--links-per-session", type=int, default=4, help="max links (conf>=0.5) per session")
    add_out_arg(ap)
    a = ap.parse_args(argv)
    OUT = resolve_out(a.out)
    rows = [json.loads(l) for l in open(os.path.join(OUT, "sessions.jsonl"))]
    def score(r):
        strong = [l for l in r["links"] if l["confidence"] >= 0.7]
        return (bool(strong), bool(r["transcript"]), min(r["n_prompts"], 20), len(strong))
    cands = sorted([r for r in rows if any(l["confidence"] >= 0.7 for l in r["links"]) and r["n_prompts"] >= 3],
                   key=score, reverse=True)
    per_repo, chosen = collections.Counter(), []
    for r in cands:
        if per_repo[r["repo"]] >= a.per_repo: continue
        per_repo[r["repo"]] += 1; chosen.append(r)
        if len(chosen) >= a.n: break
    req, sel = {}, []
    for r in chosen:
        ls = [l for l in r["links"] if l["confidence"] >= 0.5][:a.links_per_session]
        sel.append({"session_id": r["session_id"], "links": [(l["repo"], l["number"]) for l in ls]})
        for l in ls: req[f'{l["repo"]}#{l["number"]}'] = {"repo": l["repo"], "number": l["number"], "kind_hint": l["kind"]}
    json.dump({"sessions": sel, "items": list(req.values())}, open(os.path.join(OUT, "gh_request.json"), "w"), indent=1)
    print("sessions", len(sel), "items", len(req), "repos", len(per_repo))

if __name__ == "__main__":
    main()
