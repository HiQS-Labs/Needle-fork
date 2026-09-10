---
title: "Label correctness audit — make the §2 gate trustworthy"
status: In progress
created: 2026-09-09
updated: 2026-09-09
owner: noelsaw1
goal: >
  Establish a repeatable estimate of whether the semantic mapper assigns the right
  label before using those labels for another training decision.
related:
  - https://github.com/HiQS-Labs/Needle-fork/issues/20
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
| The scorer, sampler, tests, aggregate receipt, and repository-wide merge gate are complete. | Publish the review branch and replace issue #20's superseded sequence with this result. |

## Goal

Establish a repeatable estimate of whether the semantic mapper assigns the right label, separately
from coverage, before using those labels for another training decision.

## Current milestone

The frozen `v1.0.0` vocabulary remains unchanged. The current task is to make the existing 399-row
audit reproducible and statistically consistent. Taxonomy changes, new sampling, and training are
outside this milestone.

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

## One next action after this milestone

Classify the existing adjudicated errors by observed cause and rank the causes by population-weighted
contribution. Do not edit the mapper or vocabulary during classification. A later change must use a
fresh held-out audit because these 399 rows now informed development.

## Privacy and retained evidence

Row-level audit files remain under gitignored `data/`. Public receipts contain aggregates and label
pairs. The operator separately authorized existing prompt transcripts to remain public and reported
that prompts do not contain credentials; a credential-pattern scan found no recognized secrets.
