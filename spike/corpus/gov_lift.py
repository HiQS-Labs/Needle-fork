"""#9 spike, question 1: does the prompt->event correlation survive PER LABEL,
for the five labels that have zero corpus support?

Aggregate lift proves nothing about whether `park_roadmap_row` specifically is
recoverable -- those five labels are the entire point of #9. This measures each
one separately, against a shuffled-timestamp null control, and restricted to
repos we actually worked in (a third-party clone's release tags are upstream's
releases, not our governance acts).

Read-only. Prints counts and rates only -- never prompt text.
"""
import argparse, bisect, collections, datetime, json, os, random, re, sys

def clio_entries(path):
    txt = open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<!-- clio:id:([0-9a-f-]+):([0-9T:\-Z]+) -->\n## (.+?)\n', txt):
        out.append((m.group(3).strip(), datetime.datetime.fromisoformat(
            m.group(2).replace("Z", "+00:00"))))
    return out

def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clio", default=os.path.expanduser(
        "~/Documents/Noel Saw/0. Claude Prompts.md"))
    ap.add_argument("--census", required=True)
    ap.add_argument("--root", default=os.path.expanduser("~/Documents/GitHub Repos"))
    ap.add_argument("--windows", default="15,30,60")
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    ents = clio_entries(args.clio)
    prompts_by_repo = collections.defaultdict(list)
    for repo, t in ents:
        prompts_by_repo[norm(repo)].append(t)
    census = json.load(open(args.census))

    # Only repos that appear in the CLIO log -- i.e. ones we actually worked in.
    ours, skipped = {}, []
    for repo_dir, events in census["events"].items():
        key = norm(repo_dir)
        hit = key if key in prompts_by_repo else None
        if not hit:                       # try loose match (REBALANCE-OS vs rebalanceOS)
            for k in prompts_by_repo:
                if k == key or k.replace("-", "") == key:
                    hit = k; break
        if hit:
            ours[repo_dir] = (events, sorted(prompts_by_repo[hit]))
        else:
            skipped.append(repo_dir)

    print(f"repos in census: {len(census['events'])}")
    print(f"  worked-in (kept): {len(ours)}  -> {', '.join(sorted(ours))}")
    print(f"  third-party (dropped): {len(skipped)}  -> {', '.join(sorted(skipped)[:8])}...\n")

    LABELS = ["promote_capture", "complete_doc", "park_roadmap_row",
              "cut_release", "publish_release"]
    windows = [int(w) for w in args.windows.split(",")]
    rng = random.Random(0)
    results = {}

    print(f"{'label':<20}{'events':>7}", end="")
    for w in windows:
        print(f"{'  %dm real/null' % w:>18}", end="")
    print()

    for lab in LABELS:
        # every event of this label, with the prompt list of its repo
        pool = []
        for repo, (events, prompts) in ours.items():
            for t, labs in events:
                if lab in labs:
                    pool.append((datetime.datetime.fromisoformat(t), prompts))
        n = len(pool)
        row = {"events": n}
        print(f"  {lab:<18}{n:>7}", end="")
        if n == 0:
            print(f"{'  -- none --':>18}")
            results[lab] = row; continue
        for w in windows:
            def rate(shift_pool):
                hit = 0
                for T, prompts in shift_pool:
                    i = bisect.bisect_left(prompts, T)
                    # a prompt within w minutes BEFORE the event
                    if i > 0 and (T - prompts[i-1]).total_seconds() <= w*60:
                        hit += 1
                return 100*hit/len(shift_pool)
            real = rate(pool)
            nulls = []
            for _ in range(args.trials):
                shifted = []
                for T, prompts in pool:
                    if not prompts: continue
                    lo, hi = prompts[0], prompts[-1]
                    span = (hi-lo).total_seconds() or 1
                    shifted.append((lo + datetime.timedelta(seconds=rng.random()*span), prompts))
                nulls.append(rate(shifted) if shifted else 0.0)
            null = sum(nulls)/len(nulls)
            row[f"{w}m"] = {"real": round(real,1), "null": round(null,1),
                            "lift_pp": round(real-null,1)}
            print(f"{('%.0f%%/%.0f%%' % (real, null)):>18}", end="")
        print()
        results[lab] = row

    if args.out:
        json.dump({"kept_repos": sorted(ours), "dropped_repos": sorted(skipped),
                   "results": results}, open(args.out, "w"), indent=2)
        print(f"\nwritten: {args.out}")

if __name__ == "__main__":
    main()
