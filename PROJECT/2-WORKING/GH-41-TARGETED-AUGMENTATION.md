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
| The composer and five-kind fixtures passed final Codex review, 16 focused tests, and 400 non-slow tests in the declared Python 3.12 test/train environment. | Analyze the readiness evidence, then preregister Phase 3 only after a fresh real holdout and the assembly/preflight seam exist. |

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

### Owned and reserved paths

GH-41 owns `utils/corpus/build_grounded_augmentation.py`,
`tests/test_grounded_augmentation.py`, `tests/fixtures/gh41/`, and private run directories beneath
`data/grounded-augmentation/`. It may read only a newly supplied reviewed-seed file and optional
forbidden-ID manifest passed explicitly on the command line.

Issue #25 retains `utils/corpus/sample_for_audit.py`, `score_audit.py`,
`build_experiment_manifest.py`, `analyze_audit_causes.py`, their audit/corpus-identity tests, and all
existing private audit/correction/evaluation artifacts under `data/`. GH-41 neither reads nor writes
those paths. A later operator-created forbidden-ID manifest may contain stable source IDs or hashes
exported from #25 without exposing #25 files to this lane.

### Normative input and output contract

The reviewed-seed JSONL is the trust boundary. Each canonical seed contains `source_id`,
`source_kind` (`human` or `rule`), `reviewed_by`, `taxonomy_version`, `label`,
`recent_user_request`, and `prior_actions`; it does **not** contain its own digest. `source_sha256` is
SHA-256 over that complete UTF-8 seed object encoded with sorted keys, compact separators, and no
trailing newline. The candidate file references the seed ID and digest; the composer loads the
separate seed file, recomputes the digest, and rejects disagreement. The byte-drift control changes
one hashed seed field while retaining the candidate's prior digest.

Every candidate also contains unique `record_id`, `split: train`, `generated: true`, `kind`,
`generator`, and `config_sha256`. Output is a **generated-only** trainer JSONL plus a manifest that
binds every emitted row hash to its seed/candidate identities. Real rows are not mixed here. This
initial composer proves marking and separation at composition time; it does not claim to police a
later trainer invocation after the canonical serializer intentionally drops provenance metadata.
Phase 3 therefore remains blocked on a separately reviewed assembly/preflight command that consumes
this manifest plus the real holdout, proves disjoint row/source hashes, emits the exact training
command with `--val-split 0`, and rejects any generated hash in validation or evaluation.

Canonical request normalization is Unicode-preserving whitespace collapse, identical to
`serialize._clean`; its SHA-256 is the duplicate key. Duplicate keys are rejected across all
candidates and optional real-source keys. Sorting is by `record_id`, so reversed input order is
byte-identical. A digest collision between unequal canonical bytes is a hard failure.

A counterfactual `pair_id` contains exactly one `baseline` and one `counterfactual`. Both records
have byte-identical source ID/digest, prior actions, generator/config, taxonomy version, and every
candidate field except record ID, role, expected label, request, and `controlled_change`. Replacing
the declared nonempty `before` span exactly once in the baseline request with `after` must produce
the counterfactual request; no other request byte may change.

## Blast radius and rollback

Current-state radius is the offline Oracle corpus seam: `utils/corpus/serialize.py` writes the exact
trainer row shape and `build_oracle_jsonl.py` consumes real pairs. The proposed command adds one
training-only input contract and one aggregate report. It does not alter the serializer, generic
package augmentation, trainer, hook, taxonomy, checkpoint, export, or release surface.

Undo class is Easy: delete the new command/tests/fixtures and their plan records. Shield: outputs
must be explicitly marked `split: train` and generated; forbidden source identities are rejected.
Tripwire: the command builds `training.jsonl`, `manifest.json`, and `report.json` inside a sibling
staging directory, closes and fsyncs them, then atomically renames the one directory to a new,
nonexistent immutable run path. Any validation/fault before that rename removes only the proven
staging directory, leaving no final run. Model training is a later phase and stops unless a fresh
real holdout exists.

## Phase 1: Contract and deterministic composer

**Goal:** one canonical command converts validated augmentation specifications through the existing serializer.

- [x] Add `utils/corpus/build_grounded_augmentation.py`, a stdlib-only command with the contract above, deterministic ordering, immutable atomic run-directory publication, and actionable validation errors.
- [x] Require a separately reviewed seed file and recompute its canonical SHA-256; require record/source identity, taxonomy version, expected label, augmentation kind, generator/config identity, and `train` split.
- [x] For counterfactual pairs, require exactly baseline/counterfactual roles and prove the declared before→after replacement is the only request-field change.
- [x] Reuse `serialize.to_finetune_row`; do not create another query or trainer-row serializer.

### Phase 1 — QA checklist

- [x] `test_empty_input_refuses_without_run`, `test_non_train_candidate_refuses`, `test_seed_byte_drift_refuses`, `test_counterfactual_pair_invariants`, and duplicate/identity tests assert the exact error and absence of a final run.
- [x] The valid fixture asserts nonzero input/output counts before hashes/distributions; monkeypatching `serialize.to_finetune_row` to a noncanonical row makes the contract test fail before restoration.
- [x] No issue #25-owned audit or manifest file changes.

## Phase 2: Fixtures, red controls, and readiness report

**Goal:** de-identified fixtures demonstrate every supported augmentation kind and a privacy-safe aggregate receipt.

- [x] Add fixtures for paraphrase, controlled counterfactual, negation/quotation, mixed event, and abstention.
- [x] Reject exact/normalized duplicate requests, duplicate record/source identities where forbidden, unequal bytes with the same digest, and identities present in an optional forbidden-source manifest.
- [x] Emit only counts, hashes, label/kind distributions, and pair completeness; never source text, commands, paths, sessions, or repo identity.
- [ ] Run focused tests, the non-slow suite, and PDDA checks; retain witnessed red then green evidence in the PR.

### Phase 2 — QA checklist

- [x] Unchanged input/config and reversed candidate ordering produce byte-identical JSONL, manifest, and report.
- [ ] Every new gate has a witnessed failing control.
- [x] A fault injected after staging but before the directory rename leaves no final run.
- [ ] `pytest -q -m "not slow"` and `utils/pdda/pdda.sh run` pass.
- [x] Status reflects the measured result, not predicted model benefit; no changelog entry is required for this Easy, additive offline change.

## Phase 3: Controlled model experiment

**Goal:** decide on an untouched real holdout whether augmentation improves thin labels without broad regression.

- [ ] Before any training, add and review an experiment addendum freezing minimum real-holdout size, label/session/repository/time allocation, commands, primary metric, uncertainty method, improvement and regression thresholds, and stop rule.
- [ ] Add and review the bounded assembly/preflight command described above, including a red test that a generated row hash placed in validation/evaluation refuses before training and a command assertion that `--val-split 0` is present.
- [ ] Wait for mapper-qualified seeds and a new independently labelled real holdout that is disjoint from issue #25 evidence.
- [ ] Freeze real-only, real+paraphrase, and real+targeted-counterfactual arms with identical model, seed, compute, and holdout.
- [ ] Report macro-F1, per-label recall, governance accuracy, abstention precision/recall, calibration, and common-label regressions.
- [ ] Apply only the preregistered addendum thresholds; otherwise retain the negative or inconclusive result and stop.

### Phase 3 — QA checklist

- [ ] No generated row enters validation or evaluation.
- [ ] The generating model does not grade its own examples.
- [ ] Exact commands, configs, hashes, raw model outputs, and provenance are retained.
- [ ] No runtime deployment or automatic-action authority is inferred from an experimental gain.
