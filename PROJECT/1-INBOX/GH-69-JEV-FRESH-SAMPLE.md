---
gh_issue: 69
source: https://github.com/HiQS-Labs/Needle-fork/issues/69
title: "GH-69: fresh 100-row two-model-consensus sample for the Jev purpose/area classifier"
status: Proposed (1-INBOX — not yet active)
created: 2026-09-19
updated: 2026-09-19
doc_type: feedback
effort: 2
complexity: 2
risk: 1
phases: 1
---

# GH-69 — fresh 100-row sample for the Jev classifier

Capture of [#69](https://github.com/HiQS-Labs/Needle-fork/issues/69); follow-up to #67. The issue
body is the canonical protocol. Branch `exp/gh69-jev-fresh-sample` exists for one concrete
parallel-writer need: the operator commits Codex's answers from another device.

## Ask

Score Jev `jev-1.13.0` zero-shot (criteria frozen at `453cae1`) on 100 unseen public
`HiQS-Labs/*` issues/PRs created on or after 2026-09-10, labelled by two independent frontier
annotators (Claude blind first with a hash commitment, then Codex Astra extra-high) with the
operator adjudicating disagreements; `uncertain` allowed and dropped from scoring.

## Files (`TESTS-RESULTS/2026-09-19-jev-fresh-sample/`)

- `quiz.jsonl` — the 100 rows (sha256 in `manifest.json`); `QUIZ.md` — the same rows with
  instructions, decision guide and answer format for a human or model annotator.
- `manifest.json` — pool counts, seed, cap, exclusions, snapshot time, quiz hash, annotator
  commitments.
- `answers/codex-astra-xh.jsonl` — committed by the operator; `answers/claude.jsonl` — added after
  Codex's file lands and must hash to the recorded commitment; `answers/consensus.jsonl` — agreed
  rows plus operator adjudications.
- Sampler: `spike/work_classification/fresh_sample.py`.

## Pre-registered gate

Purpose axis, rows with Jev confidence ≥ 0.8: accuracy ≥ 90% and coverage ≥ 60% of scored rows.
Area reported, not gating. Met → decide where to deploy first; not met → stop.

## Rating rationale (2026-09-19)

`rated 65/30/50/80` — pri 65: operator-requested follow-up gating a deployment decision; sev 30: no
defect; appeal 50 neutral; effort 80: sampler + quiz + two annotation passes, ~$0.01 API.
