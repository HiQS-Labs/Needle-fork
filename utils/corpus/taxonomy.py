#!/usr/bin/env python3
"""v1 label taxonomy and labeling function for the Phase 2 Needle Oracle.

SINGLE SOURCE OF TRUTH. The extractor, the trainer, the evaluator and the
end-of-turn hook all import `label_call` and `LABELS_V1` from here. Issue #1 §1
requires one definition so executable tools and label schemas cannot drift.

WHY THIS REPLACES THE FIRST-PASS RULES
    The first extraction pass (16bce0b) matched an ordered regex list against the
    WHOLE command string, first match wins. Measured on 1,202 local Bash calls:
    97.8% of commands are compound (`cd X && A && B | C`) and 74.0% match two or
    more rules -- so for three of every four calls the label was decided by the
    rule's position in the list, not by the command. `git_mutate` was collecting
    `grep -n ...` and `sed -n 1,120p ROUTER.md`. Any per-label accuracy measured
    on those labels would score the regex list, not the model.

    The fix here is two changes, not new regexes:
      1. SEGMENT the command, drop `cd`/env preamble and display-only pipe tails,
         label each remaining segment, then resolve by an explicit SPECIFICITY
         tier (documented below) rather than by list order.
      2. Read `file_path`, not just `command`. Governance moves are Edit/Write
         calls on known paths -- 26.6% of local Edit/Write/Read calls target a
         governance doc. Discarding `file_path` makes every governance label
         undetectable, which is why the first pass found none.

DETECTABILITY IS RECORDED, NOT ASSUMED
    Each label carries a `detect` field naming the signal it needs:
      native        -- the Claude Code tool name alone is the intent
      command       -- recoverable from the Bash command string
      path          -- recoverable from a file_path
      path+content  -- needs the edit body, which the corpus does NOT carry
    A `path+content` label cannot be mined from the current transcripts. Freezing
    it as a contract entry is fine; training on it is not, until the signal exists.
"""
from __future__ import annotations
import re

LABEL_SET_VERSION = "v1.0.0-draft"

# --- Specificity tiers ---------------------------------------------------------
# When one compound command yields several segment labels, the HIGHEST tier wins;
# ties break to the earliest segment. Tiers are a design decision, stated openly:
#   3  governance -- rare, high-value, and the whole point of the Oracle
#   2  domain     -- a specific named action (run_tests, open_pr, commit_changes)
#   1  generic    -- transport-ish verbs that co-occur with everything (read_file,
#                    find_files, fs_mutate). These lose to anything more specific.
GOVERNANCE, DOMAIN, GENERIC = 3, 2, 1


def _L(group, tier, detect, description):
    return {"group": group, "tier": tier, "detect": detect, "description": description}


