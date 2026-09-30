---
title: Sonnet 5.5 and Luna High Phase 2 follow-up
status: Completed
created: 2026-09-29
updated: 2026-09-29
owner: Codex and operator
goal: Compare Sonnet 5.5 Medium and GPT 6 Luna High on frozen Phase 2 and record full-roster pricing
gh_issue: 81
source: https://github.com/HiQS-Labs/Needle-fork/issues/81
doc_type: research
effort: 2
complexity: 2
risk: 1
phases: 1
---

# Phase 2 follow-up

## Status

| What was just completed | What's next |
|---|---|
| Luna High 44/43 (90.625%, B); Sonnet Medium 44/40 (87.50%, B); full-roster pricing and adjudicated evidence recorded. | Retain fixture evidence; no model promotion or further inference authorized by these scores. |

## Execution and acceptance

Canonical issue [#81](https://github.com/HiQS-Labs/Needle-fork/issues/81), predecessors #80 and #13. Two calls each using the unchanged 12-case packet; capture exact prompts, raw output, usage, time and original grading. No quality retry or repaired answers. See [protocol](../../TESTS-RESULTS/2026-09-29-gh81-phase2/PROTOCOL.md) and [pricing](../../TESTS-RESULTS/2026-09-29-gh81-phase2/PRICING.md). Negative results complete the experiment. No runtime/product changes; Easy reversibility, append corrections. Clean clone preserves unrelated operator commits.

## Verification

545 passed, 7 skipped, 11 deselected before inference; original positive/six negative grader controls passed. Four distinct sessions, 48 nonempty assessments, frozen hash equality, exact raw/parsed equality and zero candidate tool events verified. Claude exposes two built-in plugins (agents-md, telemetry) despite settings isolation; native system context is not identical across vendors. No claim of backend attestation or actual billing.

## Findings

[Full results](../../TESTS-RESULTS/2026-09-29-gh81-phase2/SUMMARY.md). High improves 3.125pp over Luna Medium and ties historical GPT 5.6 Luna on total score. Sonnet ties Luna Medium in mean and varies more across runs. All B under historically calibrated final scoring. Independent literal-key reviewer was stricter; every disagreement is preserved. G05 sensitivity keeps the improvement over Medium, but historical Luna then leads High slightly.

## Lessons learned

Keep semantic grading calibrated across versions; a stricter new judge can masquerade as a model regression. Preserve both raw judge and adjudication. Separate time-limited rates (Gemini 3.7, Zen's Muse offer) from permanent cuts (Sonnet) and standing contractual discounts (Meta Contributor). Same explicit prompt does not equal identical native harness context or billable token counts.
