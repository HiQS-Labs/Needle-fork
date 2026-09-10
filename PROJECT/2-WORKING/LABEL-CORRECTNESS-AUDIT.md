---
title: "Label correctness audit — make the §2 gate trustworthy"
status: In progress
created: 2026-09-09
updated: 2026-09-10
owner: noelsaw1
goal: >
  Establish a repeatable estimate of whether the semantic mapper assigns the right
  label before using those labels for another training decision.
related:
  - https://github.com/HiQS-Labs/Needle-fork/issues/20
  - https://github.com/HiQS-Labs/Needle-fork/issues/23
  - https://github.com/HiQS-Labs/Needle-fork/issues/1
context_tags: [label-correctness, audit, measurement, oracle]
effort: 3
complexity: 3
risk: 2
phases: 1
---

# Label correctness audit — make the §2 gate trustworthy

**Raised:** 2026-09-09 · **Refs:** [#20](https://github.com/HiQS-Labs/Needle-fork/issues/20),
[#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §2 §5
**Reversibility:** Easy — audit tooling and aggregate receipts; no label or model contract changes

## Status

| What was just completed | What's next |
|---|---|
| #20's scorer correction is merged, and #23 traces all 61 adjudicated errors into weighted cause groups. | Run one two-arm feedback experiment using only the 26 high-confidence reviewed correction seeds and a fresh session-separated holdout. |

## Goal

Establish a repeatable estimate of whether the semantic mapper assigns the right label, separately
from coverage, before using those labels for another training decision.

## Current milestone

The frozen `v1.0.0` vocabulary remains unchanged. The existing 399-row audit and its error-cause
classification are reproducible. The next milestone tests whether a small reviewed correction
overlay improves a fresh holdout; taxonomy and mapper changes remain outside that comparison.

## Ground truth at takeover

The original audit correctly preserved 399 unique rows, complete answers from two auditors, and
exactly 82 third-auditor tie breaks. Its row-level judgments reproduce. Its measurement path did not:

- unequal predicted-label strata were pooled into an 84.7% headline and ordinary Wilson interval;
- duplicate IDs overwrote, missing IDs skipped, and extra/invalid rows were ignored;
- adjudication and the final aggregate had no committed executable path;
- confusion output was truncated;
- the sampler could miss its requested target, reuse a directory with stale answers, and reveal
  sorted strata through sequential IDs;
- no test covered either audit script.

## Corrected measurement

Against the unchanged adjudicated reference:

| Estimand | Sample agreement | Population-weighted estimate | 95% sampling CI |
| --- | ---: | ---: | ---: |
| All renderable calls | 338/399 = 84.71% | **77.84%** | 72.30–83.38% |
| Governance predicted strata | 108/113 = 95.58% | **94.32%** | 89.08–99.57% |
| Non-governance predicted strata | 230/286 = 80.42% | **76.78%** | 70.89–82.67% |
| Assigned labels only | — | **80.63%** | 74.89–86.37% |

The interval uses the stratified simple-random-sampling-without-replacement variance estimate. It
covers sampling error only. It does not include shared reference-label errors or generalization to
another operator, and all-right/all-wrong small strata contribute zero estimated variance.
The historical plan requested 400 rows and realized 399; these estimates use the recorded realized
allocation. Future draws now reach their target exactly or refuse.

Population weighting also changes the error priority: `run_script` contributes an estimated 10.86
percentage points of corpus error, while `unmapped` contributes at most 3.46 points. Neither point
estimate establishes the cause of the error.

## Deterministic acceptance gates

- [x] Exact row-set gate: duplicate, missing, extra, unknown-label, invalid-confidence, and
  allocation-mismatched inputs fail closed before any report is written.
- [x] Format gate: new plans require audit format v2. The frozen unversioned plan requires the
  explicit `--allow-legacy-plan` compatibility switch, which is recorded in the receipt.
- [x] Adjudication gate: the scorer requires exactly the two auditors' disagreement IDs and builds
  the final reference deterministically.
- [x] Estimand gate: unweighted sample agreement and population-weighted estimates are named and
  reported separately; pooled Wilson intervals are not presented as corpus uncertainty.
- [x] Receipt gate: full confusion pairs, weighted error contributions, interval method, and limits
  are emitted by the scorer.
- [x] Sampling gate: allocation equals the requested target or refuses; a non-empty output directory
  refuses; IDs are assigned after shuffling and derived from row content rather than stratum order.
- [x] Red controls: malformed synthetic submissions were observed passing the previous scorer; the
  focused tests now require the intended rejection message and absence of output.
- [x] Merge gate: `pytest -q -m "not slow"` passes on the final branch and the regenerated aggregate
  receipt matches the documented values.

## Decisions withdrawn

The predeclared rule that a result at or below 85% proves the ordered-rule mechanism must be replaced
is withdrawn. A score measures error frequency, not root cause. The issue #20 P1→P4 sequence is also
superseded: `unmapped`-first sampling, precedence edits, and a taxonomy version bump do not follow
from this corrected audit.

## Independent check

A one-shot consult degraded to one advisor because the installed Codex CLI could not serve its
requested model. Treating it as single-model advice, agy independently selected the same bounded
measurement correction before the P1→P4 campaign. The code and tests above, rather than that
opinion, are the acceptance evidence.

## Error-cause review

The deterministic #23 analyzer requires exactly the 61 adjudicated error IDs, checks every recorded
label pair against the frozen reference, reruns the current taxonomy on every error, and refuses
unknown causes or assertions without an observed mechanism and falsifier. It reproduces the 22.16%
estimated population error before aggregating causes.

| Observed cause | Population-error contribution |
| --- | ---: |
| Shell visibility | **6.99 pp** |
| Inline-program semantics | **5.43 pp** |
| Multi-action one-label selection | **4.46 pp** |
| Taxonomy boundary | **2.66 pp** |
| Direct rule defect | **2.52 pp** |
| Reference uncertainty | **0.10 pp** |

Shell visibility and inline semantics together account for 56.05% of estimated error. This rejects
`unmapped`-first work and the claim that rule ordering alone is the dominant root cause. Cause
labels are reviewer judgments; their weights measure prevalence, not recoverable gain.

A conservative feedback seed contains 26 rows with high-confidence cause and reference judgments.
Use the reviewed label as the positive and the old sorter label as the hard negative. Exclude rows
whose target depends on multi-action selection, a taxonomy boundary, or an uncertain reference.

## One next action after this milestone

Run an unchanged-training versus corrected-feedback comparison using a private overlay for those 26
seeds. Ordinary 44-way supervised loss already supplies negative pressure, so start by correcting
and reweighting examples rather than adding a preference-training subsystem. Evaluate only on a
fresh, session-separated holdout; the 399 audit rows have informed development.

## Privacy and retained evidence

Row-level audit files remain under gitignored `data/`. Public receipts contain aggregates and label
pairs. The operator separately authorized existing prompt transcripts to remain public and reported
that prompts do not contain credentials; a credential-pattern scan found no recognized secrets.
