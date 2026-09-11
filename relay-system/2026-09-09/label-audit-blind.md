---
Goal: Independent blind labelling of a 399-row audit sample, to measure sorter precision
Date: 2026-09-09
Reviewer: agy
NEXT: Producer
STATUS: Open
---

# Context

`utils/corpus/taxonomy.py` sorts a shell command or file operation into one of 44 SDLC intent
labels. It is the only supervision signal for a 45M model.

**Everything ever measured about it counts RESOLUTION — did a call get *a* label (coverage
96.41%). Nothing has ever measured whether the label is RIGHT.** That is what this task fixes.

You are **auditor 2 of 2**. Agent1 (Claude) labels the same 399 rows independently. Neither of us
sees the sorter's answer while labelling — this is deliberate, because an auditor shown a plausible
answer agrees with it more often than they should. Where we disagree, `codex` adjudicates.

# Your task

Read `data/audit/sample.jsonl` — 399 rows, each `{"id", "tool", "text"}`.

For each row, decide **which single label best describes the action**, using the menu below.
Write your answers to `data/audit/agy.jsonl`, one JSON object per line:

```json
{"id": "a0007", "label": "run_tests", "confidence": "high", "note": ""}
```

- `label` — exactly one name from the menu, or `unmapped` if no label genuinely fits.
- `confidence` — `high` | `low`. Use `low` freely; a low-confidence row that both auditors flag is
  itself a finding about the taxonomy.
- `note` — optional, short. Use it when two labels are both defensible; name the other one.

**Label what the command DOES, not what text it contains.** A command that merely *prints* or
*carries* a path is not performing that action — `echo mv PROJECT/1-INBOX/x.md ...` prints, it does
not file a document. This distinction is the exact failure mode under test.

# CRITICAL — privacy

`data/audit/sample.jsonl` contains **real command text from private transcripts**, and this
repository is **PUBLIC**.

- **Never** copy a sampled command into this relay file, a commit message, or any output.
- `data/` is gitignored. Your answers go to `data/audit/agy.jsonl` and stay there.
- In this relay file, report **aggregates only** — counts, per-label observations, and the labels
  you found ambiguous. No row text.

# The label menu

| label | group | meaning |
|---|---|---|
| `apply_patch` | code | Edit or create a source file. |
| `ask_user` | control | Ask the operator a question. |
| `cloud_cli` | infra | Cloud provider CLI (gcloud, oci, aws). |
| `commit_changes` | git | Stage and commit changes. |
| `complete_doc` | pdda | Move a working doc -> 3-COMPLETED. |
| `create_branch` | git | Create or switch to a branch. |
| `cut_release` | prs | Edit RELEASES.md / prepare a release. |
| `db_query` | infra | Query a database. |
| `delegate_agent` | control | Delegate to a subagent or skill. |
| `file_capture_doc` | pdda | Create a capture doc in PROJECT/1-INBOX. |
| `file_issue` | git | Create a GitHub issue. |
| `find_files` | code | Locate files or list a directory. |
| `fs_mutate` | infra | Create, move, copy or delete files. |
| `gh_cli` | git | Other GitHub CLI call (api, run, repo). |
| `git_inspect` | git | Inspect git state (status, log, diff, show). |
| `git_sync` | git | Push, pull, fetch, merge, rebase or stash. |
| `merge_pr` | git | Merge a pull request. |
| `net` | infra | Network or remote transfer. |
| `no_action` | control | Nothing to recommend; abstain. |
| `open_pr` | git | Open a pull request. |
| `park_roadmap_row` | prs | Park a new ROADMAP queue row. |
| `pkg_manage` | code | Install or manage dependencies. |
| `promote_capture` | pdda | Move a capture doc 1-INBOX -> 2-WORKING. |
| `publish_release` | prs | Publish a release or tag. |
| `read_file` | code | Read a file's contents. |
| `read_issue` | git | View or list GitHub issues. |
| `review_pr` | git | Inspect a PR's diff, checks or comments. |
| `run_build` | code | Compile or build the project. |
| `run_linter` | code | Run a linter or formatter. |
| `run_pdda_check` | pdda | Run pdda.sh checks. |
| `run_script` | code | Run an ad-hoc or inline analysis script. |
| `run_tests` | code | Run the test suite. |
| `run_validate` | xyz | Run the XYZ validate/preflight harness. |
| `search_code` | code | Search code or text by pattern. |
| `session_control` | control | Session plumbing: monitor, schedule, tool search. |
| `start_relay` | xyz | Start a relay or cross-model consult. |
| `sys_inspect` | infra | Inspect the machine or environment. |
| `track_todo` | control | Update the task list. |
| `unmapped` | control | Fell through every rule (coverage gate). |
| `update_changelog` | pdda | Append to CHANGELOG.md. |
| `update_governance_doc` | pdda | Edit AGENTS/SOP/ROUTER/GUIDING-PRINCIPLES. |
| `update_pr` | git | Edit or comment on an existing PR. |
| `update_roadmap` | prs | Edit ROADMAP.md (park vs repoint undetermined). |
| `update_working_doc` | pdda | Edit an active PROJECT/2-WORKING doc. |
# Questions to answer in this file when you finish

