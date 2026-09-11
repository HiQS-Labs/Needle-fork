# Coding-core state/transition pivot — 2026-09-11

## Decision

**The development gate promoted one frozen phase-aware backoff classifier; the disjoint private
gate then stopped it.** It scored 42/100 on the OpenHands development holdout, but only 25.23% on
23,442 eligible private actions from 63 held-out sessions. This does not authorize serving work or
establish product efficacy.

## Frozen candidate

For each prior-action history, fit target counts at these levels and use the first level with at
least two training examples:

1. `(last action, whether edit occurred before last, penultimate action)`
2. `(last action, whether edit occurred before last)`
3. Markov-1 `(last action)`
4. Global majority

Ties use global target frequency and then lexical order. The implementation is standard-library
only and extends the existing baseline evaluator. It does not consume `reasoning` or target fields
as features. ISSUE text is parsed to validate the serialized input contract but intentionally not
learned: 500 rows represent only 11 repeated training requests.

## Evidence ledger

| Probe | Top-1 | Outcome |
|---|---:|---|
| Majority | 26% | Reference |
| Repeat last | 22% | Reference |
| Markov-1 | 37% | Reference |
| Higher-order backoff, max order 2 | 37% | Rejected |
| Higher-order backoff, max order 3 | 37% | Rejected |
| Higher-order backoff, max orders 4–6 | 32%, 31%, 30% | Rejected |
| Phase-aware backoff | **42%** | Development gate met |

Inputs were the same 500-row training and 100-row/two-instance development partitions recorded in
the preceding pilot. Their SHA-256 hashes are retained in the ignored machine-readable receipt.
The development set had already informed the prior generative decision, so this is a promotion
screen rather than untouched confirmation.

## Falsification and verification

- Gate: phase-aware top-1 must be at least 42%; otherwise stop.
- Red control: temporarily raised the gate to 43%; the evaluator reported `passed: false` and exited
  1. Restoring 42 reported `passed: true` and exited 0.
- Focused parser/classifier suite: 16 passed. Full non-slow suite: 198 passed, 6 skipped,
  6 deselected. Python compilation and `git diff --check` passed.
- Independent design consult: both advisors favored a standard-library classifier and warned that
  the two-instance development score is brittle. They disagreed on raw issue-text Naive Bayes versus
  bounded phase features; the phase design won because it avoids repeated-request pseudo-replication.
- One advisor asserted a 44–45% result without firsthand-verification evidence. That assertion was
  excluded; only the locally reproduced 42% result is recorded as evidence.

## Disjoint private round

The implementation was frozen and the existing private Oracle holdout was projected into the same
six labels. Control actions break history; canonical read/search/edit/test/git actions map directly,
and remaining operational actions map to `run_command`. The classifier was fitted only on the 500
OpenHands training rows and scored once without private fitting or tuning.

| Candidate | Private top-1 |
|---|---:|
| Majority | 29.04% |
| Repeat last | **43.52%** |
| Markov-1 | 28.78% |
| Phase-aware backoff | 25.23% |

The private promotion gate was Markov-1 plus five points: 33.78%. Phase-backoff missed it by 8.55
points and is stopped. The OpenHands transition table did not transfer across domains; simple action
persistence did. That makes repeat-last the next smallest product hypothesis, not a reason to tune
the stopped classifier on private labels.

The private machine-readable receipt retains input hashes locally. This public summary contains
only aggregate counts and scores—no sessions, prompts, commands, paths, or row-level material.
The private projection invariant was witnessed red by deliberately mapping `run_tests` incorrectly;
its focused test failed, then passed again after restoring the canonical projection.
