# Label correctness — corrected stratified estimate

**Date:** 2026-09-09 · **Mapper:** `main` @ `13a156b` · **Label set:** `v1.0.0` (44 labels)
· **Sample:** 399 rows, 40 predicted-label strata, seed 20260909 · **Machine:** Mac16,8,
Python 3.11.15 · **Refs:** [#20](https://github.com/HiQS-Labs/Needle-fork/issues/20),
[#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §2

> **Correction:** the first receipt called 338/399 = 84.7% the overall precision and attached a
> pooled Wilson interval. The sample deliberately over-represents small strata, so 84.7% describes
> the audited sample, not the corpus. The row judgments are unchanged. The population-weighted
> estimate is **77.84%** with a **72.30–83.38% sampling-error interval**.

## Protocol and estimands

The sampler allocated a floor of eight rows per predicted label, then distributed the remainder
approximately in proportion to √(stratum size). Two auditors labelled all 399 rows without seeing
the sorter's answer. They agreed on 317; a third auditor adjudicated exactly the 82 disagreements,
also blind to the sorter.

The historical plan requested 400 rows but its allocation realized 399. The corrected estimate and
variance use the 399 observed rows and their recorded per-stratum allocation. The new allocator
either reaches the requested target exactly or refuses.

Two numbers serve different purposes:

- **Sample agreement** is the unweighted score on the deliberately rebalanced 399 rows. No pooled
  confidence interval is attached to it.
- **Population agreement estimate** weights each predicted-label stratum by its saved population
  share. Its interval uses the stratified simple-random-sampling-without-replacement variance
  estimate and covers sampling error only.

## Corrected result

| Estimand | Sample agreement | Population-weighted estimate | 95% sampling CI |
| --- | ---: | ---: | ---: |
| All renderable calls | 338/399 = **84.71%** | **77.84%** | 72.30–83.38% |
| Governance predicted strata | 108/113 = **95.58%** | **94.32%** | 89.08–99.57% |
| Non-governance predicted strata | 230/286 = **80.42%** | **76.78%** | 70.89–82.67% |
| Assigned labels (`unmapped` excluded) | — | **80.63%** | 74.89–86.37% |

The population interval is a normal approximation to the standard stratified SRSWOR variance
estimator. It
does **not** cover reference-label error, shared auditor mistakes, or generalization beyond this
operator and corpus. Small strata observed as all right or all wrong contribute zero estimated
within-stratum variance, so the interval should not be read as exact.

Raw auditor agreement also changes materially under population weights:

| Reference | Sample agreement | Population-weighted agreement |
| --- | ---: | ---: |
| Claude | 315/399 = 78.95% | 76.71% |
| agy | 334/399 = 83.71% | 76.44% |
| Claude ↔ agy | 317/399 = 79.45% | 75.51% |

Inter-rater agreement is evidence that the reference is noisy. It is not a mathematical ceiling on
sorter accuracy and is not part of the sampling-error interval.

## Where estimated corpus error concentrates

Per-label point estimates remain noisy because most strata have 8–15 audited rows. Weighting by
population changes the priority implied by raw stratum precision:

| Predicted stratum | Audited precision | Estimated contribution to corpus error |
| --- | ---: | ---: |
| `run_script` | 5/15 = 33.3% | **10.86 pp** |
| `unmapped` | 0/11 = 0% | **3.46 pp** |
| `apply_patch` | 12/14 = 85.7% | **1.70 pp** |
| `read_file` | 14/15 = 93.3% | **1.18 pp** |
| `sys_inspect` | 4/10 = 40.0% | **1.10 pp** |
| `find_files` | 9/12 = 75.0% | **1.09 pp** |

This reverses the proposed `unmapped`-first priority: `run_script` has the largest estimated impact.
It does not establish why those rows are wrong. Definition ambiguity, auditor interpretation,
command mix, and mapper defects remain competing explanations until the source rows are classified.

Governance's 95.58% sample precision means rows *assigned* governance labels were usually accepted
by the adjudicated reference. It does not measure governance recall or contradict the adversarial
spoofing defects found and fixed earlier.

## Corrected interpretation of confidence and adjudication

The sorter agrees on 231/240 = 96.25% of the rows where both auditors were confident and agreed.
Against the same adjudicated reference, it agrees on 107/159 = **67.30%** of the remaining rows. The
previous 52.8% figure used Claude alone for the latter subset and mixed reference standards.

The adjudicator chose Claude's answer 36 times, agy's 37 times, and a third label 9 times. That split
does not by itself distinguish genuine ambiguity from auditor error. Agreement rows were not
independently adjudicated, so shared errors remain unmeasured.

## Deterministic gates added after the first receipt

`score_audit.py` now refuses duplicate, missing, extra, unknown-label, invalid-confidence, or
plan/allocation-mismatched rows; requires the adjudicator to cover exactly the disagreements; builds
the adjudicated result itself; emits full confusion tables and weighted error contributions; and
writes reports atomically. The sampler now reaches the requested allocation exactly, refuses a
non-empty output directory, and assigns stable content-derived IDs only after shuffling so IDs do
not reveal the predicted stratum.

The original 399-row files pass every scorer gate and reproduce all row counts. Focused tests include
witnessed malformed-input failures, unequal-stratum weighting, exact allocation, complete confusion
output, stale-output refusal, deterministic adjudication, and opaque IDs.

## Decision

The earlier threshold rule—“≤85% proves the rule-order design must be replaced”—is withdrawn. The
score establishes an error rate, not its cause. The issue #20 P1→P4 sequence is also superseded:
neither `unmapped`-first work, precedence changes, nor a new taxonomy version follows from the
corrected aggregate alone.

The next bounded action is to classify the existing adjudicated errors by verified cause and rank
them by population-weighted contribution, without changing rules or label names. Any later fix is
evaluated on fresh held-out rows because these 399 rows have now informed development.

## Reproduce

```sh
python3.11 utils/corpus/score_audit.py \
  --dir data/audit \
  --auditors claude,agy \
  --adjudicator codex \
  --out TESTS-RESULTS/2026-09-09-label-correctness-audit/raw-metrics.json \
  --adjudicated-out TESTS-RESULTS/2026-09-09-label-correctness-audit/adjudicated.json
```
