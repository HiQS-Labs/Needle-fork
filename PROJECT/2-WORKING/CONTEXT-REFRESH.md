---
title: Versioned context refresh and fresh-issue comparison
status: In Progress
created: 2026-09-12
updated: 2026-09-12
owner: noelsaw1
goal: Test whether restoring observable context improves next-action prediction.
reversibility: Easy — opt-in offline extraction and retained receipts
---

# Context refresh — two bounded rounds

Authority: [#59](https://github.com/HiQS-Labs/Needle-fork/issues/59), following #53/#56.

## Status

| What was just completed | What's next |
|---|---|
| Round one verified: 10,000 train rows, 1,722 fresh eligible rows, 40 frozen quiz cases; 486 tests passed. | Commit/push round one, then immediately run the fixed Qwen comparison. |

## Contents

- [Contract](#contract)
- [Round one](#round-one)
- [Round two](#round-two)
- [QA](#qa)

## Contract

Operator authorized two rounds on main, a commit/push per round without pausing, and
adaptation of round two. Absolute deadline: 2026-09-12 17:59:35 UTC (two hours).
No downloads, dependencies, neural training, serving changes, new panel, or PR #43 changes.
The existing #51 NB stop remains in force. Prior scores/gates/data stay frozen.
See [grounded recon](recon-context-refresh.md). This is public coding-agent behavior,
not personal intent, human acceptance, or a test of a deployable tiny model.

The bet (a bundled refresh, not a single-field ablation): an issue-focused task (2,000 characters), compacted observation (2,000),
and identity/selected arguments of the last **completed** call (1,000) may restore
useful information lost by q2. q3 is opt-in; q1/q2 feature behavior stays unchanged.
Arguments, results and prose of the target/future actions never enter features.
Retain mechanical label policy: native editor view, including directories, is read;
ad-hoc verification scripts are run_command; named test/lint/build runners are run_tests.
Do not relabel to agree with predictions. Explain policy identically to each arm.

## Round one

1. [x] Add q3 through the existing matched-call state machine; prove q2 preservation,
   clipping bounds, prior-call identity, future invariance and boundary resets.
2. [x] Reuse the verified retained 1,000-trajectory source and first resolved trajectory
   per issue/trajectory ID; train only on the old train issue IDs, capped at 10,000
   rows/50 per issue. The fresh eligible pool uses hash-holdout issues absent from both old
   train and holdout, capped at 2,000 rows/50 per issue. Require 1,000 train rows,
   200 eligible fresh rows and 30 fresh issues. The model quiz is a separate subset:
   one case per issue, expected 40 cases (not a 200-case model evaluation).
   Exclude exact feature overlap from training
   using both q2 and q3 signatures. Assert aligned labels/history/row counts.
3. [x] Select one of the first 50 eligible transitions per fresh issue using SHA-256
   seed `context-refresh-v3`, without consulting targets. In source chronological
   eligible-row order, select the minimum SHA-256 hex digest of UTF-8
   `context-refresh-v3:ISSUE:ZERO_BASED_INDEX`; order issues by the SHA-256 of
   `context-refresh-v3:ISSUE`. Freeze manifests, paired
   answer-blind packets, hashes and training-only action baselines. Publish aggregate
   receipt. Round-one landing precedes all model calls.

Evidence: [round-one receipt](../../TESTS-RESULTS/2026-09-12-context-refresh/SUMMARY.md).

## Round two

1. [ ] Run the previously tested `qwen/qwen3.8-max-0902` OpenRouter route in three
   independent tool-free chat-completion requests: q2, q3, q3 with task/observation shuffled across cases within last-action
   groups (deterministic derangement, histories untouched; report fixed singletons).
   This is one controlled comparison, not three candidates. No answers, scores,
   source IDs, paths or peer outputs in packets. No tool use; inspect transcripts.
   Send no tool schemas, files, source paths, answer keys, or conversation history.
   Direct HTTP response text is never dispatched as an action. Before calls, verify
   route/prices and require worst-case input/output token cost <=$1 total; no fallback
   model or token-budget increase. Cap each output at 4,096 tokens, temperature zero.
   Maximum 600 seconds per arm, one infrastructure-only retry before any scoring;
   never retry a valid prediction. Stop for unavailable route or invalid responses.
2. [ ] Lock all responses before grading. Compare accuracy, six-label macro-F1,
   per-label support/recall, and change-only accuracy with training-only majority,
   repeat-last, Markov and phase-backoff on the same cases. Report paired wins/losses.
   Exploratory follow-up signal requires q3 accuracy >=5pp over strongest action
   baseline, q2, and shuffled q3, plus macro-F1 no worse than strongest action baseline.
   This only motivates a larger validation; missing labels preclude full six-action
   coverage claims. A failure stops investment in this context change, not the entire
   project. No post-score gate movement or automatic model promotion.
3. [ ] Record outcome/next decision, reconcile project story and issue, commit/push
   round two. On deadline or failed preflight, publish the incomplete/negative receipt,
   not invented model scores. No manual calibration required for this experiment.

## QA

Witness red controls for prior-result mismatch, target/future leakage, empty data,
overlap, malformed/duplicate/missing predictions, and deliberately wrong scores.
Run the full non-slow suite before model spending and each landing. Re-extract into
a different fresh directory and compare hashes. Re-score locked responses identically.
Raw records stay ignored; public receipts contain aggregate data and reproducible code.
Bounded streaming source is ~285 MB on disk; extracted text at most ~60 MB, quiz
under 250 KB per arm. Existing RSS tripwire at 1 GiB is not an OS-enforced ceiling
on this Mac. No GPU work. Model token/cost accounting may be unavailable via CLI.

## Plan review reconciliation

Codex and Gemini 3.1 Pro answered independently; both endorsed the chronology and
source separation design, without executing the implementation. Codex's alleged
40/200 contradiction was ambiguity between eligible pool and quiz, now explicit;
do not expand to five cases per issue. Adopt exact selection formula and the bundled
effect limitation; reject reducing q3 to 600 task characters, which defeats this
specific refresh. Gemini's claim that JSON labels automatically execute is not how
the harness works, but live agent tools are unnecessary risk. Resolve that concern
by adapting round two to the previously tested Qwen route over tool-free HTTP,
before any prediction/scoring. Adopt identical schema for shuffled text. No further
model panel, per-feature study, or review loop. Raw review transcripts remain private.
