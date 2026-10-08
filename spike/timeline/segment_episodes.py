#!/usr/bin/env python3
"""Stage 1b: split sessions into per-task episodes (HiQS-Labs/XYZ-forge#709, task 1).

Reads <out>/sessions.jsonl and writes session-shaped episode records to
<out>/sessions_segmented.jsonl, plus gh_request_segmented.json (the enriched subset remapped
to episode ids), segmentation_report.json and boundary_spotcheck_<n>.json.

A boundary fires before a prompt (never before the first) when ANY of:
  idle_gap   gap from the previous prompt exceeds --min-gap-h hours (default 2)
  new_task   explicit task-switch phrasing ("next task", "/start-task", ...)
  new_anchor the prompt first-mentions a strong GitHub item (URL or GH-N, conf >=
             --anchor-conf) that the current episode has not mentioned, and the episode
             already has a strong anchor -- the first anchor of an episode attaches,
             it never splits. Re-mentioning an item from an *earlier* episode splits
             (returning to a task is a new episode of work on it).

Known limits (v1), by design of the inputs:
  - Stage 1 collapses the CLIO per-entry branch, so branch switches are visible only
    through gh-N link mentions; re-running stage 1 with per-prompt branches would grow
    the frozen 563-session dataset (CLIO and transcript dirs are live) and is deferred.
  - Bare "#N" mentions (conf 0.3, wrong-repo prone) never split.
  - Links without first_ts (transcript_branch, claude_pr_link) attach to the session's
    first episode, flagged assignment_reason="no_first_ts".
  - Replies without ts (agy) attach to the first episode with replies_unaligned=true;
    Arm B uses time-aligned episodes only, so nothing downstream fabricates alignment.
"""
import argparse, bisect, collections, json, os, random, re
from datetime import datetime, timezone
from common import add_out_arg, resolve_out, trunc, dump_jsonl
from build_sessions import URL, GHN, HASHN  # same mention regexes as stage 1

NEW_TASK = re.compile(r"\b(?:next|new|another|different)\s+task\b|\bnext up\b|/start-task|\bstart-task\b", re.I)
# A prompt opening with one of these is answering the previous prompt (Q&A continuation), not
# starting a task: demotes an idle-gap boundary (task resumption after a break, spot-check failure
# mode #1). Stronger reasons (new_task, new_anchor) still fire.
RESPONSE_OPENER = re.compile(
    r"^(?:yes|no|ok|okay|yep|nope|leave it|apply|approved|approve|ship it|go for it|"
    r"sounds good|correct|right|go ahead|proceed)\b[.,!:\s]", re.I)
# "Q1: ..." / "A2) ..." answers the previous episode's question list; a question about the
# previous episode's own output ("Is above ...?") is likewise a continuation, not a task start.
QA_OPENER = re.compile(r"^(?:q|a)\s*\d+\s*[.:)]", re.I)
PREV_REF_QUESTION = re.compile(
    r"^\s*(?:is|was|does|did|has|have|will|would|can|could|should)\s+(?:above|that|it|this)\b", re.I)
# A pasted agent report ("From Agy: ...", "Ran command: ...") is relay content, not an operator
# task start: anchors inside it do not split (with <cross-session-message>, spot-check mode #2).
RELAY_OPENER = re.compile(r"^(?:from\s+[a-z]+[\.:]|ran command:)", re.I)

def pt(ts):
    ts = ts.rstrip("Z")
    if "." in ts:
        ts = ts.split(".")[0]  # drop fractional seconds (transcript timestamps carry millis)
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)

def prompt_strong_mentions(text, repo):
    """{(repo, number): confidence} for strong mentions in one prompt, same rules as stage 1."""
    out = {}
    for o, r, _, n in URL.findall(text or ""):
        out[(f"{o}/{r}", int(n))] = 0.7
    if repo:
        for n in GHN.findall(text or ""):
            out[(repo, int(n))] = 0.5
    return out

def prompt_weak_mentions(text, repo):
    """Bare #N mentions (conf 0.3, resolve to the session repo): they never trigger a boundary,
    but they mark an item as known to the episode so a later strong mention of the SAME item
    (URL / GH-N) does not split mid-task."""
    return {(repo, int(n)) for n in HASHN.findall(text or "")} if repo else set()

