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
Use the reviewed label as the positive and the old sorter label as the hard negative. Exclude rows
whose target depends on multi-action selection, a taxonomy boundary, or an uncertain reference.

## One next action after this milestone

Implement the source-event and separation gate defined by #25. Do not start training until it emits
nonempty private manifests, stable event/session IDs, full input hashes, and zero cross-boundary
session and q1/content overlap.

## Issue #25 — corrected feedback experiment plan

**Observed problem.** The 26-row feedback proposal was written before checking whether an audited
raw call could be joined back to the request/action history the model actually sees. Thirteen rows
match several events in their recorded session; one unique match is the first action and has no q1
history. Replaying the draw against today's Mac Studio source produces 64,335 calls rather than the
frozen 64,050 and different artifacts, so replay does not recover the lost occurrence identity.
Only one of the 12 unique q1 contexts is present in the canonical Studio training corpus.

The second correction is about the objective. `finetune.py` and the MLX port supervise target tokens
with language-model cross-entropy. They do not consume a 44-way class vector, row weight, or named
hard negative. Adding examples to only one arm would also change row count, steps, and the cosine
schedule. The first causal comparison must hold input rows and exposure fixed and change only the
reviewed target.

**Task rating (2026-09-10): `rated 82/55/50/35`.** Priority is high because this is the only current
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

**Dependencies and assumptions.** The Mac Studio frozen corpus is the baseline source; its three
core files are byte-identical to this machine's `corpus-studio` copies. An explicit source namespace
must distinguish Studio and MBP sessions. CLIO can reconstruct requests and decisions, but cannot
replace Claude transcripts because it has no tool-action target. The experiment requires enough new
sessions and reviewed rows to meet a predeclared minimum effect; otherwise its correct outcome is
INCOMPLETE.

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
3. Freeze two pools before labeling: correction candidates drawn only from recoverable canonical
   Studio **training** sessions, and evaluation candidates from sessions excluded from all fitting,
   prior audit, and model-selection evidence. Publish aggregate counts/hashes only.
   -> Expect zero shared sessions and zero exact q1/content overlap; otherwise stop.
4. Predeclare the primary effect and power cap before choosing the evaluation sample. A two-sided
   exact paired test needs roughly 295–623 rows to detect a five-point gain at 80% power when 10–20%
   of paired outcomes disagree; a three-point gain needs roughly 895–1,758. Require at least 1,000
   reviewed rows across at least 30 sessions or explicitly narrow the claim to a pilot. Retain a
   session-resampling sensitivity analysis and do not call it proof of independent sessions.
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
   -> The corrected-target hypothesis is falsified by no primary improvement, a predeclared
   regression-bound breach, or a gain confined to fitting/development rows. Discard the treatment in
   those cases; preference loss requires a separate Costly decision.

**Smallest affected surface.** The first PR changes only existing corpus/audit utilities, their
tests, this plan, Roadmap pointer, and an aggregate receipt. The MLX branch and run are a dependent
campaign after that gate lands. See `doc/recon-25-feedback-experiment.md`.

**Non-goals.** This issue does not repair shell parsing, revise the 44 labels, add preference/DPO
training, merge MLX into main, qualify the native engine, deploy a hook, or interpret the old 26-row
weighted contribution as achievable gain.

**Definition of done.** Stable event/session identities survive mount-prefix relocation; private
manifests are nonempty, immutable, and disjoint; red controls prove the gates fail; arm inputs differ
only in reviewed targets; both MLX artifacts and receipts load; the sealed paired evaluation produces
a ship/discard decision at the predeclared threshold; public artifacts contain no raw prompts,
commands, credentials, or local paths.

## Privacy and retained evidence

Row-level audit files remain under gitignored `data/`. Public receipts contain aggregates and label
pairs. The operator separately authorized existing prompt transcripts to remain public and reported
that prompts do not contain credentials; a credential-pattern scan found no recognized secrets.
