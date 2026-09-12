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

LABEL_SET_VERSION = "v1.0.0"

# --- DECISION RECORD: the support floor is a SUPPLEMENTATION gate --------------
# Adjudicated 2026-09-07 against GUIDING-PRINCIPLES.md, AGENTS.md and SOP.md.
# Recorded here because this is where someone is tempted to act on it. The same
# record is in PROJECT/3-COMPLETED/PHASE-2-LABEL-TAXONOMY.md, CHANGELOG.md, and
# oracle/labels-v1.json; SOP.md §4 has the process that produced it.
#
# A label below SUPPORT_FLOOR_RATE is FLAGGED FOR SUPPLEMENTATION (issue #1 §3b
# governance-doc synthesis, §3c git/PR-history mining). It is NEVER deleted or
# merged on the strength of the floor alone.
#
# Why not a delete gate:
#   - The floor is a threshold we chose, not a measured property. Letting an
#     invented number silently delete semantically distinct labels is exactly the
#     "check that reports confidence it never earned" AGENTS.md §6 warns about.
#   - "One source of truth per concept" (GUIDING-PRINCIPLES, DRY) is about
#     duplication, not rarity. `pkg_manage` (mutate/inspect the dependency
#     environment) and `run_script` (run something ad hoc) are two concepts.
#     Collapsing them destroys meaning without removing any duplication.
#   - Reversibility is asymmetric (AGENTS.md §3). Keeping a label is Easy to undo
#     -- collapse labels with a dict at dataset-build time, downstream of this
#     file and of the published contract. Merging is Costly to undo: it needs a
#     re-extraction over a network share that is not always mounted.
#   - Consolidation for TRAINING is legitimate; it belongs at the dataloader as a
#     projection, never at the canonical taxonomy root.
#
# The case that set the rule: `pkg_manage` was measured at 60 calls, under the
# 74-call floor, and was about to be merged into `run_script`. Both figures were
# artifacts of bugs in THIS file -- `uv add ruff` scored as `run_linter` (a
# package NAME read as an invocation) and dependency inspection (`pip list`,
# `brew list`) had been tightened out of `pkg_manage` into `unmapped`. Fixing
# them took the count to 111, above the floor, and the decision dissolved.
# Fix the measurement before adjudicating anything the measurement drives.
SUPPORT_FLOOR_RATE = 0.001  # 0.1% of calls
SUPPORT_FLOOR_ACTION = "supplement"  # never "delete" -- see the decision record

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
    ("file_issue",       r"\bgh\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*issue\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*create\b"),
    ("read_issue",       r"\bgh\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*issue\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*(view|list)\b"),
    ("open_pr",          r"\bgh\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*pr\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*create\b"),
    ("merge_pr",         r"\bgh\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*pr\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*merge\b"),
    ("review_pr",        r"\bgh\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*pr\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*(view|diff|checks|list|status)\b"),
    ("update_pr",        r"\bgh\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*(pr\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*(edit|comment|review|ready)|issue\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+)*(comment|edit|close))\b"),
    ("create_branch",    r"\bgit\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+|-C\s+\S+\s+|-c\s+\S+\s+)*(checkout\s+-b|switch\s+-c|branch\s+[^-])"),
    ("commit_changes",   r"\bgit\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+|-C\s+\S+\s+|-c\s+\S+\s+)*(commit|add)\b"),
    ("git_sync",         r"\bgit\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+|-C\s+\S+\s+|-c\s+\S+\s+)*(push|pull|fetch|merge(?!-tree|-base)|rebase|stash|clone|worktree|cherry-pick|reset|checkout|switch|restore)\b"),
    ("git_inspect",      r"\bgit\s+(?:-{1,2}[\w-]+(?:=\S+)?\s+|-C\s+\S+\s+|-c\s+\S+\s+)*(status|log|diff|show|remote|rev-parse|rev-list|describe|blame|check-ignore|ls-files|merge-tree|merge-base|config|bisect|branch\b)"),

    # code / dev
    # `make test` must survive global flags the same way the git rules do:
    # `make -C /repo test` was scoring run_build because the tokens are not adjacent.
    ("run_tests",        r"\b(pytest|jest|vitest|go test|cargo(?:\s+(?:-{1,2}[\w-]+(?:=\S+)?|\"\"))*\s+test|npm (run )?test|run-tests)\b"
                         r"|\bmake(?:\s+-\S+(?:\s+\S+)?)*\s+test\b"
                         r"|\b(?:bash|sh|zsh|ksh|dash)\s+(?:\S*/)?test/\S+\.sh\b"),
    ("run_linter",       r"\b(ruff|flake8|eslint|black|prettier|mypy|shellcheck|golangci-lint)\b"),
    ("run_build",        r"\b(make|cmake|cargo build|go build|npm run build|xcodebuild|clang|gcc|tsc)\b"),
    ("pkg_manage",       r"\b(pip3?|uv|poetry|pipx|conda)\s+(install|add|remove|uninstall|sync|list|show|freeze)\b"
                         r"|\b(npm|yarn|pnpm)\s+(install|ci|add|remove|uninstall|ls|list|outdated)\b"
                         r"|\b(brew|apt|apt-get|gem)\s+(install|upgrade|uninstall|remove|list|info)\b"
                         r"|\b(pip3?|uv|poetry)\s+install\s+-r\b"),
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
    # `which`/`command -v`/`type` report where a program LIVES; their arguments are
    # program names being asked about, and they map to a real label, so they belong.
    # `stat`/`realpath`/`shasum`/`basename`/`dirname` were also added here and that
    # was wrong: ARG_CONSUMERS is checked BEFORE command_region, so the class-level
    # control never exercised the positional default it claimed to test. Removed, so
    # the control is real (agy, PR #16 review).
    "which": "sys_inspect", "command": "sys_inspect", "type": "sys_inspect",
    "whereis": "sys_inspect",
}
_LEAD = re.compile(r"""^\s*(?:[A-Za-z_][A-Za-z0-9_]*=(?:"[^"]*"|'[^']*'|\S)*\s+)*([^\s;|&]+)""")

