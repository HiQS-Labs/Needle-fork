---
title: Codex feedback connection recon
status: planning
created: 2026-09-13
updated: 2026-09-13
owner: Codex
goal: Trace the smallest app feedback connection before implementing it
gh_issue: 63
roadmap_exempt: true
---

## Status

| What was just completed | What's next |
|---|---|
| Source and hook-contract trace on main ded9ef7; no implementation. | App-visible connection proof in [the plan](CODEX-NEEDLE-FEEDBACK.md). |

## Recon map

Existing training rows → `spike/coding_core/baselines.py:fit` → transition
counts → `spike/coding_core/shortlist_eval.py:ranked` → three category IDs.
The existing predictor needs nonempty history; an explicit global-prior fallback
is needed for a conversation with no usable action. No model weights are needed.
Use only Markov counts, not the phase arm; preserve existing scoring functions.

Codex hook event → session/turn identity and transcript prefix → action mapping
→ ranked choices → app display → next user prompt → separate feedback event.
The last four seams are NOT implemented. `utils/corpus/codex_transcript_adapter.py`
normalizes user messages and tool CALLS; it does not join completion results and
cannot establish that an action succeeded. Reuse its parsing/mapping concepts,
not an assertion that every call completed. Nested code-mode calls and outstanding
shell sessions need explicit coverage or an unknown/fallback state.

Private writer → `relay-system/.needle-feedback.jsonl` (proposed hidden direct
child of the existing transcript root). Separate from public review transcripts.
`relay-system/` is tracked; only `.log` files currently have a blanket ignore.
Implementation must add a narrow ignore BEFORE writing. The inspected
`.xyz/utils/collect-relay-system.sh` copies `relay-system/*`, including ignored
ordinary subfolders, but excludes hidden direct children under normal Bash glob
settings. Test this actual collection path with synthetic data; Git ignore alone
is insufficient. Other backups/sync tools may still copy hidden files.
`.xyz/utils/py/rtl.py:_rtl_transcript_root` can redirect through `XYZ_ARCHIVE_ROOT`
to a Git archive: do not inherit that redirect for private feedback. Pin this
repo-local private path; no cross-repo archive writes. Existing recent public QA
folder: `relay-system/2026-09-10/`; new QA may use the same root with today's date.

## Evidence ledger and unknowns

- Read current #1 latest comment and closed #62: no existing personal usefulness
  claim. New #63 is a separately requested interaction study, not a gate reversal.
- Installed CLI reports `hooks stable true`; this is NOT evidence about this app's
  display behavior or its embedded runtime version.
- [Official hook contract](https://learn.chatgpt.com/docs/hooks), checked 2026-09-13:
  `Stop` accepts JSON; `systemMessage` is surfaced as a UI/event-stream warning.
  `decision:block` instead creates an automatic continuation prompt. Avoid that
  continuation path for this feature. App rendering remains unverified.
- `UserPromptSubmit` supplies prompt/session/turn data and can add context; it
  does not document replacing the user's prompt. Treat metadata separately rather
  than promising an invisible input rewrite.
- Hook trust is required, definitions are hash-trusted, and matching hooks run
  concurrently. Do not bypass trust or change existing hooks.
- No app-hook smoke test, feedback records, training export or runtime install
  occurred during recon. Failure checks are planned, not observed passing.

## Boundaries and rollback

Additive app integration only: no training/export/quantization/runtime SDK changes,
no release configuration changes, no old receipts or CSV rewrites. A small hook
dispatcher plus focused tests and project-local config is the intended boundary.
Disabling its hook definitions must restore normal turns without deleting records.
Privacy exposure is costly to undo: keep raw records local and never publish them.