def segment_session(s, min_gap_h=2.0, anchor_conf=0.5):
    """Split one sessions.jsonl record into episode records (same schema + extras).

    `anchors` holds the current episode's strong anchors plus a "__known__" set of every
    item mentioned at any strength: weak mentions reserve an item without anchoring it."""
    prompts = s["prompts"]
    bounds, anchors = [], {}
    for i in range(len(prompts)):
        strong = {k: c for k, c in prompt_strong_mentions(prompts[i]["text"], s.get("repo")).items()
                  if c >= anchor_conf}
        known = set(strong) | prompt_weak_mentions(prompts[i]["text"], s.get("repo"))
        if i == 0:
            anchors.update(strong)
            anchors["__known__"] = known
            continue
        reasons, demoted = [], []
        text = prompts[i]["text"] or ""
        gap_h = (pt(prompts[i]["ts"]) - pt(prompts[i - 1]["ts"])).total_seconds() / 3600
        if gap_h > min_gap_h:
            if RESPONSE_OPENER.match(text) or QA_OPENER.match(text) or PREV_REF_QUESTION.match(text):
                demoted.append("idle_gap_demoted:response_opener")
            else:
                reasons.append(f"idle_gap:{gap_h:.1f}h")
        if NEW_TASK.search(text):
            reasons.append("new_task")
        relay = RELAY_OPENER.match(text.lstrip()) or text.lstrip().startswith("<cross-session-message")
        known_set = anchors.get("__known__", set())
        fresh = [k for k in strong if k not in known_set]
        if fresh and known_set:  # an episode with no mentioned item yet takes its first anchor
            if relay:
                demoted.append("new_anchor_demoted:relay_or_cross_session")
            else:
                reasons.append("new_anchor:" + ",".join(f"{k[0]}#{k[1]}" for k in sorted(fresh)))
        s.setdefault("_demotions", []).extend(demoted)
        if reasons:
            bounds.append((i, reasons))
            anchors = {"__known__": known}  # fresh episode starts from this prompt's mentions only
        else:
            anchors["__known__"] = anchors.get("__known__", set()) | known
        anchors.update(strong)

    starts = [0] + [i for i, _ in bounds]
    reason_map = dict(bounds)
    start_ts = [pt(prompts[i]["ts"]) for i in starts]
    eps = []
    for k, st in enumerate(starts):
        en = starts[k + 1] if k + 1 < len(starts) else len(prompts)
        ep_prompts = prompts[st:en]
        # replies: ts-bearing -> window [start_k, start_{k+1}); last episode keeps the tail
        ep_replies, unaligned = [], 0
        for r in s["replies"]:
            if r.get("ts"):
                j = bisect.bisect_right(start_ts, pt(r["ts"])) - 1
                if j == k:
                    ep_replies.append(r)
            elif k == 0:
                ep_replies.append(r)
                unaligned += 1
        ep_links = []
        for l in s["links"]:
            if l.get("first_ts"):
                j = bisect.bisect_right(start_ts, pt(l["first_ts"])) - 1
                if j == k:
                    ep_links.append(l)
            elif k == 0:
                ep_links.append({**l, "assignment_reason": "no_first_ts"})
        rec = {
            "session_id": f'{s["session_id"]}#{k + 1}', "parent_session_id": s["session_id"],
            "episode_index": k + 1, "n_episodes": len(starts),
            "start_reasons": reason_map.get(st, ["session_start"]),
            "project": s["project"], "repo": s["repo"], "repo_source": s["repo_source"],
            "start_ts": ep_prompts[0]["ts"], "end_ts": ep_prompts[-1]["ts"],
            "machines": s["machines"], "tool": s["tool"], "tool_source": s["tool_source"],
            "branches": s["branches"], "transcript": s["transcript"],
            "prompts": ep_prompts, "n_prompts": len(ep_prompts),
            "replies": ep_replies, "n_replies": len(ep_replies),
            "links": ep_links,
        }
        if unaligned:
            rec["replies_unaligned"] = True
            rec["n_replies_unaligned"] = unaligned
        eps.append(rec)
    return eps