# ---------------------------------------------------------------------------
# #2: a rule token in an ARGUMENT position is not an invocation.
#
# The first two instances of this bug class were each fixed with a list of
# specific programs. The class is broader than any list, because the defect is
# not "these programs take data" -- it is that a bare-name rule was allowed to
# match ANYWHERE in a segment. `chmod +x validate.sh` is not a governance run;
# `echo pytest` is not a test run; `tar -czf b.tgz validate.sh` is neither.
#
# So the default is inverted: a bare-name rule matches only in COMMAND POSITION.
# Everything after the command is data unless the program is known to take
# subcommands. That makes the fix positional rather than a fourth enumeration --
# a program nobody listed, like `stat` or `realpath`, is handled by the default.
# ---------------------------------------------------------------------------

# Wrappers whose intent is their CHILD. Unwrapped before anything else looks at
# the segment, so the effective command is what gets labelled.
_WRAPPERS = re.compile(
    r"^\s*(?:"
    # A flag may be long, short, or `=`-joined. `-\w+` alone left every `--long-flag`
    # attached to the child, dropping the command to unmapped (agy, PR #16 review).
    r"timeout\s+[\d.]+[smhd]?|nohup"
    r"|nice(?:\s+-n\s+-?\d+|\s+-{1,2}[\w-]+(?:=\S+)?)*"
    # `sudo -u <user>` takes a SEPARATE argument; a generic `flag + next token` rule
    # would eat the command itself, exactly as it did for xargs.
    r"|sudo(?:\s+-u\s+\S+|\s+-{1,2}[\w-]+(?:=\S+)?)*"
    r"|watch(?:\s+-n\s+[\d.]+|\s+-{1,2}[\w-]+(?:=\S+)?)*"
    r"|stdbuf(?:\s+-{1,2}[\w-]+(?:=\S+)?)*"
    # xargs: only a NUMBER or a `{}` placeholder is consumed as a flag argument --
    # anything else could be the command.
    r"|xargs(?:\s+-\S+(?:\s+(?:\d+|\{\}))?)*"
    r"|env(?:\s+-[iu]\s+\S+|\s+-{1,2}[\w-]+|\s+[A-Za-z_][A-Za-z0-9_]*=\S*)*"
    r"|(?:uv|poetry|pdm|hatch|pipenv|rye)\s+run|git\s+bisect\s+run"
    r"|(?:\S*/)?time(?:\s+-{1,2}[\w-]+(?:=\S+)?)*"
    r"|do|then|else|until|while|!"
    r")\s+")
