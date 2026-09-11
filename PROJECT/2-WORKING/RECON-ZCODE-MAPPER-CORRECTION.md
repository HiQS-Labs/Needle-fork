---
title: "Recon Map — ZCode mapper correction"
status: In progress
created: 2026-09-11
updated: 2026-09-11
owner: noelsaw1
goal: Track mapper correction evidence and remaining source qualification before training admission.
---

# Recon Map — ZCode mapper correction

## Status

| What was just completed | What's next |
|---|---|
| The scoped mapper correction landed in PR #40. This map records the pre-change trace. | Issue #37 still requires a new blind qualification sample before ZCode training admission. |

Commit: `eca144b` · Mode: grep + direct read · Lanes: mapper, campaign, build

## Subject and change class

Narrow cross-source corrections to the frozen `v1.0.0` action mapper. The label vocabulary does
not change; ZCode remains excluded from training until a new blind sample passes.

## The seams

| Seam | Location | Crosses | Breaks if |
| --- | --- | --- | --- |
| ZCode normalization | `utils/corpus/zcode_transcript_adapter.py` | native ZCode events to normalized actions | source fields or order are guessed |
| Blind sampling | `utils/corpus/sample_agent_label_audit.py` | normalized actions to private review rows | old development rows are reused as fresh evidence |
| Shared mapper | `utils/corpus/taxonomy.py:182` and `:193` | Claude and normalized cross-agent actions to 44 labels | a ZCode rule changes established Claude behavior broadly |
| Mapper entry point | `utils/corpus/taxonomy.py:807` | tool name/input to label and evidence | free-text descriptions become unreviewed label authority |
| Regression contract | `tests/test_taxonomy.py` | mapper behavior to CI | positive fixes lack negative controls |

## Call paths in

`zcode_transcript_adapter.py` -> `normalized_transcript.py` ->
`sample_agent_label_audit.py` -> `taxonomy.label_call()` -> `taxonomy.label_bash()`.

## State

The frozen 200-row ZCode audit is private development evidence. Aggregate score: 131/200 agreement;
69 errors, including 67 Bash calls and 2 Edit calls. The largest narrow error clusters are shell
test entrypoints, long-poll commands, and edits to completed documents.
Only mapper source and regression tests are written in this round.

## Contracts

- `LABELS_V1` and `oracle/labels-v1.json` remain unchanged.
- Claude's mapper and training/evaluation contract remain unchanged except where the new exact
  command shapes apply.
- The old ZCode audit cannot be reported as fresh post-change evaluation evidence.
- A new blind sample is required before ZCode can be reconsidered for training.

## Build, failure, and rollback today

Focused taxonomy tests and the full non-slow suite cover the shared mapper. Each new rule requires
a witnessed failing test plus a negative control. Rollback is deletion of the narrow rules/tests;
reversibility is Easy.

## Unknowns

| Unknown | Why it matters | What would settle it |
| --- | --- | --- |
| Post-change ZCode population agreement | Determines whether ZCode advances | Freeze and independently label a new sample |
| Effect on the full qualified Claude corpus | Shared mapper could shift established counts | Re-extract and diff aggregate label counts before merge |

## Current-state radius

The shared mapper affects Claude extraction, training serialization, evaluation, hooks, and every
cross-agent audit; the model architecture, checkpoint format, and native engine are untouched.
