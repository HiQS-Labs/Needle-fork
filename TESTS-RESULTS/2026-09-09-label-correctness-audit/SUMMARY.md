# Label correctness — corrected stratified estimate

**Date:** 2026-09-09 · **Mapper:** `main` @ `13a156b` · **Label set:** `v1.0.0` (44 labels)
· **Sample:** 399 rows, 40 predicted-label strata, seed 20260909 · **Machine:** Mac16,8,
Python 3.11.15 · **Refs:** [#20](https://github.com/HiQS-Labs/Needle-fork/issues/20),
[#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §2,
[#23](https://github.com/HiQS-Labs/Needle-fork/issues/23)

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
either reaches the requested target exactly or refuses. Because the frozen plan predates the format
stamp, reproduction requires the explicit `--allow-legacy-plan` switch; new unversioned plans fail.

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

## Cause review

The 61 adjudicated sorter disagreements were traced through the current segmenter and rule matcher,
then assigned one primary observed cause. The row-level judgments and command text remain under
ignored `data/`; `cause-metrics.json` contains aggregates only.

| Primary cause | Error rows | Contribution to population error | Share of estimated error |
| --- | ---: | ---: | ---: |
| Shell visibility (wrappers, loops, environment prefixes, heredoc shapes) | 21 | **6.99 pp** | 31.55% |
| Intent inside Python/heredoc program text | 5 | **5.43 pp** | 24.50% |
| Several real actions forced into one label | 14 | **4.46 pp** | 20.12% |
| Missing or overlapping label definition | 9 | **2.66 pp** | 12.01% |
| Direct rule or alias defect | 10 | **2.52 pp** | 11.36% |
| Adjudicated reference not uniquely supported | 2 | **0.10 pp** | 0.46% |

These are reviewer-assigned cause judgments, not experimental causal effects. The weights estimate
how much each observed class contributes to the saved frame's 22.16% error; they do not predict how
much a particular fix will recover. Treating all low-confidence cause judgments as unresolved still
leaves the same top three causes and moves 2.76 percentage points (12.47% of estimated error) into
the unresolved bucket.

The trace falsifies two prior framings. `unmapped` can contribute at most 3.46 percentage points,
so it is not the largest place to start. Fixed one-label selection accounts for 20.12% of estimated
error, so rule ordering alone does not explain most of the measured problem. Shell visibility plus
inline-program semantics account for 56.05% of estimated error and are the dominant observed limit
of the current command-pattern mapper.

## Feedback implication

The existing data can seed improvement. A conservative deterministic filter finds **26 rows** where
both the cause and adjudicated reference are high-confidence and the cause is shell visibility,
inline semantics, or a direct rule defect. They represent 12.31 percentage points, or 55.55%, of
the estimated error. For training, the adjudicated label is the positive and the old sorter label is
the hard negative. This set is development data, not a test set, and its weighted contribution is
not the gain training will achieve.

Ordinary 44-way supervised training already pushes down every non-target label. The lean experiment
therefore corrects and reweights these examples before considering a separate preference-training
system. Multi-action, taxonomy-boundary, and uncertain-reference rows are excluded until a written
one-label rule makes their target stable. Any result must be scored on fresh, session-separated rows.

## Decision

The earlier threshold rule—“≤85% proves the rule-order design must be replaced”—is withdrawn. The
score establishes an error rate, not its cause. The issue #20 P1→P4 sequence is also superseded:
neither `unmapped`-first work, precedence changes, nor a new taxonomy version follows from the
corrected aggregate alone.

The next bounded action is a two-arm feedback experiment: unchanged training versus the same
training with the 26 reviewed correction seeds applied through a private training-only overlay.
The mapper and `v1.0.0` vocabulary remain unchanged for that comparison. The current 399 rows must
not be used for evaluation; the gate is a fresh session-separated holdout.

## Reproduce

```sh
python3.11 utils/corpus/score_audit.py \
  --dir data/audit \
  --auditors claude,agy \
  --adjudicator codex \
  --allow-legacy-plan \
  --out TESTS-RESULTS/2026-09-09-label-correctness-audit/raw-metrics.json \
  --adjudicated-out TESTS-RESULTS/2026-09-09-label-correctness-audit/adjudicated.json

python3.11 utils/corpus/analyze_audit_causes.py \
  --dir data/audit \
  --auditors claude,agy \
  --adjudicator codex \
  --causes data/audit/error-causes.jsonl \
  --allow-legacy-plan \
  --out TESTS-RESULTS/2026-09-09-label-correctness-audit/cause-metrics.json
```