def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return None if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-gap-h", type=float, default=2.0)
    ap.add_argument("--anchor-conf", type=float, default=0.5)
    ap.add_argument("--spotcheck", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260928)
    add_out_arg(ap)
    a = ap.parse_args(argv)
    OUT = resolve_out(a.out)
    rows = [json.loads(l) for l in open(os.path.join(OUT, "sessions.jsonl"))]

    all_eps, boundaries, hist = [], [], collections.Counter()
    demoted_hist = collections.Counter()
    for s in rows:
        eps = segment_session(s, a.min_gap_h, a.anchor_conf)
        all_eps.extend(eps)
        for d in s.pop("_demotions", []):
            demoted_hist[d.split(":", 1)[0]] += 1
        for prev, ep in zip(eps, eps[1:]):
            for r in ep["start_reasons"]:
                hist[r.split(":", 1)[0]] += 1
                boundaries.append({"prev": prev, "episode": ep, "reason": r})
    dump_jsonl(os.path.join(OUT, "sessions_segmented.jsonl"), all_eps)

    # enriched subset remapped to episode ids (same links, now per episode)
    seg_req = {"sessions": [], "items": []}
    items = {}
    req_path = os.path.join(OUT, "gh_request.json")
    if os.path.exists(req_path):
        req = json.load(open(req_path))
        by_sid = collections.defaultdict(list)
        for e in all_eps:
            by_sid[e["parent_session_id"]].append(e)
        for ent in req["sessions"]:
            for e in by_sid.get(ent["session_id"], []):
                ls = [(l["repo"], l["number"]) for l in e["links"] if l["confidence"] >= 0.5][:4]
                seg_req["sessions"].append({"session_id": e["session_id"], "links": ls})
                for rp, num in ls:
                    items[f"{rp}#{num}"] = {"repo": rp, "number": num}
        seg_req["items"] = list(items.values())
    json.dump(seg_req, open(os.path.join(OUT, "gh_request_segmented.json"), "w"), indent=1)

    # dissent check on the enriched subset: same vote logic as build_episodes
    dissent = None
    meta_path = os.path.join(OUT, "gh_meta.json")
    if os.path.exists(meta_path) and os.path.exists(req_path):
        from build_episodes import purpose_votes, vote
        meta = json.load(open(meta_path))
        old = [json.loads(l) for l in open(os.path.join(OUT, "episodes.jsonl"))]
        old_lab = [e for e in old if e["weak_labels"]["purpose"]]
        subset_ids = {e["session_id"] for e in seg_req["sessions"]}
        new_lab = new_dis = 0
        for e in all_eps:
            if e["session_id"] not in subset_ids:
                continue
            votes = [v for l in e["links"] if (m := meta.get(f'{l["repo"]}#{l["number"]}')) and not m.get("error")
                     for v in purpose_votes({**m, "_link_conf": l["confidence"]}, l["confidence"])]
            p = vote(votes)
            if p:
                new_lab += 1
                new_dis += bool(p["dissent"])
        dissent = {"before": {"labeled": len(old_lab), "dissent": sum(bool(e["weak_labels"]["purpose"]["dissent"]) for e in old_lab)},
                   "after": {"labeled": new_lab, "dissent": new_dis}}

    spans_h = [(pt(e["end_ts"]) - pt(e["start_ts"])).total_seconds() / 3600 for e in all_eps]
    report = {
        "sessions": len(rows), "episodes": len(all_eps),
        "episodes_per_session_median": median([sum(1 for e in all_eps if e["parent_session_id"] == s["session_id"])
                                               for s in rows]),
        "max_episodes_in_session": max((e["n_episodes"] for e in all_eps), default=0),
        "median_prompts_per_episode": median([e["n_prompts"] for e in all_eps]),
        "median_span_hours": round(median(spans_h), 2) if spans_h else None,
        "single_prompt_episodes": sum(e["n_prompts"] == 1 for e in all_eps),
        "boundaries_total": len(boundaries),
        "boundary_reason_histogram": dict(hist.most_common()),
        "demoted_boundaries": dict(demoted_hist.most_common()),
        "links_no_first_ts": sum(bool(l.get("assignment_reason")) for e in all_eps for l in e["links"]),
        "episodes_with_unaligned_replies": sum(bool(e.get("replies_unaligned")) for e in all_eps),
        "dissent_check": dissent,
        "params": {"min_gap_h": a.min_gap_h, "anchor_conf": a.anchor_conf},
    }
    json.dump(report, open(os.path.join(OUT, "segmentation_report.json"), "w"), indent=1)

    if a.spotcheck and boundaries:
        rng = random.Random(a.seed)
        sample = rng.sample(boundaries, min(a.spotcheck, len(boundaries)))
        spot = [{"parent_session_id": b["episode"]["parent_session_id"],
                 "boundary_ts": b["episode"]["start_ts"], "reason": b["reason"],
                 "tool": b["episode"]["tool"], "repo": b["episode"]["repo"],
                 "n_prompts_before": b["prev"]["n_prompts"], "n_prompts_after": b["episode"]["n_prompts"],
                 "prev_prompt_last": trunc(b["prev"]["prompts"][-1]["text"], 280),
                 "next_prompt_first": trunc(b["episode"]["prompts"][0]["text"], 280)}
                for b in sample]
        json.dump(spot, open(os.path.join(OUT, f"boundary_spotcheck_{len(spot)}.json"), "w"), indent=1)
    print(json.dumps(report, indent=1))

if __name__ == "__main__":
    main()
