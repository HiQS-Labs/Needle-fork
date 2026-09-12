---
title: Seven-model next-action panel
status: Shipped
created: 2026-09-12
updated: 2026-09-12
owner: noelsaw1
goal: Score locked model predictions against same-case baselines and obtain next-step advice.
reversibility: Easy — offline scoring and documentation only
---

# Seven-model panel — #52 completed

Authority: operator-requested panel, then scoring and Agy Gemini 3.1 Pro review;
[#52](https://github.com/HiQS-Labs/Needle-fork/issues/52), under canonical
[#1](https://github.com/HiQS-Labs/Needle-fork/issues/1).

The bet was that stronger models might reveal predictive signal missed by the
earlier classifier. Seven locked submissions scored on the same target-blind
30-example subset of #51's development partition. Fable led at 18/30 versus
phase-backoff 14/30, but the small, imbalanced, reused sample does not establish
general superiority or human usefulness. All seven missed nine cases.

The [receipt](../../TESTS-RESULTS/2026-09-12-next-action-panel/SUMMARY.md) owns
scores, provenance, replay instructions, verification and review reconciliation.
The standalone scorer reuses existing metrics and baseline fitting; runtime,
training, old gates and held PR #43 are unchanged. Raw cases and model transcripts
remain ignored locally; only aggregate results and the scorer are published.

The relay-xyz skill selected its documented one-shot consult path for next-step
advice, not an iterative artifact approval. Gemini 3.1 Pro recommended auditing
before more model calls or training. Adopted that direction, while preserving
the frozen macro-F1 convention and treating label noise as unproven.

At completion: [#53](https://github.com/HiQS-Labs/Needle-fork/issues/53) proposed a bounded
12-event source audit (nine shared misses plus three controls). Not started;
no automatic authorization for relabeling, another experiment, or deployment.

Later update: [#53 completed](PANEL-SOURCE-AUDIT.md). Two Bash classification
defects filed as #56; source alignment passed. Original panel scores unchanged.
