#!/usr/bin/env python3
"""Stage 1: parse the CLIO prompt log, join transcripts, extract GitHub link candidates.
Read-only on all sources. Writes out/sessions.jsonl, out/link_candidates.json, out/stage1_stats.json."""
import re, os, json, glob, argparse, subprocess, collections
from common import *

MARK = re.compile(r"^<!-- clio:id:(.+):(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) -->\s*$")
URL = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/(issues|pull)/(\d+)")
GHN = re.compile(r"(?<![A-Za-z0-9])(?:GH|gh)[- ]?#?(\d{1,5})(?![0-9])")
HASHN = re.compile(r"(?:(?<=\s)|(?<=^)|(?<=\())#(\d{2,5})(?![0-9A-Za-z])")
BRANCH_GH = re.compile(r"(?:^|[/_-])gh-?(\d{1,5})(?![0-9])", re.I)
REPO_URL = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")

# ---------------------------------------------------------------- CLIO parse
def parse_clio(path):
    entries, cur, raw_markers = [], None, 0
    def flush():
        if cur is not None:
            q = "\n".join(cur["_q"]).strip()
            if q.startswith('"') and q.endswith('"') and len(q) >= 2: q = q[1:-1]
            cur["prompt"] = q; del cur["_q"]; entries.append(cur)
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip("\n")
            m = MARK.match(line)
            if m:
                flush(); raw_markers += 1
                cur = {"session_id": m.group(1), "ts": m.group(2), "line": ln, "project": None,
                       "local_ts": None, "machine": None, "branch": None, "tool": None, "_q": [], "_hdr": 0}
                continue
            if cur is None: continue
            if cur["_hdr"] == 0 and line.startswith("## "):
                cur["project"] = line[3:].strip() or None; cur["_hdr"] = 1; continue
            if cur["_hdr"] == 1 and line.strip():
                cur["local_ts"] = line.strip(); cur["_hdr"] = 2; continue
            if cur["_hdr"] == 2 and line.strip():
                parts = [p.strip() for p in line.split(" · ")]
                cur["machine"] = parts[0]
                if len(parts) >= 3: cur["branch"], cur["tool"] = parts[1], parts[2]
                elif len(parts) == 2:
                    if parts[1] in KNOWN_TOOLS: cur["tool"] = parts[1]
                    else: cur["branch"] = parts[1]
                cur["_hdr"] = 3; continue
            if line.startswith(">"):
                cur["_q"].append(line[2:] if line.startswith("> ") else line[1:])
            # all other lines (repeated '# Agent Prompt Log' headers, CLIO:ENTRIES markers,
            # blank lines) are ignored: they belong to concatenated file headers.
        flush()
    for e in entries: e.pop("_hdr", None)
    return entries, raw_markers

# ------------------------------------------------------------ transcripts idx
def index_transcripts(claude_dir, codex_dir, agy_dir):
    """Index transcripts by session id. Claude: top-level <project>/<id>.jsonl only (subagent
    sidechains excluded). Codex: rollout-*-<uuid>.jsonl. agy: conversations/<id>.db + brain/<id>/."""
    idx = {"claude": {}, "codex": {}, "agy_db": {}, "agy_brain": {}}
    for p in glob.glob(os.path.join(claude_dir, "*/*.jsonl")):
        idx["claude"][os.path.basename(p)[:-6]] = p
    for p in glob.glob(os.path.join(codex_dir, "**/*.jsonl"), recursive=True):
        m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$", p)
        if m: idx["codex"][m.group(1)] = p
    for p in glob.glob(os.path.join(agy_dir, "conversations/*.db")):
        idx["agy_db"][os.path.basename(p)[:-3]] = p
    for p in glob.glob(os.path.join(agy_dir, "brain/*")):
        if os.path.isdir(p): idx["agy_brain"][os.path.basename(p)] = p
    return idx

