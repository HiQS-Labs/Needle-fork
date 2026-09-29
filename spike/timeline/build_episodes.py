#!/usr/bin/env python3
"""Stage 3: build episodes.jsonl with rule-based weak labels (no LLM).
Inputs: <out>/sessions.jsonl, <out>/gh_meta.json (optional), <out>/gh_request.json (subset).
Usage: build_episodes.py [--all] [--out DIR]   (default: only the GitHub-enriched subset)"""
import json, os, re, sys, argparse, collections
from common import add_out_arg, resolve_out, trunc, dump_jsonl

PURPOSES = ["bug_fix", "feature_enhancement", "research_evaluation", "planning_design",
            "documentation", "maintenance", "testing_validation", "merge_closeout"]
CC = re.compile(r"^\s*(?:\[[^\]]*\]\s*)?([a-zA-Z-]+)(?:\([^)]*\))?!?:\s")
PREFIX_MAP = {
    "fix": "bug_fix", "bugfix": "bug_fix", "hotfix": "bug_fix", "revert": "bug_fix",
    "feat": "feature_enhancement", "feature": "feature_enhancement", "enhance": "feature_enhancement",
    "docs": "documentation", "doc": "documentation",
    "test": "testing_validation", "tests": "testing_validation", "qa": "testing_validation",
    "chore": "maintenance", "build": "maintenance", "deps": "maintenance", "refactor": "maintenance",
    "perf": "maintenance", "style": "maintenance", "ci": "maintenance", "cleanup": "maintenance",
    "research": "research_evaluation", "recon": "research_evaluation", "spike": "research_evaluation",
    "experiment": "research_evaluation", "exp": "research_evaluation", "eval": "research_evaluation",
    "benchmark": "research_evaluation", "audit": "research_evaluation", "investigate": "research_evaluation",
    "plan": "planning_design", "design": "planning_design", "rfc": "planning_design", "roadmap": "planning_design",
    "release": "merge_closeout", "closeout": "merge_closeout", "merge": "merge_closeout", "reconcile": "merge_closeout",
}
LABEL_MAP = {
    "bug": ("bug_fix", 0.7), "regression": ("bug_fix", 0.7), "stability": ("bug_fix", 0.4),
    "enhancement": ("feature_enhancement", 0.6), "feature": ("feature_enhancement", 0.6),
    "documentation": ("documentation", 0.7), "docs": ("documentation", 0.7),
    "tests": ("testing_validation", 0.6), "testing": ("testing_validation", 0.6),
    "chore": ("maintenance", 0.6), "dependencies": ("maintenance", 0.7), "tooling": ("maintenance", 0.4),
    "ci": ("maintenance", 0.4), "refactor": ("maintenance", 0.6),
    "research": ("research_evaluation", 0.6), "experiment": ("research_evaluation", 0.6),
    "spike": ("research_evaluation", 0.6), "investigation": ("research_evaluation", 0.6),
    "planning": ("planning_design", 0.6), "design": ("planning_design", 0.6), "release": ("merge_closeout", 0.5),
}
AREA_RULES = [  # (regex on path, area) first match wins
    (r"(^|/)\.github/workflows/|(^|/)\.gitlab-ci|(^|/)\.circleci/|Jenkinsfile", "ci_cd"),
    (r"(^|/)(\.claude/)?skills?/|Deployed Skills/|(^|/)\.claude/commands/|SKILL\.md$", "skills"),
    (r"(^|/)(tests?|spec|__tests__)/|(^|/)test_[^/]*\.py$|_test\.(py|go|ts|js)$|\.test\.(ts|js|tsx)$", "tests"),
    (r"(^|/)TESTS-RESULTS/|(^|/)benchmark", "evaluation_results"),
    (r"(^|/)(docs?|PROJECT)/|(^|/)[A-Z0-9_-]+\.md$|README|CHANGELOG|\.mdx?$", "documentation"),
    (r"\.(css|scss|html|php|tsx|jsx|vue|svelte)$|(^|/)(templates?|themes?|ui|frontend)/", "ui"),
    (r"(^|/)(hooks|\.claude|\.xyz|config)/|\.(ya?ml|toml|json|ini)$", "config_tooling"),
    (r"\.(sh|bash|zsh)$|(^|/)(scripts|bin|utils)/", "scripts_tooling"),
    (r"\.(py|ts|js|go|rs|rb|swift|java|kt)$", "core_code"),
]
STAGE_PROMPT_RULES = [  # (regex, stage, conf) all matches recorded, in this priority for the single stage
    (r"\b(merge|merged|squash)\b", "merge", 0.6),
    (r"\b(open|create|make|raise|file) (a |the )?(draft )?(pr|pull request)\b|\bgh pr create\b", "pr", 0.7),
    (r"\b(review|re-review|qa|coderabbit|relay|second opinion|feedback)\b", "review", 0.5),
    (r"\b(run|re-?run) (the )?(full )?(tests?|suite|pytest|validate)|\btests? (pass|fail)|\bsuite\b", "test", 0.6),
    (r"\b(implement|fix|add|build|write|refactor|patch|update|change|create)\b", "implement", 0.4),
    (r"\b(plan|investigate|research|recon|look into|analy[sz]e|explore|why|audit|scope)\b|\?\s*$", "investigate_plan", 0.4),
    (r"\b(next task|new task|start-task|now do|move on|next up|let's do)\b|/start-task", "new_task", 0.5),
]
def tool_stage(r):
    name = (r.get("tool") or "").lower(); cmd = (r.get("cmd") or "").lower()
    if cmd:
        if re.search(r"\bgh pr merge\b|\bgit merge\b", cmd): return "merge"
        if re.search(r"\bgh pr create\b", cmd): return "pr"
        if re.search(r"\bgh pr (review|comment|view|checks|diff)\b|/reviews|/comments", cmd): return "review"
        if re.search(r"\bpytest\b|\bunittest\b|validate\.sh|npm (run )?test|\bgo test\b|cargo test|phpunit|shellcheck", cmd): return "test"
        if re.search(r"\bgit (commit|push)\b", cmd): return "commit_push"
        if re.search(r"\bgh issue create\b", cmd): return "new_task"
        if re.search(r"\b(rg|grep|cat|sed -n|head|tail|ls|find|git (log|diff|status|show)|gh (issue|api))\b", cmd): return "investigate_plan"
        return "implement" if re.search(r"apply_patch|> |tee |mv |cp ", cmd) else None
    if name in ("edit", "write", "multiedit", "notebookedit", "apply_patch", "write_to_file", "replace_file_content",
                "multi_replace_file_content", "str_replace_editor"): return "implement"
    if name in ("read", "grep", "glob", "webfetch", "websearch", "view_file", "grep_search", "find_by_name",
                "list_dir", "codebase_search", "read_url_content", "search_web", "view_file_outline"): return "investigate_plan"
    if name in ("task", "agent"): return "investigate_plan"
    return None