LABELS_V1 = {
    # --- code / dev ---
    "read_file":        _L("code", GENERIC, "native+command", "Read a file's contents."),
    "search_code":      _L("code", GENERIC, "native+command", "Search code or text by pattern."),
    "find_files":       _L("code", GENERIC, "native+command", "Locate files or list a directory."),
    "apply_patch":      _L("code", DOMAIN,  "native+path",    "Edit or create a source file."),
    "run_tests":        _L("code", DOMAIN,  "command",        "Run the test suite."),
    "run_build":        _L("code", DOMAIN,  "command",        "Compile or build the project."),
    "run_linter":       _L("code", DOMAIN,  "command",        "Run a linter or formatter."),
    "run_script":       _L("code", DOMAIN,  "command",        "Run an ad-hoc or inline analysis script."),
    "pkg_manage":       _L("code", DOMAIN,  "command",        "Install or manage dependencies."),

    # --- git / PR ---
    "git_inspect":      _L("git", GENERIC,  "command",        "Inspect git state (status, log, diff, show)."),
    "create_branch":    _L("git", DOMAIN,   "command",        "Create or switch to a branch."),
    "commit_changes":   _L("git", DOMAIN,   "command",        "Stage and commit changes."),
    "git_sync":         _L("git", DOMAIN,   "command",        "Push, pull, fetch, merge, rebase or stash."),
    "open_pr":          _L("git", DOMAIN,   "command",        "Open a pull request."),
    "update_pr":        _L("git", DOMAIN,   "command",        "Edit or comment on an existing PR."),
    "review_pr":        _L("git", DOMAIN,   "command",        "Inspect a PR's diff, checks or comments."),
    "merge_pr":         _L("git", DOMAIN,   "command",        "Merge a pull request."),
    "file_issue":       _L("git", DOMAIN,   "command",        "Create a GitHub issue."),
    "read_issue":       _L("git", DOMAIN,   "command",        "View or list GitHub issues."),
    "gh_cli":           _L("git", GENERIC,  "command",        "Other GitHub CLI call (api, run, repo)."),

    # --- PDDA (doc lifecycle) ---
    "file_capture_doc":     _L("pdda", GOVERNANCE, "path",         "Create a capture doc in PROJECT/1-INBOX."),
    "promote_capture":      _L("pdda", GOVERNANCE, "command",      "Move a capture doc 1-INBOX -> 2-WORKING."),
    "complete_doc":         _L("pdda", GOVERNANCE, "command",      "Move a working doc -> 3-COMPLETED."),
    "update_working_doc":   _L("pdda", GOVERNANCE, "path",         "Edit an active PROJECT/2-WORKING doc."),
    "run_pdda_check":       _L("pdda", GOVERNANCE, "command",      "Run pdda.sh checks."),
    "update_changelog":     _L("pdda", GOVERNANCE, "path",         "Append to CHANGELOG.md."),
    "update_governance_doc":_L("pdda", GOVERNANCE, "path",         "Edit AGENTS/SOP/ROUTER/GUIDING-PRINCIPLES."),

    # --- PRS (release ledger) ---
    "park_roadmap_row":     _L("prs", GOVERNANCE, "command",      "Park a new ROADMAP queue row."),
    "update_roadmap":       _L("prs", GOVERNANCE, "path",         "Edit ROADMAP.md (park vs repoint undetermined)."),
    "cut_release":          _L("prs", GOVERNANCE, "path",         "Edit RELEASES.md / prepare a release."),
    "publish_release":      _L("prs", GOVERNANCE, "command",      "Publish a release or tag."),

    # --- XYZ (harness) ---
    "run_validate":     _L("xyz", GOVERNANCE, "command",  "Run the XYZ validate/preflight harness."),
    "start_relay":      _L("xyz", GOVERNANCE, "command",  "Start a relay or cross-model consult."),

    # --- infra ---
    "sys_inspect":      _L("infra", GENERIC, "command", "Inspect the machine or environment."),
    "net":              _L("infra", DOMAIN,  "command", "Network or remote transfer."),
    "db_query":         _L("infra", DOMAIN,  "command", "Query a database."),
    "fs_mutate":        _L("infra", GENERIC, "command", "Create, move, copy or delete files."),
    "cloud_cli":        _L("infra", DOMAIN,  "command", "Cloud provider CLI (gcloud, oci, aws)."),

    # --- control ---
    "delegate_agent":   _L("control", DOMAIN, "native", "Delegate to a subagent or skill."),
    "track_todo":       _L("control", DOMAIN, "native", "Update the task list."),
    "ask_user":         _L("control", DOMAIN, "native", "Ask the operator a question."),
    "session_control":  _L("control", GENERIC, "native", "Session plumbing: monitor, schedule, tool search."),
    "no_action":        _L("control", DOMAIN, "none",   "Nothing to recommend; abstain."),
    "unmapped":         _L("control", GENERIC, "none",  "Fell through every rule (coverage gate)."),
}