_remote_cache = {}
def git_remote(cwd):
    if not cwd: return None
    if cwd in _remote_cache: return _remote_cache[cwd]
    r = None
    if os.path.isdir(cwd):
        try:
            r = subprocess.run(["git", "-C", cwd, "config", "--get", "remote.origin.url"],
                               capture_output=True, text=True, timeout=5).stdout.strip() or None
        except Exception: r = None
    _remote_cache[cwd] = r
    return r

def repo_from_remote(u):
    if not u: return None
    m = REPO_URL.search(u.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else None

CODEX_EXEC = re.compile(r"""exec_command\(\{[^}]*?["']?cmd["']?\s*:\s*(["'`])((?:\\.|(?!\1).)*)\1""", re.S)
CODEX_PATCH_FILE = re.compile(r"\*\*\* (?:Update|Add|Delete) File: ([^\n\\]+)")

def summarize_tool(name, inp):
    if isinstance(inp, str):
        try: inp = json.loads(inp)
        except Exception:
            # Codex "exec" wraps calls in JS: tools.exec_command({"cmd": "..."}) / tools.apply_patch(...)
            m = CODEX_EXEC.search(inp)
            if m:
                raw = m.group(2)
                try: cmd = json.loads('"' + raw.replace("\\'", "'") + '"') if m.group(1) != "`" else raw
                except Exception: cmd = raw.replace("\\n", "\n")
                return {"tool": name, "cmd": trunc(cmd, 160)}
            if "apply_patch" in inp:
                f = CODEX_PATCH_FILE.search(inp)
                return {"tool": "apply_patch", "path": trunc(f.group(1), 160) if f else None}
            return {"tool": name, "arg": trunc(inp, 160)}
    if not isinstance(inp, dict): return {"tool": name}
    for k in ("command", "cmd", "CommandLine", "commandLine"):
        if k in inp:
            v = inp[k]; v = " ".join(v) if isinstance(v, list) else str(v)
            return {"tool": name, "cmd": trunc(v, 160)}
    for k in ("file_path", "path", "TargetFile", "AbsolutePath", "notebook_path"):
        if k in inp: return {"tool": name, "path": trunc(str(inp[k]), 160)}
    for k in ("pattern", "Pattern", "Query", "query", "url", "description", "prompt"):
        if k in inp: return {"tool": name, "arg": trunc(str(inp[k]), 120)}
    return {"tool": name, "keys": sorted(inp)[:6]}

def parse_claude(path):
    replies, meta = [], {"cwds": collections.Counter(), "branches": collections.Counter(), "pr_links": []}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try: o = json.loads(line)
            except Exception: continue
            t = o.get("type")
            if o.get("cwd"): meta["cwds"][o["cwd"]] += 1
            if o.get("gitBranch"): meta["branches"][o["gitBranch"]] += 1
            if t == "pr-link":
                meta["pr_links"].append({"repo": o.get("prRepository"), "number": o.get("prNumber"), "url": o.get("prUrl")})
            if t != "assistant" or o.get("isSidechain"): continue
            c = (o.get("message") or {}).get("content")
            items = c if isinstance(c, list) else [{"type": "text", "text": c}] if isinstance(c, str) else []
            for it in items:
                if it.get("type") == "text" and (it.get("text") or "").strip():
                    replies.append({"ts": o.get("timestamp"), "kind": "text", "text": trunc(it["text"], 300)})
                elif it.get("type") == "tool_use":
                    replies.append({"ts": o.get("timestamp"), "kind": "tool", **summarize_tool(it.get("name"), it.get("input"))})
    return replies, meta

def parse_codex(path):
    replies, meta = [], {"cwds": collections.Counter(), "branches": collections.Counter(), "repo_urls": collections.Counter()}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try: o = json.loads(line)
            except Exception: continue
            p = o.get("payload") or {}
            ts = o.get("timestamp")
            if o.get("type") == "session_meta":
                if p.get("cwd"): meta["cwds"][p["cwd"]] += 1
                g = p.get("git") or {}
                if g.get("repository_url"): meta["repo_urls"][g["repository_url"]] += 1
                if g.get("branch"): meta["branches"][g["branch"]] += 1
            elif o.get("type") == "turn_context" and p.get("cwd"):
                meta["cwds"][p["cwd"]] += 1
            elif o.get("type") == "response_item":
                pt = p.get("type")
                if pt == "message" and p.get("role") == "assistant":
                    txt = " ".join(x.get("text", "") for x in p.get("content") or [] if isinstance(x, dict))
                    if txt.strip(): replies.append({"ts": ts, "kind": "text", "text": trunc(txt, 300)})
                elif pt in ("function_call", "custom_tool_call", "local_shell_call"):
                    inp = p.get("arguments", p.get("input", p.get("action")))
                    replies.append({"ts": ts, "kind": "tool", **summarize_tool(p.get("name") or pt, inp)})
    return replies, meta

def parse_agy(db, brain):
    """Partial: tool calls only (step_type 132: name at field path (5,4,2), args at (5,4,3)).
    Assistant prose lives in undocumented protobuf fields and is NOT extracted; brain artifacts
    (implementation_plan.md, walkthrough.md, task.md) are listed by name + first heading."""
    replies, meta = [], {"cwds": collections.Counter(), "branches": collections.Counter()}
    if db:
        try:
            con = ro_sqlite(db)
            for idx, st, payload in con.execute("select idx, step_type, step_payload from steps order by idx"):
                if st != 132 or not payload: continue
                name = args = None
                for pa, s in pb_strings(payload):
                    if pa[-3:] == (5, 4, 2) and name is None: name = s
                    elif pa[-3:] == (5, 4, 3) and args is None: args = s
                if name:
                    r = {"ts": None, "kind": "tool", "step": idx, **summarize_tool(name, args or "")}
                    replies.append(r)
                    if args:
                        try:
                            a = json.loads(args)
                            for k in ("Cwd", "cwd", "SearchDirectory"):
                                if isinstance(a, dict) and a.get(k): meta["cwds"][a[k]] += 1; break
                        except Exception: pass
            con.close()
        except Exception as e:
            meta["error"] = trunc(repr(e), 120)
    if brain:
        for fn in sorted(os.listdir(brain)):
            if fn.endswith(".md"):
                head = ""
                try:
                    with open(os.path.join(brain, fn), encoding="utf-8", errors="replace") as f:
                        for l in f:
                            if l.startswith("#"): head = l.strip("# \n"); break
                except Exception: pass
                replies.append({"ts": None, "kind": "artifact", "path": fn, "text": trunc(head, 120)})
    return replies, meta

# -------------------------------------------------------------- link extract
def extract_links(text, default_repo, source, conf_hash=0.3):
    out = []
    for o, r, kind, n in URL.findall(text or ""):
        out.append({"repo": f"{o}/{r}", "number": int(n), "kind": "pr" if kind == "pull" else "issue",
                    "source": f"{source}:url", "confidence": 0.7})
    if default_repo:
        for n in GHN.findall(text or ""):
            out.append({"repo": default_repo, "number": int(n), "kind": None, "source": f"{source}:GH-N", "confidence": 0.5})
        for n in HASHN.findall(text or ""):
            out.append({"repo": default_repo, "number": int(n), "kind": None, "source": f"{source}:#N", "confidence": conf_hash})
    return out

def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clio-log", default=env_path("NEEDLE_TL_CLIO_LOG"),
                    help="CLIO prompt log markdown (env NEEDLE_TL_CLIO_LOG; required)")
    ap.add_argument("--claude-dir", default=env_path("NEEDLE_TL_CLAUDE_DIR", "~/.claude/projects"))
    ap.add_argument("--codex-dir", default=env_path("NEEDLE_TL_CODEX_DIR", "~/.codex/sessions"))
    ap.add_argument("--agy-dir", default=env_path("NEEDLE_TL_AGY_DIR", "~/.gemini/antigravity"))
    add_out_arg(ap)
    a = ap.parse_args(argv)
    if not a.clio_log or not os.path.isfile(a.clio_log):
        ap.error("--clio-log (or NEEDLE_TL_CLIO_LOG) must point to an existing CLIO prompt log")
    return a