def vote(votes):
    agg = collections.defaultdict(float)
    for v in votes: agg[v["value"]] += v["confidence"]
    if not agg: return None
    best = max(agg, key=agg.get); tot = sum(agg.values())
    conf = round(max(v["confidence"] for v in votes if v["value"] == best) * agg[best] / tot, 2)
    return {"value": best, "confidence": conf, "sources": [v for v in votes if v["value"] == best][:6],
            "dissent": sorted({v["value"] for v in votes if v["value"] != best})}

def purpose_votes(item, link_conf):
    out = []
    def add(val, src, c): out.append({"value": val, "source": src, "confidence": round(c * link_conf, 2)})
    m = CC.match(item.get("title") or "")
    if m and m.group(1).lower() in PREFIX_MAP:
        add(PREFIX_MAP[m.group(1).lower()], f'{item["kind"]}_title_prefix:{m.group(1).lower()}', 0.7 if item["kind"] == "pr" else 0.6)
    subs = [s for s in item.get("commit_subjects", []) if not s.lower().startswith("merge ")]
    pc = collections.Counter(PREFIX_MAP[m.group(1).lower()] for s in subs if (m := CC.match(s)) and m.group(1).lower() in PREFIX_MAP)
    if pc:
        val, n = pc.most_common(1)[0]
        add(val, f"commit_prefix_majority:{n}/{len(subs)}", 0.6 * n / max(len(subs), 1) + 0.1)
    for l in item.get("labels", []):
        k = l.lower().strip()
        if k in LABEL_MAP: add(LABEL_MAP[k][0], f"label:{l}", LABEL_MAP[k][1])
    return out

