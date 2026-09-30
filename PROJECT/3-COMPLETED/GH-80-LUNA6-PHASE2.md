---
title: GPT 6 Luna frozen Phase 2 replication
status: Completed
created: 2026-09-29
updated: 2026-09-29
owner: Codex and operator
goal: Compare GPT 6 Luna Medium with historical GPT 5.6 Luna on the unchanged 12-case Git/PR analyst packet
gh_issue: 80
source: https://github.com/HiQS-Labs/Needle-fork/issues/80
doc_type: research
effort: 2
complexity: 2
risk: 1
phases: 1
---

# GPT 6 Luna Phase 2 replication

## Status

| What was just completed | What's next |
|---|---|
| Two frozen GPT 6 Luna Medium calls completed; final 43/41, grade B, below historical 44/43. Evidence and review reconciled. | Revised 2026-09-29: operator authorized Sonnet 5.5 and Luna High follow-up in [#81](https://github.com/HiQS-Labs/Needle-fork/issues/81); this remains the completed Medium baseline. |

## Execution and acceptance

See [frozen protocol](../../TESTS-RESULTS/2026-09-29-gh80-luna6-phase2/PROTOCOL.md). Complete two fresh Medium calls, preserve raw receipts and unchanged prompt bytes, reconcile per-case scores under the original rubric, and publish results on #80 with a pointer from #13. A negative result completes the experiment. No product/runtime change.

## Findings

[Results and receipts](../../TESTS-RESULTS/2026-09-29-gh80-luna6-phase2/SUMMARY.md): 87.50% versus historical 90.625%, both B. Verdicts 12/12 and 10/12; no critical false all-clear or observed tool action. Generic classifier summaries and inconsistent deployment uncertainty offset better preservation and one improved CI verdict. Candidate prompt bytes match the original; minimal-checkout context and CLI drift prevent a model-only causal claim.

## Verification

545 non-slow tests passed, 7 skipped, 11 deselected. Original grader positive/six negative controls pass; frozen hashes, nonempty answers, raw/parsed equality, distinct threads and zero tool events verified. Independent anonymized reviewer plus coordinator adjudication retained per case, including disagreement. No production source changed.

## Lessons Learned (For Future Agents)

- Reusing exact prompt bytes does not reproduce ambient CLI/project instructions; record candidate checkout and runtime identity.
- Preserve semantic-equivalence calibration and per-case disagreements. A stricter reviewer can change the letter without a change in candidate output.
- Keep G05's original verdict for comparability and publish its sensitivity separately. Do not infer failed CI or absent external deployment from missing records.
- Missing test dependencies were resolved in an isolated environment using declared extras; no source fixes were needed.
