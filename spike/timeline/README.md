# Timeline dataset pipeline (prototype)

Offline research code for HiQS-Labs/XYZ-forge#709. It builds a per-session **timeline dataset** from
an operator's local agent history, used for work-purpose classification (Arm A) and stage/next-action
prediction (Arm B). It is not part of the installed `needle` runtime.

It joins three sources:

1. **The CLIO prompt log.** A markdown log of every user prompt, with session id, UTC timestamp,
   project heading, machine, branch and tool.
2. **Local agent transcripts, matched by session id.**
   - Claude Code: `~/.claude/projects/*/<id>.jsonl`
   - Codex: `~/.codex/sessions/**/rollout-*-<id>.jsonl`
   - agy / Antigravity: `~/.gemini/antigravity/{conversations/<id>.db,brain/<id>/}`
3. **GitHub metadata** for linked issues/PRs, fetched **read-only** with `gh api -X GET`.

Weak labels are **rule-based only. No LLM generates any label.** Every label records its `source`
and a heuristic `confidence` (rule confidence × link confidence); confidences are not calibrated.

Everything is stdlib Python 3.10+. The pipeline is read-only on every source: sqlite is opened with
`mode=ro&immutable=1`, and GitHub is only ever sent GET requests.

## Privacy: outputs must never be committed

Outputs contain raw prompts, transcript excerpts, and titles/paths from **private client repos**.

- `out/` and `*.jsonl` are gitignored here.
- `resolve_out()` refuses to write inside a git checkout unless the target is ignored.
- Keep generated data in the operator's private synced storage (a private Dropbox folder, the
  `needle-timeline/` folder, with its own README) until a sanitization pass has been reviewed.

## Configuration

Every flag falls back to its environment variable, then to a default:

| Flag | Env var | Default |
|---|---|---|
| `--clio-log` | `NEEDLE_TL_CLIO_LOG` | *(required)* |
| `--out` | `NEEDLE_TL_OUT` | `spike/timeline/out/` (gitignored) |
| `--claude-dir` | `NEEDLE_TL_CLAUDE_DIR` | `~/.claude/projects` |
| `--codex-dir` | `NEEDLE_TL_CODEX_DIR` | `~/.codex/sessions` |
| `--agy-dir` | `NEEDLE_TL_AGY_DIR` | `~/.gemini/antigravity` |

## Run

```sh
cd spike/timeline
export NEEDLE_TL_CLIO_LOG="/path/to/prompt-log.md"
export NEEDLE_TL_OUT="/path/to/private/needle-timeline/out"   # outside any repo

python3 build_sessions.py        # stage 1 -> sessions.jsonl, link_candidates.json, stage1_stats.json
python3 select_subset.py 50      # stage 2a -> gh_request.json (prototype subset, <=10 per repo)
python3 fetch_github.py "$NEEDLE_TL_OUT/gh_request.json" "$NEEDLE_TL_OUT/gh_meta.json"   # stage 2b, resumable
python3 build_episodes.py        # stage 3 -> episodes.jsonl (+ _stats.json)
python3 build_episodes.py --all  # stage 3 over every session -> episodes_all.jsonl
```

Tests use synthetic data only: `pytest -q tests/test_timeline_pipeline.py`.

## What each stage does

- **`build_sessions.py`**
  - Parses the CLIO log and ignores the repeated `# Agent Prompt Log` / `CLIO:ENTRIES` headers left
    by concatenated files.
  - Reads the meta line as follows: 3 parts = machine · branch · tool; 2 parts = machine · tool if
    the tool is known, otherwise machine · branch.
  - Drops duplicate `(session_id, ts)` entries (keeping the first), counts file-order inversions,
    sorts each session by UTC timestamp, and groups entries into sessions.
  - Condenses assistant replies to text (300 chars) plus tool name and command/path (160 chars).
  - Resolves the repo from the transcript's git remote, falling back to the majority URL repo under
    the same project heading.
  - Extracts link candidates. Confidence depends on the source:

    | Source | Confidence |
    |---|---|
    | Claude `pr-link` record | 0.9 |
    | `gh-N` branch | 0.8 |
    | GitHub URL | 0.7 |
    | `GH-N` mention | 0.5 |
    | `#N` mention | 0.3 |

- **`select_subset.py`** picks sessions with a strong link, preferring ones with a transcript and
  at least 3 prompts.
- **`fetch_github.py`** fetches title, state, state_reason and labels; for PRs it adds merged,
  base/head, changed file paths and commit subjects.
- **`build_episodes.py`** builds the episode records and their weak labels:
  - **purpose**: conventional-commit prefixes in titles and commit subjects, plus a label map,
    combined by weighted vote into the Arm A taxonomy: bug_fix, feature_enhancement,
    research_evaluation, planning_design, documentation, maintenance, testing_validation,
    merge_closeout. Dissenting votes are recorded.
  - **area**: majority vote over path rules for changed files (ci_cd, skills, tests,
    evaluation_results, documentation, ui, config_tooling, scripts_tooling, core_code).
  - **completion**: merged, closed_completed, closed_not_completed or open.
  - **stage_sequence** for Arm B: investigate_plan, implement, test, commit_push, review, pr,
    merge, new_task, from prompt keyword rules and tool/command rules, with consecutive repeats
    collapsed.

## Output record (`episodes*.jsonl`)

`session_id, project, repo, repo_source, start_ts, end_ts, machines, tool, tool_source, branches,
transcript, github_enriched, opening_prompt, user_prompts[], closing_prompts[], n_replies,
replies_condensed[], link_candidates[], linked[] (GitHub metadata + link_sources/link_confidence),
weak_labels{purpose, area, completion, stage_sequence, stage_ordering}`

## Known limits (prototype)

- **One session is not one task.** Long sessions mix tasks and repos, so they need segmenting
  before labelling.
- **`#N` / `GH-N` mentions resolve against the session's repo.** They can point to the wrong repo;
  one case returned a 404.
- **agy is partial.** Only tool calls are decoded (protobuf `steps`, step_type 132) plus the names of
  its brain artifacts. The assistant's prose is not decoded, and steps have no timestamps, so their
  stages are listed after the prompts (`prompts_then_unaligned_tools`).
- **zcode (`sess_` ids) is not joined yet.** See `utils/corpus/zcode_transcript_adapter.py`.
- **Some Codex `exec` calls have no extracted command.** Their JS-wrapper shapes aren't parsed yet.
- **The area rules over-assign documentation.** Doc-heavy repos push `.md` files to the top.