def main(argv=None):
    a = parse_args(argv)
    OUT = resolve_out(a.out)
    entries, raw_markers = parse_clio(a.clio_log)
    # dedupe on (session_id, ts); keep first occurrence, record duplicates
    seen, uniq, dups = {}, [], []
    for e in entries:
        k = (e["session_id"], e["ts"])
        if k in seen:
            dups.append({"key": list(k), "same_prompt": seen[k]["prompt"] == e["prompt"], "lines": [seen[k]["line"], e["line"]]})
            continue
        seen[k] = e; uniq.append(e)
    inversions = sum(1 for a, b in zip(entries, entries[1:]) if b["ts"] > a["ts"])
    sessions = collections.OrderedDict()
    for e in sorted(uniq, key=lambda e: (e["ts"], e["line"])):
        sessions.setdefault(e["session_id"], []).append(e)

    # repo universe + project->repo majority map from URLs in prompts
    proj_repo = collections.defaultdict(collections.Counter)
    for e in uniq:
        for o, r, _, _ in URL.findall(e["prompt"]):
            proj_repo[(e["project"] or "").upper()][f"{o}/{r}"] += 1

    idx = index_transcripts(os.path.expanduser(a.claude_dir), os.path.expanduser(a.codex_dir), os.path.expanduser(a.agy_dir))
    rows, link_cands = [], []
    stats = collections.Counter()
    for sid, es in sessions.items():
        bare = sid[5:] if sid.startswith("sess_") else sid
        tools = collections.Counter(e["tool"] for e in es if e["tool"])
        tr = None
        if bare in idx["claude"]:
            tr = ("claude-code", idx["claude"][bare]); replies, meta = parse_claude(tr[1])
        elif bare in idx["codex"]:
            tr = ("codex", idx["codex"][bare]); replies, meta = parse_codex(tr[1])
        elif bare in idx["agy_db"] or bare in idx["agy_brain"]:
            tr = ("agy", idx["agy_db"].get(bare) or idx["agy_brain"].get(bare))
            replies, meta = parse_agy(idx["agy_db"].get(bare), idx["agy_brain"].get(bare))
        else:
            replies, meta = [], {"cwds": collections.Counter(), "branches": collections.Counter()}
        tool = tools.most_common(1)[0][0] if tools else (tr[0] if tr else ("zcode" if sid.startswith("sess_") else None))
        tool_src = "clio" if tools else ("transcript_match" if tr else ("id_prefix" if tool else None))
        # repo resolution
        project = collections.Counter(e["project"] for e in es if e["project"]).most_common(1)
        project = project[0][0] if project else None
        repo_votes = collections.Counter()
        for u, c in meta.get("repo_urls", {}).items():
            rr = repo_from_remote(u)
            if rr: repo_votes[rr] += 100
        for cwd, c in meta["cwds"].most_common(3):
            rr = repo_from_remote(git_remote(cwd))
            if rr: repo_votes[rr] += 50
        pr = proj_repo.get((project or "").upper())
        if pr:
            # prefer repo whose name matches the project heading
            name_match = [r for r in pr if r.split("/")[1].upper().replace("_", "-") == (project or "").upper()]
            for r in (name_match or [pr.most_common(1)[0][0]]): repo_votes[r] += 10
        repo = repo_votes.most_common(1)[0][0] if repo_votes else None
        repo_src = ("transcript_git" if repo_votes and repo_votes[repo] >= 50 else "project_heading_url_majority") if repo else None
        # links
        links = []
        for e in es:
            links += [dict(l, ts=e["ts"]) for l in extract_links(e["prompt"], repo, "prompt")]
            for m in BRANCH_GH.findall(e["branch"] or ""):
                if repo: links.append({"repo": repo, "number": int(m), "kind": None, "source": "clio_branch", "confidence": 0.8, "ts": e["ts"]})
        for b in meta["branches"]:
            for m in BRANCH_GH.findall(b):
                if repo: links.append({"repo": repo, "number": int(m), "kind": None, "source": "transcript_branch", "confidence": 0.8, "ts": None})
        for pl in meta.get("pr_links", []):
            if pl.get("repo") and pl.get("number"):
                links.append({"repo": pl["repo"], "number": int(pl["number"]), "kind": "pr", "source": "claude_pr_link", "confidence": 0.9, "ts": None})
        # merge duplicates: keep max confidence, union sources
        merged = {}
        for l in links:
            k = (l["repo"].lower(), l["number"])
            if k not in merged:
                merged[k] = {"repo": l["repo"], "number": l["number"], "kind": l["kind"], "sources": [l["source"]],
                             "confidence": l["confidence"], "first_ts": l["ts"], "mentions": 1}
            else:
                m = merged[k]; m["mentions"] += 1
                if l["source"] not in m["sources"]: m["sources"].append(l["source"])
                m["confidence"] = max(m["confidence"], l["confidence"]); m["kind"] = m["kind"] or l["kind"]
                if l["ts"] and (not m["first_ts"] or l["ts"] < m["first_ts"]): m["first_ts"] = l["ts"]
        links = sorted(merged.values(), key=lambda l: (-l["confidence"], -l["mentions"]))
        row = {
            "session_id": sid, "project": project,
            "start_ts": es[0]["ts"], "end_ts": es[-1]["ts"], "n_prompts": len(es),
            "machines": sorted({e["machine"] for e in es if e["machine"]}),
            "branches": sorted({e["branch"] for e in es if e["branch"]} | set(meta["branches"])),
            "tool": tool, "tool_source": tool_src,
            "repo": repo, "repo_source": repo_src,
            "transcript": {"kind": tr[0], "path": tr[1].replace(HOME, "~")} if tr else None,
            "prompts": [{"ts": e["ts"], "text": e["prompt"]} for e in es],
            "replies": replies, "n_replies": len(replies),
            "links": links,
        }
        if meta.get("error"): row["transcript_error"] = meta["error"]
        rows.append(row)
        stats["sessions"] += 1
        if tr: stats[f"joined_{tr[0]}"] += 1
        if links: stats["linked_any"] += 1
        if any(l["confidence"] >= 0.7 for l in links): stats["linked_strong"] += 1
        for l in links: link_cands.append({"session_id": sid, **l})
    dump_jsonl(os.path.join(OUT, "sessions.jsonl"), rows)
    json.dump(link_cands, open(os.path.join(OUT, "link_candidates.json"), "w"), indent=0)
    s = {"raw_markers": raw_markers, "entries_parsed": len(entries), "entries_unique": len(uniq),
         "duplicates": dups, "file_order_inversions": inversions, **stats,
         "transcript_index": {k: len(v) for k, v in idx.items()},
         "tool_counts": collections.Counter(r["tool"] for r in rows),
         "tool_source_counts": collections.Counter(r["tool_source"] for r in rows),
         "repo_source_counts": collections.Counter(r["repo_source"] for r in rows)}
    json.dump(s, open(os.path.join(OUT, "stage1_stats.json"), "w"), indent=1, default=dict)
    print(json.dumps({k: v for k, v in s.items() if k != "duplicates"}, indent=1, default=dict))
    print("duplicates:", len(dups), "same_prompt:", sum(d["same_prompt"] for d in dups))

if __name__ == "__main__":
    main()