# `python -m pip install X` IS package management, and `python -m pytest` IS a test
# run: `-m` names the real program. Without this the region stops at `pip` and the
# rule needing `pip install` never sees the subcommand. Anything else run this way
# is still a script, so the fallback keeps that.
# The lead is often unresolvable: a shell variable holding an interpreter path
# (`"$P" -m pytest`) is extremely common here, and requiring a literal `python`
# dropped real test runs to unmapped. Key on the `-m` SHAPE instead.
_DASH_M = re.compile(r"""^\s*(?:\S*python[\d.]*|["']?\$\{?\w+\}?["']?|\S*/\S+)\s+-m\s+""")
# `git bisect run <probe>` is still a git operation even though its probe is not.
_WRAPPER_FALLBACK = ((re.compile(r"^\s*git\s+bisect\b"), "git_inspect"),)

# Programs whose next tokens are SUBCOMMANDS, not data. Everything not listed
# here is assumed to take operands -- the safe default, and the one that makes
# an unlisted program behave correctly without being added.
SUBCOMMAND_PROGRAMS = {"git", "gh", "npm", "yarn", "pnpm", "pip", "pip3", "pipx",
                       "uv", "poetry", "brew", "apt", "apt-get", "gem", "conda",
                       "cargo", "go", "docker", "podman", "xyz", "aws", "gcloud",
                       "az", "oci", "make", "kubectl", "systemctl",
                       # Unlisted runners degrade to `unmapped`, never to a WRONG
                       # label -- the safe direction, but these are common enough.
                       "bundle", "just", "tox", "nox", "rake", "pipenv", "task"}
# Container images are `name:tag`, which reads as a bare tool name; one token is
# all the subcommand ever is.
_SUBCOMMAND_DEPTH = {"docker": 1, "podman": 1, "make": 1}
# For these the next token is the SCRIPT being run, so it is in command position:
# `bash scripts/validate.sh` really is a governance run.
EXECUTORS = {"bash", "sh", "zsh", "ksh", "dash", "source", ".",
             "python", "python3", "node", "npx", "ruby", "perl", "swift",
             "deno", "tsx", "osascript"}
# Rules that read OPERANDS rather than only the command position: a directory move,
# or a specific command sequence.
#
# Blanking quoted text for them was too blunt in BOTH directions (agent2, #309930):
# it did nothing about UNQUOTED display data (`echo mv PROJECT/1-INBOX/a ...` still
# scored promote_capture) and it destroyed the operands of a REAL move written with
# quoted paths. The rule is not "quoted text is data"; it is:
#
#   establish the command's ROLE first, then read its operands with values intact.
#
# So each of these carries a gate naming the invocation it describes. The gate is
# tested per clause, because a heredoc keeps `mkdir ... && git mv ...` in one segment.
ANY_POSITION = {"promote_capture", "complete_doc", "park_roadmap_row"}


def _is_move(clause: str) -> bool:
    lead = leading_program(clause)
    if lead == "mv":
        return True
    if lead != "git":
        return False
    # `_second_token` took token 2 literally, so ANY global flag broke the gate
    # and demoted a real governance move to fs_mutate (`git -C /repo mv ...`).
    # command_region already resolves the subcommand past flags and their args.
    return "mv" in command_region(clause).split()[1:]


