# Top-three shortlist kill test (#62) — 2026-09-12 Pacific

## Verdict: useful narrow signal, failed investment rule — park

History-based counts improve coarse shortlist coverage, but the phase-aware
candidate did not clear the fixed margin over the strongest cheap baseline.
**Issue-macro hit@3: 89.3789% versus Markov 85.1211%; +4.2578 points, required +5.**
The other two gates passed. Do not round this up, tune it, or build a prototype
as an automatic follow-on. This closes the count-based shortlist round, not the
question of whether any future next-action product could be useful.

The bigger-picture gain is knowing that simple history already captures much of
this six-label task; extra phase detail adds only a limited margin over Markov.
This is stronger evidence of a narrow ranking signal, **not evidence of useful
personal recommendations**. Three broad labels cannot specify the right file,
command, timing or reason. No human acceptance or governance capability was tested.

## Same-case results

All arms score all 1,722 development rows / 40 issues. Primary metric gives each
issue equal weight; pooled percentages are separate and never substituted for it.

| Arm | Pooled hit@1 | Pooled hit@3 (correct) | Issue-macro hit@3 | Six-label macro recall@3 |
|---|---:|---:|---:|---:|
| Static training frequency | 26.07% | 69.05% (1,189) | 68.86% | 50.00% |
| Repeat last + frequency fill | 31.94% | 75.03% (1,292) | 74.92% | 63.05% |
| Markov + frequency fill | 49.42% | 85.31% (1,469) | 85.12% | 78.47% |
| Phase-aware + frequency fill | 53.54% | 89.43% (1,540) | 89.38% | 81.36% |
| Phase with permuted histories | 23.05% | 61.50% (1,059) | 61.59% | 49.77% |

| Fixed gate versus strongest control (Markov) | Measured | Decision |
|---|---:|---|
| >=5 absolute points issue-macro lift | +4.2577911830 | Fail (0.7422088170 points short) |
| No six-label macro recall decrease | +2.8823971592 | Pass |
| Strictly more issue wins than losses | 34 wins / 3 ties / 3 losses | Pass |

Candidate beats static/repeat controls on all 40 issues; those weaker comparisons
do not replace the predeclared strongest-control test. The threshold is a chosen
engineering investment heuristic, not a statistical-significance boundary.

## Label and action-change limitations

| Label | Support | Markov recall@3 | Phase recall@3 |
|---|---:|---:|---:|
| edit | 281 | 98.58% | 90.04% |
| git | 33 | 36.36% | 39.39% |
| read | 449 | 82.41% | 91.09% |
| run_command | 450 | 84.67% | 94.67% |
| run_tests | 219 | 85.39% | 88.13% |
| search | 290 | 83.45% | 84.83% |

Edit recall regresses by 8.54 points (24 fewer hits); the higher macro average
does not erase this tradeoff. Git remains weak with only 33 targets. On 1,172
ordinary action-change rows, phase pooled hit@3 is 84.81% (994), Markov 78.41%
(919); issue-macro rates 84.59% / 77.84%. Git changes are captured only 1/21 times
by phase (Markov 0/21). These are diagnostic subsets, not alternative promotion
gates. Previous actions remained eligible in every prediction: no oracle switch
exclusion or target-dependent shortlist generation.

## Provenance, cost and verification

Authority: [#62](https://github.com/HiQS-Labs/Needle-fork/issues/62). Fixed scope
at `ee28f3e`; implementation/tests committed and pushed before scoring at
`06b3bfb`. Start 2026-09-13 02:35:25 UTC, one-hour absolute bound to 03:35:25 UTC.
One valid fit/predict/score invocation; exit 1 means the rule failed, not a crash.
No new models, API prediction calls, downloads, neural training or manual ratings.
Wall time for the invocation: **1.733 seconds**; peak RSS **206,995,456 bytes**
(197.4 MiB). The 600-second alarm did not fire. macOS rejected RLIMIT_AS; bounded
bytes and 1 GiB RSS checkpoints are tripwires, not a guaranteed hard memory cap.

Reuse trusted [#59 manifest](../2026-09-12-context-refresh/manifest.json): 10,000
training rows / 224 issues, 1,722 development rows / 40 disjoint issues, 47,989,092
bytes total. All six labels, paired q2/q3 alignment, exact row identity and
cross-view feature separation validated. No re-extraction or row re-selection.
The issues were already used in #59: this is reused public development evidence,
not fresh confirmation, personal-domain transfer or an independent benchmark.

Predictions use only histories and training counters, with fixed support floor,
count/prior/lexical ranking and distinct global-prior fill. All four unshuffled
rank-one predictions match the original ordinary predictors on every row. The
history-permutation null SHA-sorts zero-based indices using `shortlist-v1:INDEX`,
then cyclically assigns donor histories without moving targets; 1,717/1,722
histories differ. It is an association diagnostic, not a causal conclusion.

Prediction vectors were written and hashed before any score; retained privately
with per-issue details. [Lock](lock.json), [aggregate metrics](metrics.json) and
[resource receipt](resources.json) are byte-identical public copies; no private
IDs, prompts or paths included. Public counts/hashes refer to public-derived
data and code. Replay verifies the trusted manifest and prediction lock, reloads
the same data and reproduces the metrics without refitting.

17 focused tests and 510 non-slow tests passed (6 skipped, 11 deselected).
Synthetic controls reject empty/wrong/count-mismatched inputs, same-size target
substitution, issue overlap, wrong paired views, duplicate identities/shortlists,
unknown labels, prediction-lock tampering, score tampering and output overwrite.
Five in-memory source mutations produced red then green tests: broken ranking,
pooled-for-issue averaging, and each of the three gates. No source mutation persisted.
An independent calculation from locked vectors reproduced pooled, per-label,
per-issue and change-slice arithmetic and wins/ties/losses; altered count and
false-pass controls failed. All 13 old panel hashes and all 10 #59 artifact hashes
remain unchanged. Initial verification selected the wrong panel JSON wrapper,
then was corrected to its actual `metrics.json` hash map; that failed check was
not counted as evidence. No historical score changed and PR #43 remains held.

## Reproduce from retained local artifacts

No network needed. Run from the repo root with the existing Python environment:

```bash
# Replay only; no model refit or new experiment:
.venv-mlx-spike/bin/python spike/coding_core/shortlist_eval.py \
  --data data/context-refresh-round1 --out data/shortlist-round62 --replay
.venv-mlx-spike/bin/python -m pytest -q tests/test_shortlist_eval.py
```

The original command was the same evaluator invocation without `--replay`; it
refuses an existing output directory. Do not launch another scoring round merely
to improve this result. Missing retained private artifacts are a replay limitation,
not permission to regenerate inputs or change the expected hashes silently.