def area_label(items):
    c = collections.Counter(); n = 0
    for it in items:
        for f in it.get("files", []):
            n += 1
            for rx, a in AREA_RULES:
                if re.search(rx, f): c[a] += 1; break
            else: c["other"] += 1
    if not n: return None
    a, k = c.most_common(1)[0]
    return {"value": a, "confidence": round(0.8 * k / n, 2), "source": f"pr_changed_files:{k}/{n}",
            "distribution": dict(c.most_common(5))}

def completion_label(items):
    prs = [i for i in items if i["kind"] == "pr"]; iss = [i for i in items if i["kind"] == "issue"]
    if any(p.get("merged") for p in prs):
        p = next(p for p in prs if p.get("merged"))
        return {"value": "merged", "confidence": round(0.95 * p["_link_conf"], 2), "source": f'github_pr_merged:{p["resolved_repo"]}#{p["number"]}'}
    done = [i for i in iss if i["state"] == "closed" and i.get("state_reason") in (None, "completed")]
    if done: return {"value": "closed_completed", "confidence": round(0.9 * done[0]["_link_conf"], 2), "source": f'github_issue_closed:{done[0]["number"]}'}
    if any(i["state"] == "closed" for i in items):
        return {"value": "closed_not_completed", "confidence": 0.5, "source": "github_closed_unmerged_or_not_planned"}
    if items: return {"value": "open", "confidence": 0.6, "source": "github_state_open"}
    return None

def stage_sequence(sess):
    ev = [(p["ts"], "prompt", p["text"]) for p in sess["prompts"]]
    seq = []
    for ts, _, text in ev:
        t = text.lower()
        for rx, st, c in STAGE_PROMPT_RULES:
            if re.search(rx, t): seq.append({"ts": ts, "stage": st, "source": "prompt_rule", "confidence": c}); break
    # tool stages, bucketed into runs (ts may be None for agy -> ordered by step)
    tools = [(r.get("ts"), tool_stage(r)) for r in sess["replies"] if r["kind"] == "tool"]
    for ts, st in tools:
        if st: seq.append({"ts": ts, "stage": st, "source": "tool_rule", "confidence": 0.6})
    aligned = all(s["ts"] for s in seq)
    if aligned: seq.sort(key=lambda s: s["ts"])
    # agy tool steps carry no timestamp: tool stages are appended after prompt stages (unaligned)
    sess["_stage_ordering"] = "time_aligned" if aligned else "prompts_then_unaligned_tools"
    # collapse consecutive duplicates
    out = []
    for s in seq:
        if out and out[-1]["stage"] == s["stage"]:
            out[-1]["n"] += 1; out[-1]["confidence"] = max(out[-1]["confidence"], s["confidence"])
            if s["source"] not in out[-1]["source"]: out[-1]["source"] += "+" + s["source"]
        else:
            out.append({**s, "n": 1})
    return out