def _is_roadmap_tool(clause: str) -> bool:
    return "releases_app.py" in command_region(clause)


# Gate per operand-reading rule: does this clause actually INVOKE the thing?
ANY_POSITION_GATE = {"promote_capture": _is_move, "complete_doc": _is_move,
                     "park_roadmap_row": _is_roadmap_tool}


_CLAUSE_SEP = re.compile(r"&&|\|\||;")


def _split_outside_quotes(seg: str) -> list[str]:
    """Split on `&&`/`||`/`;` that are NOT inside a quoted string.

    A plain `re.split` here was the 4th instance of the operand/invocation bug
    class (GH-17): a separator inside a quoted string forged a clause whose
    leading program was `mv`, so a COMMIT MESSAGE scored `promote_capture`.
    It also cut a real move whose path contained a `;`.
    """
    parts, buf, i, quote = [], [], 0, None
    while i < len(seg):
        ch = seg[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(seg):      # keep an escaped char whole
                buf.append(seg[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'":
            quote, i = ch, i + 1
            buf.append(ch)
            continue
        m = _CLAUSE_SEP.match(seg, i)
        if m:
            parts.append("".join(buf))
            buf, i = [], m.end()
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def _operand_clauses(seg: str):
    """Clauses of a segment, with quote CHARACTERS removed but values preserved.

    A real move may quote its paths (`mv "PROJECT/1-INBOX/a.md" ...`); blanking the
    content lost the very operands the rule exists to read. Splitting is
    quote-aware -- see `_split_outside_quotes`.
    """
    for clause in _split_outside_quotes(seg):
        clause = clause.strip()
        if clause:
            yield clause, clause.replace('"', "").replace("'", "")
_HEREDOC_BODY = re.compile(r"<<-?\s*'?[A-Za-z_]")
_REDIRECT = re.compile(r"\s*\d?(?:>>|>|<)\s*\S+")
# `cat > file <<EOF` WRITES a file -- the redirection is the whole action, and
# stripping it leaves a bare `cat`, which reads as the opposite. Only for commands
# that emit content and do nothing else: `pytest > out.txt` is still a test run.
_CONTENT_PRODUCERS = {"cat", "echo", "printf", "tee"}
# STDOUT only. `\d?` also matched `cat f 2>/dev/null`, turning 34 ordinary reads
# into writes -- stderr redirection says nothing about where content goes.
# Any `/dev/*` target is a DISCARD, not a write: `echo x > /dev/null` was scoring
# apply_patch. `\d?` also matched `2>/dev/null`, fixed earlier.
_WRITE_REDIRECT = re.compile(r"(?:^|\s)1?>>?\s*(?!/dev/)\S+")
# Quote-aware tokenisation, so a quoted operand survives as ONE token.
_TOKEN = re.compile(r"""(?:[^\s'"]+|'[^']*'|"[^"]*")+""")
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
_FILEISH = re.compile(r"/|\.[A-Za-z][A-Za-z0-9]{0,4}$")
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Named so a mutation control can DISABLE it. A control that only asserts a
# table's contents shows the table, not that the guard is why a test passes
# (agy, GH-17) -- every internal mechanism here must be switchable off.
_END_OF_OPTIONS = "--"
# Short flags that take a SEPARATE argument, per program. Assuming EVERY short
# flag did so swallowed the subcommand: `git -p diff` -> unmapped (GH-17).
# The default is BOOLEAN -- the conservative direction, since a boolean flag
# wrongly consuming its successor hides a real command, while an arg-taking
# flag wrongly kept only exposes a value the rules would have to match anyway.
_SHORT_TAKES_ARG = {
    "git":    {"-C", "-c"},
    "make":   {"-C", "-f", "-j"},          # -j only when numeric, see _NUMERIC_ARG
    "gh":     {"-R"},
    "npm":    {"-C", "-w"},
    "pnpm":   {"-C", "-w"},
    "yarn":   {"-C"},
    "docker": {"-f"},
    "podman": {"-f"},
    "uv":     {"-C"},
    "cargo":  {"-Z"},
}
# A token directly after a flag, before any subcommand is found, is that flag's
# VALUE when it LOOKS like one -- a path, or `key=value`. Recognising the shape
# needs no table, so an unlisted option cannot truncate the walk:
# `git --exec-path /tmp/validate.sh status` used to score unmapped (codex).
# Blanking rather than breaking is the safe direction either way: the value can
# never be read as an invocation, and the walk continues to the real subcommand.
_VALUE_SHAPED = re.compile(r"/|=|\.[A-Za-z][A-Za-z0-9]{0,4}$")
# Flags whose argument is PROSE. Unquoted, it was read as command text:
# `git tag -m ruff v1` scored run_linter -- the bug class, via a message.
_PROSE_FLAGS = {"-m", "--message", "-t", "--title", "--body", "-F", "--file"}
# A branch NAME legitimately contains `/`. _FILEISH read it as an operand and
# truncated `git branch feat/x` to `git branch`, which the rule no longer matches.
_BRANCH_SUBCOMMANDS = {"branch", "checkout", "switch"}
# Flags whose argument is OPTIONAL and numeric: `make -j 4 test` passes 4, but
# `make -j test` runs the target `test`. Consuming unconditionally lost it.
_NUMERIC_ARG = {"-j"}


def _effective_clause(seg: str) -> str:
    """Drop leading setup clauses (`cd X &&`) from a HEREDOC-joined segment.

    Only heredoc segments: `split_segments` has already cut every other segment on
    `&&`/`;`, so a separator still present in one of those is inside quotes, and
    splitting on it again mislabels 123 local commands.
    """
    if not _HEREDOC.search(seg):
        return seg
    for clause in re.split(r"&&|;", seg):
        clause = clause.strip()
        if clause and not _PREAMBLE.match(clause) and not _DISPLAY.match(clause):
            return _unwrap(clause)[0]
    return seg


def _unwrap(seg: str) -> tuple[str, str | None]:
    """Strip wrapper prefixes until the effective command is exposed."""
    fallback = None
    for _ in range(6):                       # bounded: wrappers do not nest deeply
        for rx, label in _WRAPPER_FALLBACK:
            if rx.match(seg):
                fallback = label
        m = _DASH_M.match(seg)
        if m:
            seg, fallback = seg[m.end():], "run_script"
            continue
        m = _WRAPPERS.match(seg)
        if not m:
            break
        seg = seg[m.end():]
    return seg, fallback


_INLINE_CODE_FLAGS = {"-c", "-e", "--command", "--eval", "-E"}


def _tee_target(lead: str, seg: str) -> bool:
    """`tee file` names its destination as an OPERAND, not through a redirection.

    Without this `tee` sat in _CONTENT_PRODUCERS doing nothing at all.
    """
    if lead != "tee":
        return False
    return any(not t.startswith("-") and not t.startswith("/dev/")
               for t in seg.split()[1:])


def _is_quoted(tok: str) -> bool:
    return len(tok) > 1 and tok[0] == tok[-1] and tok[0] in "\"'"


def command_region(seg: str) -> str:
    """The part of a segment a bare-name rule is allowed to match.

    Tokenised QUOTE-AWARE, and a quoted token is emptied unless it sits in command
    position. Blanking quotes BEFORE tokenising destroyed the operand outright, so
    `bash "scripts/validate.sh"` lost its governance label and `"$P" -m pytest`
    stopped being a test run (agy, PR #16 review).
    """
    seg = _REDIRECT.sub("", seg)
    tokens = [t for t in _TOKEN.findall(seg) if t]
    # `leading_program` skips `KEY=val` prefixes; this must agree with it, or
    # tokens[0] is the ASSIGNMENT and every such call falls to unmapped --
    # `CI=1 ./validate.sh`, `PYTHONPATH=. pytest` (GH-17).
    while tokens and _ENV_ASSIGN.match(tokens[0]):
        tokens.pop(0)
    if not tokens:
        return ""

    def text(tok, keep=False):
        if not _is_quoted(tok):
            return tok
        return tok[1:-1] if keep else '""'

    lead = leading_program(seg)
    if lead in EXECUTORS:
        # lead plus the script it runs. A flag's ARGUMENT is not the script, so
        # `bash -o errexit scripts/validate.sh` must not stop at `errexit`.
        out, prev_flag, inline = [text(tokens[0], keep=True)], False, False
        for tok in tokens[1:]:
            if tok.startswith("-"):
                out.append(tok)
                # `-c`/`-e` introduce inline CODE, not a script path, so what
                # follows is data: `python3 -c "print('ruff')"` is not a linter run.
                inline = tok in _INLINE_CODE_FLAGS
                prev_flag = not tok.startswith("--") and "=" not in tok
                continue
            if inline:
                # `-c`/`-e` bodies are CODE. text(tok, keep=False) returned an
                # UNQUOTED token intact, so `python3 -c print(ruff)` scored
                # run_linter. Nothing after inline code is an invocation.
                out.append('""')
                break
            out.append(text(tok, keep=True))
            if not prev_flag:
                break
            prev_flag = False
        return " ".join(out)
    if lead not in SUBCOMMAND_PROGRAMS:
        return text(tokens[0], keep=True)
    depth, out, seen, prev_flag, was_flag = _SUBCOMMAND_DEPTH.get(lead, 3), [tokens[0]], 0, "", False
    short_args = _SHORT_TAKES_ARG.get(lead, frozenset())
    for tok in tokens[1:]:
        if tok == _END_OF_OPTIONS:
            # END OF OPTIONS: everything after it is an operand by definition.
            # Treating `--` as an ordinary flag set prev_flag and so skipped the
            # _FILEISH break, leaving `git diff -- validate.sh` scoring run_validate
            # -- the exact defect #2 exists to remove.
            break
        if tok.startswith("-"):
            # `--flag=value` carries its own argument, and the value is where a path
            # like `--output=/tmp/validate.sh` hides. Keep the flag, drop the value.
            flag = tok.split("=", 1)[0]
            out.append(flag)
            # Whether a flag takes a SEPARATE argument is a property of the flag,
            # not of its dash count. Assuming every short flag did swallowed the
            # subcommand (`git -p diff` -> unmapped); assuming no long flag did
            # left its path operand to hit _FILEISH and truncate the walk
            # (`cargo --manifest-path /p/Cargo.toml test`). Both are GH-17.
            # prev_flag holds the FLAG, not a bool, so a conditional consumer
            # like `-j` can inspect it when its argument arrives.
            if "=" in tok:
                prev_flag = ""
            elif flag in _PROSE_FLAGS:
                prev_flag = flag
            elif tok.startswith("--"):
                prev_flag = ""          # decided by SHAPE at the next token
            else:
                prev_flag = flag if flag in short_args else ""
            was_flag = True
            continue
        if prev_flag:
            if prev_flag in _NUMERIC_ARG and not tok.isdigit():
                # An optional numeric argument that is not a number: this token
                # is the subcommand, not the flag's value.
                prev_flag = ""
            else:
                pass
        if prev_flag:
            # A flag's argument (`git -C /repo status`) is DATA, not command text:
            # emitted as an empty placeholder so the `-C <arg>` shape the git rules
            # match on survives while the value cannot be read as an invocation.
            # Keeping the value let `git -C /tmp/validate.sh status` score
            # run_validate (agent2, AgentChorus #309930). It also must not consume
            # subcommand depth -- that truncated `make -C /repo test` before `test`.
            out.append('""')
            prev_flag = ""
            continue
        if was_flag and seen < depth and _VALUE_SHAPED.search(tok):
            # An unlisted option's value: DATA. DROPPED rather than blanked --
            # `git --exec-path <path> status` must read as `git --exec-path
            # status`, which the rules' flag prefix already matches, and they
            # have no alternative for a bare `""` placeholder here.
            was_flag = False
            continue
        was_flag = False
        if _FILEISH.search(tok):
            if out and out[-1] in _BRANCH_SUBCOMMANDS:
                # A branch NAME may contain `/`. Emitted as a placeholder so the
                # `branch <name>` SHAPE the rule matches survives while the name
                # itself stays unreadable as an invocation (GH-17).
                out.append('""')
            break                       # an operand: `make validate.sh`
        out.append(text(tok))
        seen += 1
        if seen >= depth:
            break
    return " ".join(out)

# Package managers take PACKAGE NAMES as arguments, so their arguments must not be
# read as invocations -- `uv add ruff` is installing ruff, not running it, and was
# being labelled run_linter. Same class of error as ARG_CONSUMERS above.
#
# They are also runners (`uv run pytest`, `poetry run pytest`), so the delegating
# subcommands fall through to the normal rules instead.
PKG_MANAGERS = {"pip", "pip3", "pipx", "brew", "apt", "apt-get", "gem", "poetry",
                "uv", "conda", "cargo-install"}
PKG_DELEGATES = {"run", "exec", "tool"}
# npm/yarn/pnpm delegate constantly (`npm run build`), so only their own
# dependency subcommands count as package management.
NODE_PKG = {"npm", "yarn", "pnpm"}
NODE_PKG_SUBCOMMANDS = {"install", "i", "ci", "add", "remove", "uninstall", "rm",
                        "ls", "list", "outdated", "update", "upgrade", "link", "prune"}


def _second_token(seg: str) -> str:
    parts = seg.split()
    return parts[1].strip("\"'") if len(parts) > 1 else ""


def _subcommand(seg: str) -> str:
    """The first real subcommand, past global flags and their arguments.

    `_second_token` reads token 2 literally, so any flag hid the subcommand:
    `uv --directory /p run pytest` looked like package management rather than a
    delegated test run (GH-17). command_region has already resolved the flags.
    """
    for tok in command_region(seg).split()[1:]:
        if tok.startswith("-") or tok == '""':
            continue
        return tok.strip("\"'")
    return ""


def leading_program(seg: str) -> str:
    m = _LEAD.match(seg)
    return m.group(1).strip("\"'").rsplit("/", 1)[-1] if m else ""


# Segments that are setup or display, never the intent of the call.
_PREAMBLE = re.compile(
    r"^\s*(cd\b|export\b|source\b|\.\s|set\b|nohup\b|time\b|nice\b|sudo\b|timeout\s+\d+\b"
    r"|for\b|while\b|until\b|do\b|done\b|if\b|then\b|fi\b|else\b|case\b|esac\b|function\b"
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
    """Label one segment, or None if no rule matches.

    Order matters: the wrapper is unwrapped first so every later test sees the
    EFFECTIVE command, and path-shaped governance rules run before the name-based
    ones so `mv PROJECT/1-INBOX/x PROJECT/2-WORKING/x` stays a promotion.
    """
    seg, fallback = _unwrap(seg)
    # A heredoc suppresses segment splitting, so `cd X && git commit -F - <<EOF`
    # arrives here whole and its leading token is `cd`. While rules matched
    # anywhere that did not matter; now the leading token decides, so the setup
    # clause has to come off or every heredoc commit reads as a script run.
    full = seg                 # path-shaped rules must still see the whole segment
    seg = _effective_clause(seg)
    lead = leading_program(seg)
    if lead in PKG_MANAGERS and _subcommand(seg) not in PKG_DELEGATES:
        return "pkg_manage"
    if lead in NODE_PKG and _subcommand(seg) in NODE_PKG_SUBCOMMANDS:
        return "pkg_manage"
    if lead in _CONTENT_PRODUCERS and (_WRITE_REDIRECT.search(seg) or _tee_target(lead, seg)):
        return "apply_patch"
    if lead in ARG_CONSUMERS:
        # `sed -i` rewrites a file; `sed -n 1,20p` reads one.
        if lead == "sed":
            return "apply_patch" if re.search(r"\s-i\b", seg) else "read_file"
        return ARG_CONSUMERS[lead]
    region = command_region(seg)
    if lead in {"pytest", "unittest"} and leading_program(region) == lead:
        # GH-56: classify the effective runner, never mentions in scripts/data.
        # Only unambiguous metadata-only invocations are inspection. Do not scan
        # arbitrary option values (`pytest -k "--version"`) for metadata flags.
        tokens = _TOKEN.findall(_REDIRECT.sub("", seg))
        while tokens and _ENV_ASSIGN.match(tokens[0]):
            tokens.pop(0)
        args = [t[1:-1] if _is_quoted(t) else t for t in tokens[1:]]
        if lead == "unittest" and args[:1] == ["discover"]:
            args = args[1:]
        metadata = {"-h", "--help"} | ({"-V", "--version"} if lead == "pytest" else set())
        if (set(args) & metadata
                and set(args) <= metadata | {"-q", "--quiet", "-v", "--verbose"}):
            return "sys_inspect"
        if lead == "unittest":
            return "run_tests"
    # ONE ordered pass, so the original rule precedence is preserved exactly; only
    # the HAYSTACK changes per rule. Splitting this into two passes silently
    # promoted every heredoc above `commit_changes`, turning 44 real commits in the
    # local corpus into `run_script` -- a regression no unit test caught, found only
    # by diffing a re-extraction.
    for name, rx in BASH_RE:
        if name in ANY_POSITION:
            # Per CLAUSE of the whole segment, because a heredoc keeps
            # `mkdir -p PROJECT/3-COMPLETED && git mv PROJECT/2-WORKING/x ...` in one
            # piece. A clause counts only when it actually invokes the operation --
            # otherwise `echo mv PROJECT/1-INBOX/a ...` is a promotion, quoted or not.
            gate = ANY_POSITION_GATE[name]
            if any(gate(clause) and rx.search(unquoted)
                   for clause, unquoted in _operand_clauses(full)):
                return name
            continue
        if rx.search(region):
            return name
    # A heredoc means script content is being fed in -- but only once nothing else
    # matched. Testing it INSIDE the ordered pass made every rule after run_script
    # unreachable, so `sqlite3 db <<EOF` scored run_script instead of db_query
    # (agy, PR #16 review).
    if _HEREDOC_BODY.search(full):
        return "run_script"
    return fallback


def label_bash(cmd: str) -> tuple[str, str]:
    """Label a Bash command. Returns (label, evidence_segment)."""
    raw_segments = split_segments(cmd)
    segments = substantive_segments(cmd)
    # ZCode commonly emits waiting and the subsequent status read as one call.
    # A bare sleep remains machine inspection; the compound shape controls a session.
    for index, seg in enumerate(raw_segments[:-1]):
        if leading_program(seg) != "sleep":
            continue
        # Waiting can refine an otherwise unlabeled prefix, but it must not erase
        # a substantive action that already happened in this command.
        if any(label_segment(item) is not None for item in raw_segments[:index]):
            continue
        tail = raw_segments[index + 1:]
        labels = [label_segment(item) for item in tail]
        allowed = {"read_file", "search_code", "sys_inspect"}
        if (any(label in allowed for label in labels)
                and all(label in allowed or leading_program(item) in {"echo", "printf"}
                        for item, label in zip(tail, labels))):
            return "session_control", cmd[:120]
    best = None  # (tier, -order, label, segment)
    for order, seg in enumerate(segments):
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
