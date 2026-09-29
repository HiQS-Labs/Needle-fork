#!/usr/bin/env python3
"""Stage 2b: read-only GitHub metadata via `gh api -X GET` (never writes to GitHub). Resumable:
items already in the output without an error are skipped.
Usage: fetch_github.py [REQUEST_JSON] [META_JSON]   (defaults: <out>/gh_request.json, <out>/gh_meta.json)"""
import json, subprocess, sys, os, time, argparse
from common import DEFAULT_OUT

def gh(path):
    r = subprocess.run(["gh", "api", "-X", "GET", path], capture_output=True, text=True)
    if r.returncode != 0: return None, r.stderr.strip()[:200]
    return json.loads(r.stdout), None

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("request", nargs="?", default=os.path.join(DEFAULT_OUT, "gh_request.json"))
    ap.add_argument("meta", nargs="?", default=os.path.join(DEFAULT_OUT, "gh_meta.json"))
    a = ap.parse_args(argv)
    req = json.load(open(a.request))["items"]
    out = json.load(open(a.meta)) if os.path.exists(a.meta) else {}
    for i, it in enumerate(req):
        key = f'{it["repo"]}#{it["number"]}'
        if key in out and not out[key].get("error"): continue
        iss, err = gh(f'repos/{it["repo"]}/issues/{it["number"]}')
        if iss is None:
            out[key] = {"error": err}; continue
        rec = {"repo": it["repo"], "resolved_repo": iss.get("repository_url", "").split("repos/")[-1],
               "number": it["number"], "kind": "pr" if iss.get("pull_request") else "issue",
               "title": iss.get("title"), "state": iss.get("state"), "state_reason": iss.get("state_reason"),
               "labels": [l["name"] for l in iss.get("labels", [])], "created_at": iss.get("created_at"),
               "closed_at": iss.get("closed_at"), "html_url": iss.get("html_url")}
        if rec["kind"] == "pr":
            pr, _ = gh(f'repos/{it["repo"]}/pulls/{it["number"]}')
            if pr:
                rec.update(merged=bool(pr.get("merged")), merged_at=pr.get("merged_at"), base=pr["base"]["ref"],
                           head=pr["head"]["ref"], changed_files=pr.get("changed_files"))
            files, _ = gh(f'repos/{it["repo"]}/pulls/{it["number"]}/files?per_page=100')
            rec["files"] = [f["filename"] for f in (files or [])]
            commits, _ = gh(f'repos/{it["repo"]}/pulls/{it["number"]}/commits?per_page=100')
            rec["commit_subjects"] = [c["commit"]["message"].split("\n", 1)[0][:120] for c in (commits or [])]
        out[key] = rec
        if i % 10 == 0:
            json.dump(out, open(a.meta, "w"), indent=1); print(i, "/", len(req), flush=True)
    json.dump(out, open(a.meta, "w"), indent=1)
    print("done", len(out), "errors", sum(1 for v in out.values() if v.get("error")))

if __name__ == "__main__":
    main()
