---
title: Private-trained transition comparison
status: Completed
created: 2026-09-11
updated: 2026-09-11
owner: noelsaw1
goal: Run the agreed bounded private-training comparison and report both gates honestly.
---

# Private-trained transition comparison

## Status

| What was just completed | What's next |
|---|---|
| One frozen private round completed; both families failed both gates. | Review PR #48; no tuning or serving. A different product scope needs a new decision under #1. |

Canonical authority: [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1), including the
Astra/Fable synthesis and subsequent operator authorization. PR #43 remains held and untouched.

## Recon (before implementation)

Mode: direct source reads, one local lane. Base main `cc8f462`; selected experimental source
`18274fc5f03081c6ff6f5724fd7d07ea106ee534` from #42. Only `spike/coding_core/baselines.py`
is selected, not the MLX branch or its other files.

- Existing CLI -> `load` / `load_oracle_pairs` -> `evaluate` -> `choose` / `phase_keys`.
  The private loader only handles holdout; `evaluate` fits training counters and scores binary hits.
- `utils/corpus/extract_claude_transcripts.py:160` assigns one split per session; lines 184–191
  emit session, step, prior actions, and target. Histories precede the target.
- Projection reads `taxonomy.LABELS_V1`; controls reset history, other groups project into six
  actions. No re-labeling or raw prompt features are added.
- Existing consumers are the experimental CLI and `tests/test_coding_core.py` on #42; main has
  no consumers. Preserve the old public evaluation function for parity checks.
- Output is a new aggregate receipt; private source is read-only. Loader errors, empty inputs,
  split overlap and duplicate events must stop before fitting. No checkpoint/cache/network writes.
- Unknown: historical private receipt is not in main; confirm source by reproducing its 23,442
  eligible rows / 63 sessions and recorded repeat-last count. Original raw event identity is legacy,
  so session/step and content overlap checks have limits; disclose them rather than claim fresh data.
  Preflight confirmed 23,442 eligible evaluation rows / 63 sessions, 45,128 eligible training rows
  / 296 sessions. One exact shared canonical content row is excluded from training, leaving 45,127.
  No shared sessions or duplicate session/step events; all six training labels have support.

## Frozen protocol and execution

Completed protocol retained below as history, not instructions to repeat the run. Measured
phase-backoff: 45.7256% overall, 40.8112% conditional destinations; required 48.5244% and 40.8634%.
Markov-1: 43.5244% and 37.9711%. Decision: stop. Pooled receipt is
`TESTS-RESULTS/2026-09-11-private-transitions/SUMMARY.md`; detailed distributions remain private.

Reversibility: Easy — additive isolated experiment; no runtime, taxonomy, release or held-branch
changes. Preserve private inputs byte-for-byte; publish aggregates only. Budget: one engineer-hour,
stdlib only, one fit/score round, no feature or threshold search. Debug-mantra governs any failure.

1. Validate the existing split, nonempty rows and action-change subset; record counts/hash privately.
   Refuse shared sessions or repeated session/step events. Audit exact canonical request/history/target
   overlap; remove overlapping training content before fitting, never change evaluation membership.
   This is an exact serialized-content safeguard, not proof of raw-transcript deduplication;
   do not remove common projected six-action transition tuples across independent sessions.
2. Extend the existing evaluator with private train/holdout loading and per-session reporting.
   Keep phase keys, support floor 2, majority ties and original ordinary predictions unchanged.
   For conditional destination scoring, exclude the previous action at every level, then measure
   support: fine phase (>=2), coarse phase (>=2), transition (>=1), global training change-destination
   frequencies (>=1). An empty terminal distribution fails closed. Ordinary predictions retain
   their original support and fallback rules. The destination baseline uses the same global
   training change-destination frequencies excluding the previous action; ties use global training
   target frequencies then lexical order. This conditional variant cannot detect when to switch.
3. Test empty/overlap refusal, prefix-only prediction, exclusion/backoff and same-family gate logic.
   Compare ordinary predictions with frozen `evaluate`; witness red controls on synthetic fixtures.
   Retain verification in the dated receipt. No private scores before these checks.
4. Fit both models once on private train and score existing evaluation. Require the SAME family to
   beat repeat-last by >=5 percentage points overall and destination baseline by >=10 points on
   change rows with the previous action excluded. Also report ordinary change-row scores and
   per-session distributions. Families are exactly `markov_1` and `phase_backoff`, with both margins
   evaluated separately for each. Empty slices cannot pass. CLI asserts 23,442 evaluation rows and
   63 sessions before fitting. Keep per-session distributions and private input hashes in ignored
   receipts; publish only pooled counts/scores, no session-level values or identities.
5. Record result and limitations in #1, FINDINGS, README and a focused PR. Both gates pass: design
   prospective serving next; only one passes: consider separately scoped action-run-ending work;
   neither passes: stop these two models at this representation. Do not call label agreement human
   acceptance or reused evaluation fresh confirmation.

## QA

2026-09-12 review follow-through: CLI reruns now verify the retained private manifest's input digest
before loading/fitting and check frozen train/session/overlap counts. The original result is unchanged.
Use the trusted original private receipt as `--private-manifest`; never regenerate its expected digest
from an unverified replacement input. Same-size substitution failed a red regression before the fix.

Consult reconciliation: both advisors required explicit filtered support/fallback rules, implemented
split checks and same-family gates before execution. They differed on privacy: one allowed anonymous
session summaries and input hashes, the other rejected public distributions/hashes. Use the stricter
boundary: private detailed receipt, public pooled metrics only. Both reviewed the pre-implementation
code, not a completed experiment; their advice is not runtime verification. No new model suggested
by review is in scope. Raw consult logs remain private because they contain local paths.

- [x] Nonempty/split/content checks and falsification tests pass with red controls witnessed.
- [x] Predictor parity and full non-slow suite pass (398 passed, 6 skipped, 11 deselected).
- [x] One frozen result and sanitized receipt recorded; no private rows or IDs published.
- [x] Issue and current docs reconciled with measured outcome; #43 unchanged at `974ddcf`.