# --- Native Claude Code tool -> label ------------------------------------------
NATIVE = {
    "Read": "read_file", "Grep": "search_code", "Glob": "find_files",
    "Edit": "apply_patch", "Write": "apply_patch", "NotebookEdit": "apply_patch",
    "TodoWrite": "track_todo", "AskUserQuestion": "ask_user",
    "Agent": "delegate_agent", "Task": "delegate_agent", "Skill": "delegate_agent",
    "WebFetch": "net", "WebSearch": "net",
    "Monitor": "session_control", "ToolSearch": "session_control",
    "ListAgents": "session_control", "ScheduleWakeup": "session_control",
    "TaskStop": "session_control", "TaskOutput": "session_control",
    "SendMessage": "session_control", "ExitPlanMode": "session_control",
}

# --- MCP tool name -> label ----------------------------------------------------
# MCP servers expose intent directly in the tool name (`mcp__github__issue_read`),
# so they need no command parsing. Matched by longest prefix.
MCP_RULES = [
    ("mcp__github__issue_write", "file_issue"),
    ("mcp__github__issue_read", "read_issue"),
    ("mcp__github__search_issues", "read_issue"),
    ("mcp__github__list_issues", "read_issue"),
    ("mcp__github__pull_request_read", "review_pr"),
    ("mcp__github__pull_request_write", "update_pr"),
    ("mcp__github__get_commit", "git_inspect"),
    ("mcp__github__list_commits", "git_inspect"),
    ("mcp__github__get_file_contents", "read_file"),
    ("mcp__github__search_code", "search_code"),
    ("mcp__github__merge_pull_request", "merge_pr"),
    ("mcp__github__create_pull_request", "open_pr"),
    ("mcp__github__", "gh_cli"),
    ("mcp__", "session_control"),
]

# --- file_path -> governance label (checked BEFORE the native map) -------------
PATH_RULES = [
    ("update_changelog",      re.compile(r"(^|/)CHANGELOG\.md$", re.I)),
    ("update_roadmap",        re.compile(r"(^|/)ROADMAP\.md$", re.I)),
    ("cut_release",           re.compile(r"(^|/)RELEASES\.md$", re.I)),
    ("file_capture_doc",      re.compile(r"PROJECT/1-INBOX/")),
    ("update_working_doc",    re.compile(r"PROJECT/2-WORKING/")),
    ("complete_doc",          re.compile(r"PROJECT/3-COMPLETED/")),
    ("update_governance_doc", re.compile(r"(^|/)(AGENTS|SOP|ROUTER|GUIDING-PRINCIPLES|CLAUDE|PDDA)\.md$", re.I)),
]

