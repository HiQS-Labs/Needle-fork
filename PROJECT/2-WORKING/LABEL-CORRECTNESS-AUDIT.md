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
  - https://github.com/HiQS-Labs/Needle-fork/issues/25
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
| #24 is merged; #25 recon found that the legacy 26 correction judgments do not retain enough identity to produce 26 exact q1 training rows. | Add stable source-event identity and freeze new, disjoint training-correction and evaluation manifests before any model run. |

## Goal

Establish a repeatable estimate of whether the semantic mapper assigns the right label, separately
from coverage, before using those labels for another training decision.

## Current milestone

The frozen `v1.0.0` vocabulary remains unchanged. The existing 399-row audit and its error-cause
classification are reproducible as aggregate evidence. #25 recon falsified the assumption that all
26 correction judgments can be rendered back into exact training contexts from the saved audit.
The next milestone repairs source identity, freezes new private manifests, and only then tests a
matched corrected-target treatment. Taxonomy and mapper changes remain outside that comparison.

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
Those judgments remain evidence for selecting new training-only correction cases, but they are not
reconstructable as a 26-row training overlay. In the matched comparison, Arm A uses each new row's
frozen sorter target and Arm B uses its reviewed target. Exclude rows whose target depends on
multi-action selection, a taxonomy boundary, or an uncertain reference.

## One next action after this milestone

Implement the source-event and separation gate defined by #25. Do not start training until it emits
nonempty private manifests, stable event/session IDs, full input hashes, and zero cross-boundary
session and q1/content overlap.

## Issue #25 — corrected feedback experiment plan

**Verified locally.** The 26-row feedback proposal was written before checking whether an audited
raw call could be joined back to the request/action history the model actually sees. Thirteen rows
match several events in their recorded session; one unique match is the first action and has no q1
history. Replaying the draw against today's Mac Studio source produces 64,335 calls rather than the
frozen 64,050 and different artifacts, so replay does not recover the lost occurrence identity.
Only one of the 12 unique q1 contexts is present in the canonical Studio training corpus.

**Verified from code.** `finetune.py` and the MLX port supervise target tokens
with language-model cross-entropy. They do not consume a 44-way class vector, row weight, or named
hard negative. Adding examples to only one arm would also change row count, steps, and the cosine
schedule. The first causal comparison must hold input rows and exposure fixed and change only the
reviewed target.

**Task rating (2026-09-09): `rated 82/55/50/35`.** Priority is high because this is the only current
Roadmap action and blocks another trustworthy model result. Severity is moderate: the present model
is not shippable, but this task protects private data and produces disposable artifacts rather than
changing a released contract. Appeal is neutral by policy. Cheapness is 35 because two blind audits
and two MLX runs are material even though the code change is narrow. Recent recurrence evidence is
the chain of corrected measurements in #12, #14, #20, and #23; these are related evidence failures,
not four independent incidents with one proven root cause.

**Reversibility:** Easy for additive identity/manifest tooling and private data; Costly for the MLX
campaign because it consumes hours and review effort, although its adapters are disposable. The
rollback is to discard the treatment artifacts and retain the unchanged baseline. No model
architecture, `.cact` format, taxonomy, mapper, native engine, or default dependency changes.

**Verified dependencies.** The Mac Studio frozen corpus is the baseline source; its three core files
are byte-identical to this machine's `corpus-studio` copies. CLIO records prompts and decisions but
does not supply the Claude tool-action target needed by the q1 serializer.

**Hypotheses to test.** An explicit source namespace plus transcript-internal event identity will
survive copies and mount-prefix changes. Correcting targets on matched training contexts will improve
fresh-session top-1 accuracy by at least five percentage points without crossing either protected
subset bound. If the source gate fails or the sample is too small, the outcome is `INCOMPLETE`, not a
model result.

### One ordered execution sequence

1. Extend the existing transcript iterator/extractor and audit sampler with an explicit source
   namespace, a mount-invariant relative-session ID, transcript SHA-256, and stable source-event ID
   from the transcript session/tool-use identity plus action ordinal. Preserve legacy callers.
   -> Expect the same fixture under two mount prefixes to produce identical IDs, two namespaces to
   differ, and a deliberately removed/duplicated event to fail.
2. Add one private manifest command that calls the existing serializer and records session, event,
   q1-input, full-row, and source hashes. It must refuse empty inputs, overwrite, hash drift,
   ambiguous event joins, label/query-version drift, and cross-boundary session or exact q1/content
   overlap. Report within-side duplicates without silently deleting natural repetition.
   -> Expect synthetic overlap, empty input, and mount-prefix mutations to go red; unchanged replay
   must be byte-identical.
3. Freeze the eligible inventories, then choose no evaluation rows until the following decision rule
   is stored in the manifest. Correction candidates come only from recoverable canonical Studio
   **training** sessions; evaluation candidates come from sessions excluded from all fitting, prior
   audit, and model-selection evidence. Publish aggregate counts/hashes only.
   -> Expect zero shared sessions and zero exact q1/content overlap; otherwise stop.
