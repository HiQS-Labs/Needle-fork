---
title: Manual on-demand suggestion usefulness test
status: In progress
created: 2026-09-12
updated: 2026-09-12
owner: noelsaw1
goal: Learn whether a frozen action suggestion is useful at voluntary request moments without building a product.
---

# Manual usefulness test — #49

## Status

| What was just completed | What's next |
|---|---|
| Protocol scoped; no interface or training work needed. No trial ratings collected. | First voluntary real-work request and operator usefulness rating. |

Authority: [#49](https://github.com/HiQS-Labs/Needle-fork/issues/49), under
[#1](https://github.com/HiQS-Labs/Needle-fork/issues/1). The operator asked to proceed after discussing
a cheap manual test. This is a product-discovery exception, **not a pass for #48**. Its two benchmark
gates remain failed. PR #43 remains held. Reversibility: Easy; stop the manual exercise, no service
or runtime changes to undo.

## Scope and evidence

Reuse #48's `spike/coding_core/baselines.py`: `load_private_splits` -> `fit` -> `predict`.
The ordinary prediction uses only an observed prior-action prefix; the six-action projection is
unchanged and control actions clear history. Predictor code at `082ca3a` is the frozen reference;
later input-validation hardening does not change its fit/predict logic. This is a non-code plan;
the relevant functions have been read, and no new serving path or feature is proposed.

The private benchmark scored 45.73% overall versus 43.52% repeat-last, but ordinary change-row
accuracy was 14.06%. Neither score measures usefulness. The test below asks a different question
on a voluntarily selected sample; it cannot repair or confirm the previous benchmark.

## Procedure

1. Start only when the operator explicitly requests a trial (for example, “trial: what next?”)
   during real coding work. Record the current task and up to twelve **already observed** canonical
   actions privately. Use the existing projection. If the prefix is unavailable, ambiguous or empty
   after a control boundary, ask for it or log a skip; never manufacture context or inspect a future
   action to decide whether a request is eligible. No automatic prompts or background monitoring.
2. Reconstruct the unchanged count tables only from the original verified training partition if
   they are not already available. Compare the source hash to the retained trusted private receipt,
   check the frozen counts, and use the identical overlap filter. This is deterministic reconstruction
   of the previous model, not learning from trial feedback, new training data or parameter search.
   Do not run holdout evaluation again or use its outcomes to choose a suggestion.
3. Compare ordinary `phase_backoff` with the fixed `repeat_last` rule on that same prefix.
   **Never exclude the previous action** or assume a future switch. Render both as “Next action:
   read / search / edit / run_tests / run_command / git.” Do not elaborate one into an LLM-authored
   recommendation or executable command. If different, show A/B with source hidden and alternate
   order by eligible trial number. If identical, show once and record a tie. This is not a blinded
   randomized efficacy study; the facilitator knows the sources.
4. Ask the operator to rate each distinct suggestion `useful now` or `not useful now`, optionally
   choose A / B / neither, and give a short reason. Judge assistance, not whether the action was
   later taken. Tied suggestions receive one rating credited equally. Missing feedback is missing,
   not acceptance. The operator remains in control; no suggested actions execute automatically.
5. Keep one private manual log under ignored `data/`: trial number, UTC timestamp, task/prefix,
   source-to-display assignment, displayed labels, ratings, tie/skip status and optional reason.
   Do not publish context, session IDs, timestamps or row-level ratings. A local log is sufficient;
   no UI, hook, telemetry, model artifact publishing or collector is part of this test.
6. End at ten eligible requests or five working days after the first request, whichever comes first;
   stop immediately on operator request or privacy/discomfort concern. Report total requests,
   eligible/rated/skipped/missing counts, ties, and usefulness/preference counts with denominators.
   No significance, general acceptance-rate or deployment claim. Continue only if the operator
   identifies a concrete helpful use and explicitly authorizes another bounded step; otherwise park.

## QA and stop conditions

- [x] Scope uses existing ordinary predictor and repeat-last; no new code or numerical gate.
- [x] Real trigger, private record shape, missing-data handling and stopping boundary are explicit.
- [ ] Before the first trial, verify input identity and that no prediction sees future actions;
  missing prefix or mismatched manifest must stop/skip rather than emit a fabricated comparison.
- [x] Before collecting ratings, verify one tie and one differing-label display using clearly
  marked synthetic practice examples; these are not user trials and do not enter the totals.
- [ ] At closeout, reconcile private log totals and report the operator decision on #49/#1.

Use debug-mantra if a protocol check fails. Do not change features, baselines or presentation based
on a disappointing first rating; record limitations and stop instead of turning this into tuning.
An empty log, synthetic practice, or the assistant's own ratings cannot establish user usefulness.

Synthetic practice verified against #48's existing test fixture: prefix `read` gives a shared `read`
suggestion; prefix `edit, read` gives phase `run_tests` versus repeat-last `read`. One display for a
tie, equal-format A/B otherwise, no fabricated rating. These are fixture outputs, not private results.