# --- Bash segment -> label. Evaluated per SEGMENT; ties resolved by tier. -------
# Ordering inside a tier still matters, so the specific forms are listed first.
BASH_RULES = [
    # governance -- these must be tested before the generic verbs they contain
    ("promote_capture",  r"\bmv\b.*PROJECT/1-INBOX/.*PROJECT/2-WORKING/"),
    ("complete_doc",     r"\bmv\b.*PROJECT/(1-INBOX|2-WORKING)/.*PROJECT/3-COMPLETED/"),
    ("run_pdda_check",   r"(^|[\s/])pdda[a-z-]*\.sh\b"),
    ("run_validate",     r"(^|[\s/])(validate\.sh|preflight\.sh|ci-local\.sh)\b|\bxyz\s+(validate|preflight)\b"),
    ("start_relay",      r"(^|[\s/])(relay-drive|codex-turn|agy-turn|poll)\.sh\b"),
    ("park_roadmap_row", r"\breleases_app\.py\s+roadmap\s+add\b"),
    ("publish_release",  r"\b(gh\s+release\s+create|git\s+tag\s+-a)\b"),

    # git / PR -- specific before generic
    ("file_issue",       r"\bgh\s+issue\s+create\b"),
    ("read_issue",       r"\bgh\s+issue\s+(view|list)\b"),
    ("open_pr",          r"\bgh\s+pr\s+create\b"),
    ("merge_pr",         r"\bgh\s+pr\s+merge\b"),
    ("review_pr",        r"\bgh\s+pr\s+(view|diff|checks|list|status)\b"),
    ("update_pr",        r"\bgh\s+(pr\s+(edit|comment|review|ready)|issue\s+(comment|edit|close))\b"),
    ("create_branch",    r"\bgit\s+(-C\s+\S+\s+)?(checkout\s+-b|switch\s+-c|branch\s+[^-])"),
    ("commit_changes",   r"\bgit\s+(-C\s+\S+\s+)?(commit|add)\b"),
    ("git_sync",         r"\bgit\s+(-C\s+\S+\s+)?(push|pull|fetch|merge(?!-tree|-base)|rebase|stash|clone|worktree|cherry-pick|reset)\b"),
    ("git_inspect",      r"\bgit\s+(-C\s+\S+\s+)?(status|log|diff|show|remote|rev-parse|rev-list|describe|blame|check-ignore|ls-files|merge-tree|merge-base|config|branch\b)"),

    # code / dev
    ("run_tests",        r"\b(pytest|jest|vitest|go test|cargo test|npm (run )?test|make test|run-tests)\b"),
    ("run_linter",       r"\b(ruff|flake8|eslint|black|prettier|mypy|shellcheck|golangci-lint)\b"),
    ("run_build",        r"\b(make|cmake|cargo build|go build|npm run build|xcodebuild|clang|gcc|tsc)\b"),
    ("pkg_manage",       r"\b(pip3?\s+install|npm\s+(install|ci)|yarn\s+add|brew\s+(install|upgrade)|uv\s+(pip|add)|poetry\s+(add|install)|apt(-get)?\s+install|gem\s+install)\b"),
    ("run_script",       r"(<<\s*'?[A-Z_]+'?|\bpython3?\s+-[cm]\b|/bin/python\b"
                         r"|\b(python3?|node|npx|bash|sh|zsh|ruby|perl|swift|deno|tsx)\s+\S+"
                         r"|^\./\S+|^\$[A-Za-z_])"),

    ("gh_cli",           r"\bgh\s+\w+"),

    # infra
    ("cloud_cli",        r"\b(gcloud|oci|aws|az)\s+"),
    ("db_query",         r"\b(sqlite3|psql|mysql|bq)\b"),
    ("net",              r"\b(curl|wget|ping|ssh|scp|rsync)\b"),
    ("sys_inspect",      r"\b(ps|top|uptime|sysctl|df|du|whoami|which|uname|sw_vers|scutil|env|pkill|pgrep|lsof|sleep|true|false|cmp|tar|jq)\b|\bcommand\s+-v\b"),

    # generic
    ("search_code",      r"\b(rg|grep|ag|ack)\b"),
    ("read_file",        r"\b(cat|head|tail|less|bat|sed\s+-n|awk)\b"),
    ("find_files",       r"\b(find|fd|ls|tree)\b"),
    ("fs_mutate",        r"\b(mkdir|rm|mv|cp|touch|chmod|ln)\b"),
]
BASH_RE = [(n, re.compile(p)) for n, p in BASH_RULES]

# Programs that consume the REST of their segment as data, not as intent.
# `grep -E "pdda|release" file` is a search that MENTIONS governance, not a
# governance move -- and because governance outranks search on tier, letting the
# rules read those arguments would hand the highest-value labels their loudest
# false positives. So a segment led by one of these IS that program's label, full
# stop, and its arguments are never inspected.
#
# (The first pass's leading-program table was junk because `cd "/path" && ...`
# made `cd` the leading program 77.6% of the time. Preamble segments are dropped
# before this runs, so the leading program is now the real one.)
ARG_CONSUMERS = {
    "grep": "search_code", "rg": "search_code", "ag": "search_code", "ack": "search_code",
    "cat": "read_file", "head": "read_file", "tail": "read_file", "less": "read_file",
    "more": "read_file", "bat": "read_file", "awk": "read_file", "wc": "read_file",
    "find": "find_files", "fd": "find_files", "ls": "find_files", "tree": "find_files",
    "sed": "read_file",
}
_LEAD = re.compile(r"^\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*([^\s;|&]+)")


