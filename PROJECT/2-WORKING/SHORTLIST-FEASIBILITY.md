---
title: Top-three shortlist feasibility and prototype decision
status: In Progress
created: 2026-09-12
updated: 2026-09-12
owner: noelsaw1
goal: Decide whether a tiny shortlist prototype merits further effort without another model campaign.
gh_issue: 62
reversibility: Easy — additive offline scope, no runtime or original-score changes
---

# Top-three shortlist — authorized bounded round

Authority: [#62](https://github.com/HiQS-Labs/Needle-fork/issues/62), under
[#1](https://github.com/HiQS-Labs/Needle-fork/issues/1). Operator initially authorized
scope and consult only; now authorized the recommended offline round. No prototype
build. Start 2026-09-13 02:35:25 UTC; absolute stop 03:35:25 UTC (one hour).

## Status

| What was just completed | What's next |
|---|---|
| Trusted inputs verified; additive evaluator and 17 focused tests pass, five in-memory test mutations witnessed red/green. | Freeze and commit implementation before one locked prediction/score run. |

## Table of contents

- [Decision and boundaries](#decision-and-boundaries)
- [Proposed single round](#proposed-single-round)
- [QA and stopping rule](#qa-and-stopping-rule)
- [Consult](#consult)

## Decision and boundaries

The original ambition is useful top-three next steps. Exact next-action attempts
have not qualified: [#48](../../TESTS-RESULTS/2026-09-11-private-transitions/SUMMARY.md)
failed both gates; [#59](../../TESTS-RESULTS/2026-09-12-context-refresh/ROUND2.md)
scored richer context 52.5% versus 60% simple baselines on 40 cases. Engineering
and diagnostic progress is real; useful personal recommendations remain unproven.

Bet: existing history counters might yield a better three-label shortlist than
cheap controls, even without better exact predictions. Failure mode: selecting
half of a six-label universe produces an impressive but uninformative hit rate.
This is a new, exploratory endpoint on reused development data, NOT a revised
gate for #48/#51/#59, fresh confirmation, governance coverage or human acceptance.
Even a pass would justify only considering a separately scoped interaction test.

One CPU-only, stdlib round, at most one engineer-hour including checks; scoring
timeout 600 seconds, bounded inputs and 1 GiB RSS tripwire (not a hard macOS cap).
No new downloads, model/API calls, neural training, dependencies, source re-extraction,
taxonomy changes, manual CSV work, UI, hooks, server, execution suggestions or PR #43
changes. Inputs read-only; new ignored output directory; sanitized aggregates only.
No model-fitting search: reuse fixed count fitting once. See [Recon Map](recon-shortlist.md).

## Proposed single round

1. [x] Verify retained #59 paired train/holdout against the committed
   [manifest](../../TESTS-RESULTS/2026-09-12-context-refresh/manifest.json), not a
   newly generated expected digest. Use all 10,000 training rows / 224 issues and
   all 1,722 development rows / 40 issues, NOT only the 40-case model quiz.
   Read q2 issue/history/target; task/observation are unused. Check nonempty rows,
   all six labels, history/target schema, issue disjointness, exact row identity,
   paired-view alignment and unchanged membership. Git support is only 33 rows.
   These 40 issues were already used in #59: call them reused development data.
2. [x] Add one offline evaluator plus focused tests, importing `baselines.fit`,
   `phase_keys`, `MIN_CONTEXT_SUPPORT`; do not change `baselines.predict` or old
   evaluators. Candidate: choose the first fine/coarse counter with support >=2,
   else last-action transition counter, else global training targets. Rank observed
   labels by descending counter count, descending global count, lexical label;
   fill to exactly three distinct labels using global rank, skipping duplicates.
   Never exclude the previous action or consult whether a switch actually happened.
   Rank one must match ordinary `phase_backoff` prediction for every scored row.
3. [ ] On identical rows, score static global-frequency top three, Markov top three
   with the same ranking/fill rule, and repeat-last followed by global-frequency
   fill. No fitted cutoff or abstention. A deterministic history-permutation null
   uses seed `shortlist-v1` to SHA-sort row indices and cyclically assign another
   row's history without moving targets; report changed-history coverage. This
   is a history-association diagnostic, not a causal claim or promotion control.
4. [ ] Freeze outputs before reading scores. Primary metric: issue-macro hit@3
   (mean of each issue's hit fraction); also pooled hit@1/hit@3, six-label recall@3
   and its unweighted mean, ordinary action-change slice, and paired issue
   wins/ties/losses against each control. No conditional future-switch exclusions.
   Keep per-issue details private; publish aggregate counts and each control.

## QA and stopping rule

Proposed engineering go/no-go heuristic, fixed before any scores: candidate must
beat the strongest of the three unshuffled controls by >=5 absolute points on
issue-macro hit@3, with no decrease in six-label macro recall@3 against that
same control (choose the higher macro recall control on a primary-score tie).
Also require strictly more issue wins than losses against that control; ties
do not count as wins. This additional restraint was adopted from the pre-score consult.
Report every per-label regression; no claim of significance, superiority on new
issues, or product usefulness. A result dominated by regressions requires review,
not automatic prototype approval. Passing means only reconsidering a tiny demo.
Fail -> park this count-based shortlist; no threshold, label or phase-key tuning.
Invalid data or guard/test failure -> no score and no product conclusion.

Before scoring, witness rejecting tests for empty data, wrong digest/counts,
cross-split issue identity, duplicate/unknown shortlist labels, same-size target
substitution and score arithmetic tampering. Prove target/future-field edits
cannot change predictions, deterministic ties/fallbacks, rank-one parity, and
issue-macro arithmetic on an intentionally uneven synthetic fixture. The test
mutation must fail before trusting the check. These controls are PLANNED, not
claimed complete. Full non-slow suite, old artifact hashes and fresh-output
no-overwrite checks must pass; publish all outcomes to #62 and #1. No retries
of valid scores, newly chosen label groupings, or larger follow-on campaign.

## Consult

Completed: Sol High recommends one bounded offline check first; Agy recommends
parking the idea entirely. Both advise against an interaction demo now. See the
[reconciled feedback](../../doc/shortlist-prototype-consult.md), including Agy's
sample-size misread and the distinction between half the label universe and
expected hit rate. Coordinator recommends the check solely as a kill test, not
as proof of usefulness; retain the original one-hour cap, not the proposed 90-minute
or four-hour expansions. No new collection daemon or additional model consultation.

Reuse existing validation/tests where they already guard these inputs; add only
tests for the new ranking/scoring seam and witness the listed failures. If that
does not fit the hour, stop with no score rather than building more infrastructure
or weakening guards after seeing results. Passing would not remove the separate
need to define what a future interaction study could learn without a ratings task.
Pre-run verification: inputs total 47,989,092 bytes; validation process peak RSS
177,782,784 bytes. Exact trusted hashes/counts, paired views, row identities,
issue/feature separation and all six labels pass. Planned memory allowance is
bounded input plus parsed rows/counters (<1 GiB tripwire); no GPU arrays or weights.
Synthetic-only tests reject bad hashes/counts, same-size target replacement,
empty data, overlap, duplicate identities/shortlist labels, wrong labels/views,
locked-output mutation and score tampering. Five deliberate source mutations in
memory fail tests (ranking, pooled-for-issue averaging, each of the three gates),
then pass after restoration. Real predictions remain uncomputed at this checkpoint.
