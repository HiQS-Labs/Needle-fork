"""#9 spike, question 0: do governance events EXIST in git history, and how many?

Before any correlation work, this answers the question that can kill the idea
outright. Five governance labels have ZERO corpus support:

    complete_doc, cut_release, park_roadmap_row, promote_capture, publish_release

They are absent from ~/.claude transcripts because they are OUTCOMES -- a doc
moved between PDDA folders, a roadmap row parked, a release cut -- not tool
calls. If they are also absent from git history, no correlation window helps and
#9 needs a different source.

Detection is by PATH and RENAME, not commit message, because the message is the
author's prose while the path change is the act itself. Message text is used
only where the act has no path signature (release tags).

Read-only. Prints aggregate counts. Never prints prompt text or file contents.
"""
import argparse, collections, json, os, re, subprocess, sys

# PDDA lifecycle folders -- a rename ACROSS them is the governance act.
INBOX, WORKING, COMPLETED = "1-INBOX", "2-WORKING", "3-COMPLETED"

def run(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""

def classify(renames, paths, subject, tags_at):
    """Return the set of governance labels this commit evidences."""
    out = set()
    for old, new in renames:
        if INBOX in old and WORKING in new:
            out.add("promote_capture")
        elif WORKING in old and COMPLETED in new:
            out.add("complete_doc")
        elif INBOX in old and COMPLETED in new:
            out.add("complete_doc")
    for p in paths:
        base = os.path.basename(p)
        if base == "ROADMAP.md":
            out.add("park_roadmap_row")
        elif base in ("RELEASES.md", "releases.db", "releases.sql"):
            out.add("cut_release")
    if tags_at:
        out.add("publish_release")
    return out

def census(repo):
    """One pass over the whole history; returns label -> commit count."""
    # tags by commit
    tags = collections.defaultdict(list)
    for line in run(repo, "for-each-ref", "--format=%(objectname) %(refname:short)",
                    "refs/tags").splitlines():
        p = line.split(" ", 1)
        if len(p) == 2:
            tags[p[0]].append(p[1])
    raw = run(repo, "log", "--all", "--name-status", "-M",
              "--format=\x01%H\x02%aI\x02%s")
    counts = collections.Counter()
    events = []
    cur = None
    renames, paths = [], []
    def flush():
        if not cur:
            return
        h, t, subj = cur
        labs = classify(renames, paths, subj, tags.get(h))
        for l in labs:
            counts[l] += 1
        if labs:
            events.append((t, sorted(labs)))
    for line in raw.split("\n"):
        if line.startswith("\x01"):
            flush()
            parts = line[1:].split("\x02")
            cur = (parts[0], parts[1], parts[2] if len(parts) > 2 else "")
            renames, paths = [], []
        elif line and cur:
            f = line.split("\t")
            if f[0].startswith("R") and len(f) >= 3:
                renames.append((f[1], f[2])); paths.append(f[2])
            elif len(f) >= 2:
                paths.append(f[1])
    flush()
    return counts, events

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/Documents/GitHub Repos"))
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    LABELS = ["promote_capture", "complete_doc", "park_roadmap_row",
              "cut_release", "publish_release"]
    total = collections.Counter()
    per_repo = {}
    all_events = {}
    for name in sorted(os.listdir(args.root)):
        repo = os.path.join(args.root, name)
        if not os.path.isdir(os.path.join(repo, ".git")):
            continue
        c, ev = census(repo)
        if c:
            per_repo[name] = dict(c)
            all_events[name] = ev
            total.update(c)

    print(f"{'label':<20}{'commits':>9}   repos")
    for l in LABELS:
        top = sorted(((v.get(l, 0), k) for k, v in per_repo.items()), reverse=True)[:4]
        top = ", ".join(f"{k}:{n}" for n, k in top if n)
        print(f"  {l:<18}{total.get(l,0):>7}   {top}")
    print(f"\nrepos with any governance event: {len(per_repo)}")
    if args.out:
        json.dump({"totals": dict(total), "per_repo": per_repo,
                   "events": {k: v for k, v in all_events.items()}},
                  open(args.out, "w"), indent=2)
        print(f"written: {args.out}")

if __name__ == "__main__":
    main()