def leading_program(seg: str) -> str:
    m = _LEAD.match(seg)
    return m.group(1).strip("\"'").rsplit("/", 1)[-1] if m else ""


# Segments that are setup or display, never the intent of the call.
_PREAMBLE = re.compile(
    r"^\s*(cd\b|export\b|source\b|\.\s|set\b|nohup\b|time\b|nice\b|sudo\b|timeout\s+\d+\b"
    r"|for\b|while\b|do\b|done\b|if\b|then\b|fi\b|else\b|case\b|esac\b|function\b"
    r"|continue\b|break\b|return\b|exit\b|\[|\(|\\\\$|test\s"
    r"|[A-Za-z_][A-Za-z0-9_]*=)")
_DISPLAY = re.compile(r"^\s*(echo|printf|head|tail|wc|sort|uniq|column|less|more|tee|jq|cut|tr|xargs\s+echo)\b")
_HEREDOC = re.compile(r"<<-?\s*'?[A-Za-z_][A-Za-z0-9_]*'?")


def split_segments(cmd: str) -> list[str]:
    """Split a shell command into candidate action segments.

    A heredoc body is NOT split: `python3 - <<'PY' ... PY` is one action, and its
    body is Python, not shell. Splitting it produced the `bash_other` pile-up in
    the first pass.
    """
    if _HEREDOC.search(cmd):
        return [cmd[: _HEREDOC.search(cmd).end()]]
    parts, buf, quote, i = [], [], None, 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif cmd.startswith("&&", i) or cmd.startswith("||", i):
            parts.append("".join(buf)); buf = []; i += 1
        elif ch in ";|\n":
            parts.append("".join(buf)); buf = []
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def substantive_segments(cmd: str) -> list[str]:
    """Drop `cd`/env preamble and display-only pipe tails."""
    segs = split_segments(cmd)
    keep = [s for s in segs if not _PREAMBLE.match(s) and not _DISPLAY.match(s)]
    return keep or [s for s in segs if not _PREAMBLE.match(s)] or segs


def label_segment(seg: str) -> str | None:
    """Label one segment, or None if no rule matches."""
    lead = leading_program(seg)
    if lead in ARG_CONSUMERS:
        # `sed -i` rewrites a file; `sed -n 1,20p` reads one.
        if lead == "sed":
            return "apply_patch" if re.search(r"\s-i\b", seg) else "read_file"
        return ARG_CONSUMERS[lead]
    for name, rx in BASH_RE:
        if rx.search(seg):
            return name
    return None


def label_bash(cmd: str) -> tuple[str, str]:
    """Label a Bash command. Returns (label, evidence_segment)."""
    best = None  # (tier, -order, label, segment)
    for order, seg in enumerate(substantive_segments(cmd)):
        name = label_segment(seg)
        if name is None:
            continue
        cand = (LABELS_V1[name]["tier"], -order, name, seg)
        if best is None or cand > best:
            best = cand
    if best is None:
        return "unmapped", ""
    return best[2], best[3][:120]


def label_call(tool: str, tool_input: dict | None) -> tuple[str, str]:
    """Label one Claude Code tool_use record. Returns (label, evidence)."""
    inp = tool_input or {}
    if tool == "Bash":
        return label_bash(inp.get("command") or "")
    if tool.startswith("mcp__"):
        for prefix, label in MCP_RULES:
            if tool.startswith(prefix):
                return label, tool
    path = inp.get("file_path") or inp.get("notebook_path") or ""
    if path:
        for name, rx in PATH_RULES:
            if rx.search(path):
                # Reading a governance doc is still a read, not a governance move.
                if tool == "Read":
                    return "read_file", path
                return name, path
    if tool in NATIVE:
        return NATIVE[tool], path or tool
    return "unmapped", tool


def coverage(labels) -> float:
    """§2 gate: fraction of calls that resolved to a real intent label."""
    labels = list(labels)
    if not labels:
        return 0.0
    return 1.0 - (labels.count("unmapped") / len(labels))