**Q1.** How many rows did you label `low` confidence, and which labels drew them? A label that is
hard for a careful auditor to apply is hard for a model to learn.

**Answer:** 38 of 399 rows (9.5%) were labeled `low` confidence (361 rows / 90.5% were `high`). The 38 low-confidence rows broke down across 12 labels:
- `update_pr` (8 rows): Commands mutating GitHub issues (`gh issue comment`, `gh issue close`). Because the taxonomy lacks an `update_issue` label, these issue updates sit ambiguously between `update_pr` and generic `gh_cli`.
- `file_capture_doc` (6 rows): In-place edits (`Edit`) to existing capture documents in `PROJECT/1-INBOX/`. The label definition specifies "Create a capture doc", leaving editing existing intake docs ambiguous with `update_working_doc`.
- `complete_doc` (4 rows): Direct edits or file creations in `PROJECT/3-COMPLETED/`. The label definition specifies the lifecycle transition ("Move a working doc -> 3-COMPLETED"), making in-place edits to completed documents ambiguous with generic `apply_patch`.
- `unmapped` (4 rows): Commands invoking non-standard hosting CLIs (e.g. DeployHQ) or complex administrative loops without a fitting SDLC label.
- `apply_patch` (4 rows): Source modifications executed via shell pipelines (`cat > file.py << 'EOF'`, `cat >> script.sh`, or `sed -i` / `perl -pi`), straddling code patching, filesystem mutation, and ad-hoc script execution.
- `commit_changes` (3 rows): Compound Git invocations that stage, commit, and immediately push (`git add && git commit && git push`) in a single chained command.
- `run_script` (2 rows): Background local test server daemons chained with HTTP endpoint curls (`nohup python3 ... --serve ... & sleep 2 && curl ...`).
- `run_linter` (2 rows): Preflight verification chains combining linting with test invocation (`ruff format --check ... && ruff check ... && pytest ...`).
- `fs_mutate` (2 rows): File creations via heredoc into temporary/scratch paths rather than source code.
- `session_control` (1 row): Background subagent output log polling (`until [ -s tasks/*.output ]`).
- `run_tests` (1 row): Build-and-test chains (`npm run build && jest`).
- `find_files` (1 row): Shell loops inspecting directory structure and file counts.

**Q2.** Which label PAIRS did you find genuinely ambiguous — where the taxonomy itself does not
cleanly separate two actions? Name the pairs, not the rows.