def condense_replies(replies, cap=120):
    keep = replies if len(replies) <= cap else replies[: cap // 2] + [{"kind": "elided", "n": len(replies) - cap}] + replies[-cap // 2:]
    return keep

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true", help="emit every session (episodes_all.jsonl)")
    ap.add_argument("--sessions-file", default="sessions.jsonl",
                    help="input sessions file inside --out (default sessions.jsonl)")
    ap.add_argument("--request-file", default="gh_request.json",
                    help="subset/enrichment request file inside --out (default gh_request.json)")
    ap.add_argument("--out-name", default=None,
                    help="override output filename (default episodes.jsonl / episodes_all.jsonl)")
    add_out_arg(ap)
    a = ap.parse_args(argv)
    OUT = resolve_out(a.out); allmode = a.all
    sessions = {json.loads(l)["session_id"]: json.loads(l) for l in open(os.path.join(OUT, a.sessions_file))}
    meta = json.load(open(os.path.join(OUT, "gh_meta.json"))) if os.path.exists(os.path.join(OUT, "gh_meta.json")) else {}
    req = json.load(open(os.path.join(OUT, a.request_file)))
    subset = {s["session_id"] for s in req["sessions"]}
    ids = list(sessions) if allmode else [s["session_id"] for s in req["sessions"]]
    eps = []; st = collections.Counter(); dist = {"purpose": collections.Counter(), "area": collections.Counter(),
                                                   "completion": collections.Counter(), "stage": collections.Counter()}
    for sid in ids:
        s = sessions[sid]
        linked = []
        for l in s["links"]:
            m = meta.get(f'{l["repo"]}#{l["number"]}')
            if m and not m.get("error"):
                linked.append({**m, "_link_conf": l["confidence"], "link_sources": l["sources"], "link_confidence": l["confidence"]})
        pv = [v for it in linked for v in purpose_votes(it, it["_link_conf"])]
        purpose = vote(pv); area = area_label(linked); comp = completion_label(linked); stages = stage_sequence(s)
        ep = {
            "session_id": sid, "project": s["project"], "repo": s["repo"], "repo_source": s["repo_source"],
            "start_ts": s["start_ts"], "end_ts": s["end_ts"], "machines": s["machines"], "tool": s["tool"],
            "tool_source": s["tool_source"], "branches": s["branches"][:10],
            "transcript": s["transcript"], "github_enriched": sid in subset,
            "opening_prompt": trunc(s["prompts"][0]["text"], 500),
            "user_prompts": [{"ts": p["ts"], "text": trunc(p["text"], 400)} for p in s["prompts"]],
            "closing_prompts": [trunc(p["text"], 300) for p in s["prompts"][-2:]],
            "n_replies": s["n_replies"], "replies_condensed": condense_replies(s["replies"]),
            "link_candidates": s["links"][:25],
            "linked": [{k: v for k, v in it.items() if k != "_link_conf"} for it in linked],
            "weak_labels": {"purpose": purpose, "area": area, "completion": comp, "stage_sequence": stages,
                            "stage_ordering": s.get("_stage_ordering"),
                            "_note": "rule-based, no LLM; confidences are heuristic, not calibrated"},
        }
        eps.append(ep)
        st["episodes"] += 1
        if linked: st["linked_with_metadata"] += 1
        if purpose: st["purpose"] += 1; dist["purpose"][purpose["value"]] += 1
        if area: st["area"] += 1; dist["area"][area["value"]] += 1
        if comp: st["completion"] += 1; dist["completion"][comp["value"]] += 1
        if stages: st["stage_seq"] += 1
        for x in stages: dist["stage"][x["stage"]] += 1
    name = a.out_name or ("episodes_all.jsonl" if allmode else "episodes.jsonl")
    dump_jsonl(os.path.join(OUT, name), eps)
    rep = {"file": name, **st, "distributions": {k: dict(v.most_common()) for k, v in dist.items()}}
    json.dump(rep, open(os.path.join(OUT, name.replace(".jsonl", "_stats.json")), "w"), indent=1)
    print(json.dumps(rep, indent=1))

if __name__ == "__main__":
    main()
