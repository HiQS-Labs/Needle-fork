---
gh_issue: 41
source: https://github.com/HiQS-Labs/Needle-fork/issues/41
title: "Targeted grounded augmentation — Build Plan"
status: In progress
created: 2026-09-11
updated: 2026-09-11
owner: noelsaw1
goal: Prove whether grounded training-only counterfactual augmentation can be composed safely before spending model-training time.
doc_type: feedback
related:
  - https://github.com/HiQS-Labs/Needle-fork/issues/1
  - https://github.com/HiQS-Labs/Needle-fork/issues/25
  - https://github.com/HiQS-Labs/Needle-fork/issues/37
context_tags: [augmentation, governance, corpus, evaluation]
effort: 3
complexity: 3
risk: 2
phases: 3
branch: feat/gh-41-targeted-augmentation
reversibility: Easy — additive offline tooling and fixtures; no runtime, model, or taxonomy mutation.
---

# Targeted grounded augmentation — Build Plan

## Status

| What was just completed | What's next |
|---|---|
| Issue #41 was filed and recon traced the current corpus writer, generic augmentation path, tests, and issue #25 collision boundary at `b25436b`. | Phase 1: obtain Codex plan approval, then implement the deterministic training-only composer. |

## Table of contents

- [Phase 1: Contract and deterministic composer](#phase-1-contract-and-deterministic-composer)
- [Phase 2: Fixtures, red controls, and readiness report](#phase-2-fixtures-red-controls-and-readiness-report)
- [Phase 3: Controlled model experiment](#phase-3-controlled-model-experiment)

## Problem and decisions

Needle has abundant Oracle rows but thin governance support, a small work-purpose corpus, and
source-dependent mapper quality. Generic generation would multiply label errors. The smallest safe
step is a standard-library offline composer for already reviewed or rule-grounded seeds. It will
reuse `serialize.to_finetune_row`; generated rows are training-only, while model evaluation remains
blocked on a fresh real holdout. Issue #25 owns its existing sampler, correction manifests, and
evaluation-capacity lane; this branch does not edit or consume them.

The first implementation does not call an LLM. Generator outputs become candidate specification
rows that this command validates. This keeps provider choice outside the canonical data contract and
avoids a new dependency. Debugging follows debug-mantra. Failure is a nonzero exit with no output or
report; there is no retry loop.

## Blast radius and rollback

Current-state radius is the offline Oracle corpus seam: `utils/corpus/serialize.py` writes the exact
trainer row shape and `build_oracle_jsonl.py` consumes real pairs. The proposed command adds one
training-only input contract and one aggregate report. It does not alter the serializer, generic
package augmentation, trainer, hook, taxonomy, checkpoint, export, or release surface.

Undo class is Easy: delete the new command/tests/fixtures and their plan records. Shield: outputs
must be explicitly marked `split: train` and generated; forbidden source identities are rejected.
Tripwire: any validation failure removes temporary output and exits before publishing either the
JSONL or report. Model training is a later phase and stops unless a fresh real holdout exists.

## Phase 1: Contract and deterministic composer

**Goal:** one canonical command converts validated augmentation specifications through the existing serializer.

- [ ] Add a stdlib-only command under `utils/corpus/` with a versioned spec, deterministic ordering, atomic output, and actionable validation errors.
- [ ] Require record/source identity, SHA-256 provenance, taxonomy version, expected label, augmentation kind, generator/config identity, and `train` split.
- [ ] For counterfactual pairs, require exactly baseline/counterfactual roles and prove the declared before→after replacement is the only request-field change.
- [ ] Reuse `serialize.to_finetune_row`; do not create another query or trainer-row serializer.

### Phase 1 — QA checklist

- [ ] Empty, unknown-label, non-training, duplicate-identity, incomplete-pair, and ungrounded rows fail before output exists.
- [ ] A deliberate serializer bypass in the test is observed red.
- [ ] No issue #25-owned audit or manifest file changes.

## Phase 2: Fixtures, red controls, and readiness report

**Goal:** de-identified fixtures demonstrate every supported augmentation kind and a privacy-safe aggregate receipt.

- [ ] Add fixtures for paraphrase, controlled counterfactual, negation/quotation, mixed event, and abstention.
- [ ] Reject exact/normalized duplicate requests and identities present in an optional forbidden-source manifest.
- [ ] Emit only counts, hashes, label/kind distributions, pair completeness, and exclusions; never source text, commands, paths, sessions, or repo identity.
- [ ] Run focused tests, the non-slow suite, and PDDA checks; retain witnessed red then green evidence in the PR.

### Phase 2 — QA checklist

- [ ] Unchanged input/config produces byte-identical JSONL and report.
- [ ] Every new gate has a witnessed failing control.
- [ ] `pytest -q -m "not slow"` and `utils/pdda/pdda.sh run` pass.
- [ ] Status and changelog reflect the measured result, not predicted model benefit.

## Phase 3: Controlled model experiment

**Goal:** decide on an untouched real holdout whether augmentation improves thin labels without broad regression.

- [ ] Wait for mapper-qualified seeds and a new independently labelled real holdout that is disjoint from issue #25 evidence.
- [ ] Freeze real-only, real+paraphrase, and real+targeted-counterfactual arms with identical model, seed, compute, and holdout.
- [ ] Report macro-F1, per-label recall, governance accuracy, abstention precision/recall, calibration, and common-label regressions.
- [ ] Advance only if thin-label gains are material on real data without material broad degradation; otherwise retain the negative result and stop.

### Phase 3 — QA checklist

- [ ] No generated row enters validation or evaluation.
- [ ] The generating model does not grade its own examples.
- [ ] Exact commands, configs, hashes, raw model outputs, and provenance are retained.
- [ ] No runtime deployment or automatic-action authority is inferred from an experimental gain.

