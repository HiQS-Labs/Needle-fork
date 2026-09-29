#!/usr/bin/env python3
"""Stage 1c: validate episode links against GitHub (read-only) and tag repo visibility
(HiQS-Labs/XYZ-forge#709, task 2).

Reads:  <out>/sessions_segmented.jsonl   (episodes from task 1)
        <out>/gh_meta.json               (existing metadata; those items skip the API)
Writes: <out>/link_validity.json         cache {"repo#n": {status, created_at, kind, title, via}}
        <out>/repo_visibility.json       cache {"repo": {status, visibility}}
        <out>/sessions_validated.jsonl   episodes with validated links (+ repo_visibility)
        <out>/validation_report.json
        --public-only also writes <out>/sessions_validated_public.jsonl (public-repo links only)

Rules (task 2 spec):
  - every link's item must exist (404 -> dropped, any source);
  - a #N / GH-N-only link is accepted only if the item was created at or before the
    episode end + 1 day -- a prompt cannot refer to an item created after it;
  - explicit URLs, Claude pr-link records and gh-N branches are the preferred sources:
    existence check only (a merged link carrying any strong source takes this path);
  - a lookup that errors (rate limit, 5xx) is UNRESOLVED: the link is parked in
    links_unresolved and re-fetched on the next run (caches are resumable);
  - every linked repo gets a visibility tag (public/private/unknown).

Usage: validate_links.py [--out DIR] [--public-only] [--max-items N]
"""
import argparse, collections, json, os, subprocess, time
from datetime import datetime, timedelta, timezone
from common import add_out_arg, resolve_out, trunc, dump_jsonl

STRONG_SOURCES = {"prompt:url", "claude_pr_link", "clio_branch", "transcript_branch"}

def pt(ts):
    ts = ts.rstrip("Z")
    if "." in ts:
        ts = ts.split(".")[0]
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)