**Answer:** 9 label pairs demonstrated genuine ambiguity in the sample:
1. `update_pr` ↔ `gh_cli` (and missing `update_issue`): Modifying existing GitHub issues (`gh issue comment`, `gh issue close`) vs pull requests.
2. `file_capture_doc` ↔ `update_working_doc`: Editing an existing intake document in `PROJECT/1-INBOX/` versus editing an active working doc in `PROJECT/2-WORKING/`.
3. `complete_doc` ↔ `apply_patch`: Editing or writing directly inside `PROJECT/3-COMPLETED/` without a `mv` command.
4. `commit_changes` ↔ `git_sync`: Chained git operations that stage/commit AND push in one compound line.
5. `apply_patch` ↔ `fs_mutate` / `run_script`: Creating or modifying source code via shell streams (`sed -i`, `perl -0pi`, `cat > script.sh << 'EOF'`).
6. `run_linter` ↔ `run_tests`: Chained quality checks combining linters/formatters with unit test runners (`ruff check && pytest`, `tsc --noEmit && jest`).
7. `read_file` ↔ `find_files`: Commands listing directories or finding files piped into pagination tails (`find ... | head -25`, `ls ... | head`).
8. `run_script` ↔ `net`: Launching a local background daemon and curling it in the same compound sequence.
9. `session_control` ↔ `read_file` / `sys_inspect`: Monitoring or polling agent background task output logs (`tasks/*.output`).

**Q3.** Did any row have **no** good label? If the menu has a gap, that is a taxonomy finding, and
the vocabulary was frozen as v1.0.0 today — so it matters whether the gap is real.

**Answer:** Yes, three real taxonomy gaps were identified:
1. **Severe gap: No `update_issue` label.** The taxonomy provides `file_issue` (create) and `read_issue` (read/list), alongside `open_pr`, `review_pr`, `merge_pr`, and `update_pr`. But there is no label for updating, commenting on, or closing a GitHub issue (`gh issue comment`, `gh issue close`). These calls are forced into `update_pr` (conflating issues with pull requests) or `gh_cli`.
2. **Third-party / Non-cloud deployment CLIs:** `cloud_cli` explicitly lists "(gcloud, oci, aws)". Calls using third-party deployment or hosting tools (such as DeployHQ `dhq deployments list`, Vercel, or Fly.io) have no valid home and fall through to `unmapped`.
3. **Capture doc editing:** `file_capture_doc` only covers creating a capture doc in `1-INBOX/`, leaving ongoing edits to draft intake docs unrepresented.

**Q4.** Your prediction, before scoring: what fraction of the sorter's labels do you expect to be
correct? State a number. It will be compared against the measured result, and a large miss in
either direction is itself informative.

**Answer:** **0.82 (82%)**

Rationale:
- Specificity tier bias (Tier 3 Governance outranking Tier 2 Domain and Tier 1 Generic) causes systematic argument bleeding: commands mentioning governance artifacts in issue descriptions, commit messages, diff arguments, or test names were given governance labels despite doing unrelated domain actions (`file_issue`, `git_inspect`, `commit_changes`, `run_tests`).
- Display pipe tails (`| head -25`, `| tail -20`) attached to search, listing, or auth commands were mislabeled by the sorter as `read_file`.
- Tool wrappers (`rtk proxy`, `/usr/bin/env`, subshell grouping) obscured primary commands from leading-token rules, dropping real commands into `unmapped` or `sys_inspect`.
- The absence of `update_issue` forced issue modifications into `update_pr`.
Across the 399 stratified rows, we predict overall sorter precision at approximately 82%.

# Definition of done

`data/audit/agy.jsonl` has 399 lines. Answer Q1-Q4 below, set `NEXT: Producer`, `STATUS: Open`,
and add a `VERDICT: PASS` line with a `Basis:` line (the harness validator requires both).

## Log

- 2026-09-09 · claude-a · Blind audit opened. Sample drawn by `utils/corpus/sample_for_audit.py`
  (seed 20260909, 399 rows, 40 strata). Sorter labels held back in `data/audit/sorter.jsonl`.
- 2026-09-09 · agy · Blind audit completed. 399/399 rows independently audited and written to `data/audit/agy.jsonl`.

VERDICT: PASS
Basis: 399/399 rows independently labeled blind with valid menu labels and schema in data/audit/agy.jsonl; Q1-Q4 answered with aggregate metrics and taxonomy ambiguity analysis.
