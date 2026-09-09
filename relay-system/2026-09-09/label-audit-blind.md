---
Goal: Independent blind labelling of a 399-row audit sample, to measure sorter precision
Date: 2026-09-09
Reviewer: agy
NEXT: Reviewer
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

**Q2.** Which label PAIRS did you find genuinely ambiguous — where the taxonomy itself does not
cleanly separate two actions? Name the pairs, not the rows.

**Q3.** Did any row have **no** good label? If the menu has a gap, that is a taxonomy finding, and
the vocabulary was frozen as v1.0.0 today — so it matters whether the gap is real.

**Q4.** Your prediction, before scoring: what fraction of the sorter's labels do you expect to be
correct? State a number. It will be compared against the measured result, and a large miss in
either direction is itself informative.

# Definition of done

`data/audit/agy.jsonl` has 399 lines. Answer Q1-Q4 below, set `NEXT: Producer`, `STATUS: Open`,
and add a `VERDICT: PASS` line with a `Basis:` line (the harness validator requires both).

## Log

- 2026-09-09 · claude-a · Blind audit opened. Sample drawn by `utils/corpus/sample_for_audit.py`
  (seed 20260909, 399 rows, 40 strata). Sorter labels held back in `data/audit/sorter.jsonl`.