4. Use change in sealed-holdout top-1 accuracy (`Arm B - Arm A`) as the only primary effect. The
   primary inferential rule is a two-sided 95% percentile interval (`alpha = 0.05`) from 10,000
   whole-session resamples at seed `2501`; each resample includes all frozen rows from every selected
   session and computes the row-weighted accuracy change. Promotion requires both a point change of
   at least `+5.00 pp` and a lower interval endpoint above zero. Evaluate exactly 1,000 reviewed rows
   spanning at least 30 sessions, with no session supplying more than 40 rows; a smaller eligible or
   completed sample is `INCOMPLETE`. These counts are eligibility floors, not a prospective power
   claim: the previously calculated 295–623 independent-row requirement does not apply once outcomes
   cluster by session. Report row-level exact McNemar arithmetic only as a descriptive sensitivity,
   never as the promotion test.

   The governance and rare-label subsets are blocking secondary safety gates. Governance membership
   is the frozen taxonomy's governance tier. A rare label has less than 1% support in the frozen base
   training manifest. Each aggregate subset must contain at least 50 gold rows across at least 20
   contributing sessions; less is `INCOMPLETE`. For each subset, resample its contributing sessions
   10,000 times at seed `2501` and compute a one-sided 95% lower confidence bound for its
   row-weighted top-1 change. Promotion requires both lower bounds to be strictly above `-5.00 pp`.
   Top-3, per-label recall, and reviewed-versus-old target margins are descriptive secondary results
   and do not replace the primary rule.
5. Blind-label both frozen samples with two auditors and adjudicate only disagreements. The
   correction set may enter training after its references pass the same completeness/confidence
   gates as #20. The evaluation reference remains sealed until both artifacts and run receipts are
   immutable.
   -> Expect missing, duplicate, extra, invalid-label, or wrong-event answers to fail before output.
6. Build equal-size Arm A and Arm B inputs from identical correction contexts. Arm A uses the frozen
   sorter target; Arm B uses the reviewed target. Set MLX validation split to zero and keep base
   checkpoint, seed, row order, row count, batch/micro-batch, epochs/steps, schedule, QAT plan, and
   memory cap identical. Do not add a `hard_negative` field or a new loss.
   -> Expect a deterministic arm diff containing target/reasoning changes only; any other difference
   blocks training.
7. Train in an isolated full clone of `origin/spike/mlx-finetune`, preserving its no-MLX-on-main
   boundary. Extend its receipt to include full data/checkpoint hashes, seed, optimizer/schedule,
   code commit, and completion state before the paid/time-consuming run.
   -> Expect preflight parity/tests and the memory estimate to pass; a missing hash, zero supervised
   tokens, nonzero exit, incomplete receipt, or artifact load failure stops the campaign.
8. Score both artifacts once on the sealed manifest through identical MLX candidate-sequence
   scoring. Report paired top-1/top-3, both/A-only/B-only/neither, exact McNemar arithmetic,
   session-resampling sensitivity, label support/recall, governance and rare-label bounds, and the
   reviewed-label-versus-old-label sequence margin.
   -> The corrected-target hypothesis is falsified unless every primary promotion condition passes,
   or when either protected subset crosses `-5.00 pp`. Discard the treatment in those cases. A pass
   promotes the recipe only to serving qualification; it does not ship a runtime model. Preference
   loss requires a separate Costly decision.

**Smallest affected surface.** The first PR changes only existing corpus/audit utilities, their
tests, this plan, Roadmap pointer, and an aggregate receipt. The MLX branch and run are a dependent
campaign after that gate lands. See `doc/recon-25-feedback-experiment.md`.

**Verified implementation checkpoint (2026-09-09).** The first-PR gate now emits stable namespaced
session/event identities, verifies every selected event against the hashed source transcript, retains
identity through audit v3, reconstructs legacy canonical-train membership, and rejects overlap with
both namespaced and legacy exclusions. A real private run recovered 20,711 exact canonical training
rows across 257 sessions. It excluded 22,104 matched `(session, step)` rows whose current mapper
rendering differs from the frozen row and 5,929 canonical rows unavailable in the current snapshot.
The same run found zero exact q1/content overlap for 2,806 MacBook candidates against all 74,428
frozen canonical Studio pairs. The MacBook candidates span only 17 eligible sessions, so the
experiment is `INCOMPLETE` against the 30-session floor and no training started. See
`TESTS-RESULTS/2026-09-09-issue-25-source-gate/`.

**Non-goals.** This issue does not repair shell parsing, revise the 44 labels, add preference/DPO
training, merge MLX into main, qualify the native engine, deploy a hook, or interpret the old 26-row
weighted contribution as achievable gain.

**Definition of done.** Stable event/session identities survive mount-prefix relocation; private
manifests are nonempty, immutable, and disjoint; red controls prove the gates fail; arm inputs differ
only in reviewed targets; both MLX artifacts and receipts load; the sealed paired evaluation produces
a promote/discard/`INCOMPLETE` decision from the numeric rules above; public artifacts contain no raw
prompts, commands, credentials, or local paths.

## Privacy and retained evidence

Raw transcripts, prompts, rendered rows, row-level labels, and local paths remain under gitignored
`data/` or outside the repository. Public receipts contain aggregate counts, hashes, metrics, and
label-pair counts only after a credential-pattern and local-path scan. The operator's general
permission to discuss prompts publicly does not make the corpus itself a tracked artifact.