class GhApi:
    """Read-only REST via `gh api -X GET`; 404 -> not_found, other failures -> error."""
    def item(self, repo, number):
        r = subprocess.run(["gh", "api", "-X", "GET", f"repos/{repo}/issues/{number}"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            err = r.stderr.strip()
            if "404" in err:
                return {"status": "not_found"}
            return {"status": "error", "detail": trunc(err, 120)}
        o = json.loads(r.stdout)
        return {"status": "ok", "created_at": o.get("created_at"),
                "kind": "pr" if o.get("pull_request") else "issue", "title": o.get("title")}

    def repo_info(self, repo):
        r = subprocess.run(["gh", "api", "-X", "GET", f"repos/{repo}"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            err = r.stderr.strip()
            if "404" in err:
                return {"status": "not_found"}
            return {"status": "error", "detail": trunc(err, 120)}
        return {"status": "ok", "visibility": json.loads(r.stdout).get("visibility", "unknown")}

def load_cache(path):
    return json.load(open(path)) if os.path.exists(path) else {}

def lookup_item(repo, number, api, meta, cache):
    """Resolve one (repo, number) to a validity record, via caches first."""
    key = f"{repo}#{number}"
    if key in cache and cache[key].get("status") in ("ok", "not_found"):
        return cache[key], False
    m = meta.get(key)
    if m and not m.get("error") and m.get("created_at"):
        rec = {"status": "ok", "created_at": m["created_at"], "kind": m.get("kind"),
               "title": m.get("title"), "via": "gh_meta"}
        cache[key] = rec
        return rec, False
    rec = api.item(repo, number)
    rec.setdefault("via", "api")
    cache[key] = rec
    return rec, True

def lookup_repo(repo, api, cache):
    if repo in cache and cache[repo].get("status") in ("ok", "not_found"):
        return cache[repo], False
    rec = api.repo_info(repo)
    cache[repo] = rec
    return rec, True

def validate_episodes(episodes, api, meta, item_cache=None, repo_cache=None, slack=timedelta(days=1)):
    """Return new episode records with validated links. Mutates the caches in place."""
    item_cache = item_cache if item_cache is not None else {}
    repo_cache = repo_cache if repo_cache is not None else {}
    out = []
    for ep in episodes:
        end = pt(ep["end_ts"]) + slack
        kept, dropped, unresolved = [], [], []
        for l in ep.get("links", []):
            rec, _ = lookup_item(l["repo"], l["number"], api, meta, item_cache)
            rrec, _ = lookup_repo(l["repo"], api, repo_cache)
            vis = rrec.get("visibility", "unknown") if rrec["status"] == "ok" else "unknown"
            if rec["status"] == "error" or rrec["status"] == "error":
                unresolved.append({"repo": l["repo"], "number": l["number"],
                                   "detail": rec.get("detail") or rrec.get("detail")})
                continue
            if rec["status"] == "not_found":
                dropped.append({"repo": l["repo"], "number": l["number"], "confidence": l["confidence"],
                                "sources": l["sources"], "reason": "not_found"})
                continue
            preferred = bool(STRONG_SOURCES & set(l["sources"]))
            if not preferred and rec.get("created_at") and pt(rec["created_at"]) > end:
                dropped.append({"repo": l["repo"], "number": l["number"], "confidence": l["confidence"],
                                "sources": l["sources"], "reason": "created_after_episode_end",
                                "created_at": rec["created_at"]})
                continue
            kept.append({**l, "repo_visibility": vis, "item_created_at": rec["created_at"],
                         "item_kind_resolved": rec.get("kind")})
        e = dict(ep)
        e["links"] = kept
        if dropped:
            e["links_dropped"] = dropped
        if unresolved:
            e["links_unresolved"] = unresolved
        out.append(e)
    return out

def public_only(episodes):
    """Filter to public-repo links only; episodes with no public links are kept, emptied."""
    out = []
    for ep in episodes:
        e = dict(ep)
        e["links"] = [l for l in ep.get("links", []) if l.get("repo_visibility") == "public"]
        e.pop("links_dropped", None)
        e["public_only"] = True
        out.append(e)
    return out

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--public-only", action="store_true",
                    help="also write sessions_validated_public.jsonl (public-repo links only)")
    ap.add_argument("--slack-days", type=float, default=1.0)
    ap.add_argument("--max-items", type=int, default=0, help="debug: cap API item lookups")
    add_out_arg(ap)
    a = ap.parse_args(argv)
    OUT = resolve_out(a.out)
    eps = [json.loads(l) for l in open(os.path.join(OUT, "sessions_segmented.jsonl"))]
    meta = load_cache(os.path.join(OUT, "gh_meta.json"))
    item_cache = load_cache(os.path.join(OUT, "link_validity.json"))
    repo_cache = load_cache(os.path.join(OUT, "repo_visibility.json"))
    api = GhApi()

    # pre-flight: which (repo, number) pairs still need an API call?
    todo = []
    seen = set()
    for ep in eps:
        for l in ep.get("links", []):
            key = (l["repo"], l["number"])
            if key in seen:
                continue
            seen.add(key)
            rec = item_cache.get(f'{key[0]}#{key[1]}')
            m = meta.get(f'{key[0]}#{key[1]}')
            cached_ok = rec and rec.get("status") in ("ok", "not_found")
            meta_ok = m and not m.get("error") and m.get("created_at")
            if not cached_ok and not meta_ok:
                todo.append(key)
    if a.max_items:
        todo = todo[: a.max_items]
    repos_todo = [r for r in {k[0] for k in seen}
                  if r not in repo_cache or repo_cache[r].get("status") not in ("ok", "not_found")]
    print(f"items to fetch: {len(todo)} (of {len(seen)} unique), repos to fetch: {len(repos_todo)}", flush=True)

    done = 0
    for repo, number in todo:
        lookup_item(repo, number, api, meta, item_cache)
        done += 1
        if done % 25 == 0:
            json.dump(item_cache, open(os.path.join(OUT, "link_validity.json"), "w"), indent=1)
            print(f"  {done}/{len(todo)}", flush=True)
        time.sleep(0.05)
    for repo in repos_todo:
        lookup_repo(repo, api, repo_cache)
    json.dump(item_cache, open(os.path.join(OUT, "link_validity.json"), "w"), indent=1)
    json.dump(repo_cache, open(os.path.join(OUT, "repo_visibility.json"), "w"), indent=1)

    validated = validate_episodes(eps, api, meta, item_cache, repo_cache,
                                   slack=timedelta(days=a.slack_days))
    dump_jsonl(os.path.join(OUT, "sessions_validated.jsonl"), validated)
    if a.public_only:
        dump_jsonl(os.path.join(OUT, "sessions_validated_public.jsonl"), public_only(validated))

    st = collections.Counter()
    vis_hist = collections.Counter()
    for ep in validated:
        st["links_kept"] += len(ep["links"])
        st["links_dropped"] += len(ep.get("links_dropped", []))
        st["links_unresolved"] += len(ep.get("links_unresolved", []))
        for d in ep.get("links_dropped", []):
            st[f'dropped_{d["reason"]}'] += 1
        for l in ep["links"]:
            vis_hist[l["repo_visibility"]] += 1
    n_404_unresolved = sum(1 for v in item_cache.values() if v.get("status") == "error")
    n_repo_unresolved = sum(1 for v in repo_cache.values() if v.get("status") == "error")
    report = {
        "episodes": len(validated), **dict(st),
        "link_visibility_histogram": dict(vis_hist.most_common()),
        "unresolved_item_lookups": n_404_unresolved,
        "unresolved_repo_lookups": n_repo_unresolved,
        "unique_items_seen": len(seen),
        "repos": {r: repo_cache[r].get("visibility", "unknown") for r in sorted(repo_cache)},
        "params": {"slack_days": a.slack_days},
    }
    json.dump(report, open(os.path.join(OUT, "validation_report.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k != "repos"}, indent=1))

if __name__ == "__main__":
    main()
