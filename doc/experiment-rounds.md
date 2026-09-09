# Repeatable experiment rounds

Implements the first executable slice of [#14](https://github.com/HiQS-Labs/Needle-fork/issues/14).
The audit is an offline evidence checker, not an automatic scientific reviewer.
It imports no model runtime, makes no network requests, and never starts training.

## Contract shared by every phase

Freeze the question, population/prediction boundary, input manifest, expected size,
primary comparisons, baseline selection, falsifier, resource cap, and decision rule
before measuring. Capture results separately from interpretation. After collection,
pin the resulting receipt files in an analysis configuration. Do not relabel this
post-collection configuration as a preregistration; retain the original protocol too.
A changed protocol, parser, artifact, or selection rule creates a new round.

Each round produces: the frozen protocol, immutable raw receipts, an audit report,
and a short reviewed decision. Private inputs stay in ignored `data/` or private
external storage. Public issues receive sanitized aggregate evidence and synthetic
controls, never raw transcripts. Failed and incomplete runs are retained.

Use three outcomes: PASS (the named check passed), FAIL (contradiction or invalid
input), INCOMPLETE (missing evidence or a review not performed). A passing structural
check does not prove a causal explanation. Keep model outcome separate: useful gain,
no demonstrated gain, or inconclusive. No demonstrated difference is not equivalence.

Gates carry a **kind**. A *deterministic* gate is one a script can decide; a *review*
gate is one only a person can close. G3, G5 and G6 are review gates and are hardcoded
INCOMPLETE, so the overall disposition can never be PASS and exit 0 is unreachable while
they are open — that is deliberate, not a bug. `deterministic_status` in the report
carries the disposition the script actually earned, so a permanently-open review gate
cannot hide either a clean arithmetic result or a broken one.

**FAIL outranks INCOMPLETE when routing the next action.** A contradiction is a defect;
a missing receipt may be irrecoverable. Routing by gate order alone always named the
earliest non-PASS gate, and G0 is INCOMPLETE on every legacy arm for want of run
metadata — so a genuine arithmetic contradiction in G4 was never reported as the thing
to fix. `blocked_gates` lists both classes separately.

**Exact query overlap between the fitting and evaluation files is rejected as a declared
protocol choice, not as proof of copying.** Two independent sessions can legitimately
produce the same observable history, so equal inputs are not evidence that anything was
copied. Rejecting them is a conservative restriction that pins the estimand to
*generalisation to unseen inputs*. It is the current default because it is conservative
and trivially reversible — **reopen it before any round whose estimand is deployment
performance on naturally recurring inputs**, where excluding repeats would bias the
answer. Recorded dissent, AgentChorus #729301. No fuzzy or near-duplicate matching:
source-event identity is the stronger next guard if one is ever needed.

**The comparator's fitting data must be disjoint from the evaluation manifest, and the
audit measures it rather than trusting the filename.** Selecting a baseline from data it
is later scored against is the error behind a withdrawn #12 claim (LESSONS-LEARNED #2);
this corpus also carries ~36% duplicate holdout rows and ~25% duplicate training rows,
so accidental overlap is a live hazard, not a theoretical one. Overlap is a G0 **FAIL**,
checked at both exact-line and query identity. Measured on `frozen-200` against
`oracle-train.jsonl`: 0 of 200 by either test.

## Offline audit

Run from the repository root, using any supported Python with the standard library:

```sh
python3 spike/mlx/audit_round.py --config /private/round.json --outdir /private/new-report
```

The output directory must not already exist. It contains `round.json`, `report.json`,
and `SUMMARY.md`. Exit codes are **0 PASS, 1 FAIL, 2 INCOMPLETE**. An existing output
directory raises an error and remains intact. Repeat using a different directory;
identical configuration and evidence produce byte-identical reports in the same
Python environment. Floating-point last bits across Python/platform versions are
not promised identical; environment versions belong in the execution receipt.

Example configuration (paths resolve relative to this JSON file). Replace every
placeholder with an actual full SHA-256, e.g. from `shasum -a 256 FILE`:

```json
{
  "format_version": 1,
  "round_id": "oracle-serving-round-N",
  "question": "Does the saved paired comparison reproduce?",
  "population": "Frozen diagnostic rows; session independence unverified",
  "falsifier": "Missing/mismatched rows or raw verdict disagreement",
  "time_cap": "Offline audit only; no model inference",
  "manifest": {"path": "manifest.jsonl", "sha256": "FULL_SHA256", "expected_n": 200},
  "taxonomy": {"path": "labels-v1.json", "sha256": "FULL_SHA256"},
  "training": {"path": "training.jsonl", "sha256": "FULL_SHA256"},
  "arms": [
    {
      "name": "candidate",
      "runtime": "mlx",
      "path": "candidate/rows.jsonl",
      "sha256": "FULL_SHA256",
      "declared": ["read_file", "run_script", "search_code", "apply_patch", "git_inspect"],
      "run_metadata": {"path": "candidate/run.json", "sha256": "FULL_SHA256"}
    }
  ],
  "comparisons": [["candidate", "training_majority"]]
}
```

For a legacy arm, omit unavailable `run_metadata` instead of fabricating it; the
report returns INCOMPLETE. Declaration lists inherited from old issue text must be
labeled as inherited in the review. A supplied list is not proof of what ran.

The audit verifies hashes, count/identity/gold alignment, canonical label/status
consistency, available raw-output replays, metadata links, and paired arithmetic.
The baseline is fitted on training labels with lexical tie-breaking. Errors and
abstentions remain in full-task denominators. It reports reachable-subset counts
separately. Exact two-sided McNemar p-values are explicitly conditional on independent
row pairs; they do not certify that sampling assumption.

### What is enforced, reviewed, or unimplemented

Do not read the issue's requirement table as a description of shipped behaviour. Today:

| Requirement | State |
| --- | --- |
| Input pinning, hashes, expected count, protocol fields | **enforced** by G0 |
| Baseline/evaluation disjointness | **enforced** by G0 (exact + query identity) |
| Row identity, gold alignment, status/prediction legality | **enforced** by G1 |
| Raw-output replay to the saved verdict, scoring false-positive rejection | **enforced** by G2 where raw exists; INCOMPLETE where it does not |
| Paired contingency counts and exact McNemar arithmetic | **enforced** by G4 |
| Immutable output, overwrite refusal, deterministic replay | **enforced** by the CLI |
| Served-token semantics and schema-span accounting (G3) | **manual review only** |
| Session dependence, multiplicity, confidence intervals, power (G5) | **manual review only**; family size is reported, no adjustment is applied |
| Scientific interpretation, dissent, next-action choice (G6) | **manual review only** |
| Query-identity coverage, so a zero overlap is not mistaken for absent evidence | **enforced** by G0; a partial test is INCOMPLETE |
| Session provenance recovery and cluster-robust sensitivity | **exploratory only** — `session_clustering.py` is not a gate and cannot close G5 |
| Effective run provenance (engine binary, session IDs, tokenizer identity) | **unimplemented** — recorded as explicitly null, never inferred |
| Overclaim detection in prose | **unimplemented**, and deliberately so — a word filter cannot certify a scientific claim |

**Current deliberate limits:** G3 (served token semantics), G5 (population inference),
and G6 (scientific review/decision) remain INCOMPLETE in this command. There is no
flag to assert them green. Complete these in an evidence-linked reviewed decision;
the checker must not manufacture a PASS from a filename or reviewer assertion.
No confidence interval or power estimate is currently implemented. Before drawing
population conclusions, choose and document an appropriate uncertainty procedure,
recover session/family provenance, and address multiplicity and reused test data.
The first blocked prerequisite is emitted as the next repair/review target. A decision
to stop rather than repair is valid; this is not an infinite repair loop.

## New evaluation receipts

The existing `spike/mlx/run_eval.py` flags remain available, but output layout is now:

```text
data/spike-mlx/logs/frozen/<runtime>-<tag>/
  run.json       # settings, full input/source hashes, completion state
  rows.jsonl     # incrementally retained verdict and complete raw output
  summary.json  # created only after evaluation completes
```

Use a fresh tag for each invocation. Reusing a tag refuses overwrite. A crashed run
retains an incomplete `run.json` and any rows collected; it cannot pass as a full run.
Missing binary/session provenance is explicitly null. The recorded local tokenizer
file hash does not attest which tokenizer the closed native engine actually loaded.
Capture review must establish those remaining identities before claiming parity.

**Historical note, so the scorer's own history is not misremembered.** At `e9e994f` the
scorer selected the **first** `<tool_call>` block: it had no multiple-*block* check, and its
`multiple_calls` status covered multiple *calls inside one block*. Its real gaps were
invalid argument shapes, duplicate JSON keys, and a trailing unclosed block, all of which
it scored `ok`. A later claim that it already rejected multiple blocks was wrong and was
withdrawn in #14.

The scorer is specifically for the existing **parameterless Oracle** label contract:
omitted arguments or `{}` are allowed; nonempty/nonobject arguments, duplicate JSON
keys, multiple calls/blocks, incomplete blocks, and labels only mentioned in reasoning
are not valid predictions. A future enum tool has a different schema and needs an
explicit versioned scorer change and controls. Do not silently use this scorer for it.
Historical saved scores remain unchanged; replay raw evidence with a named scorer
version where available. Missing historical raw output is irrecoverable from a label.

## Native trace collection

Only when a bounded native probe is justified by the reviewed next action:

```sh
.venv-mlx-spike/bin/python spike/mlx/kv_verify.py --outdir data/spike-mlx/kv-round-UNIQUE --counts 5 6 10 44 --rows 0 1 7
```

Each child has a timeout (default 60 seconds), command, input hashes, row ID, full
stdout/stderr, exit/timeout outcome, and all prefix/turn token-ID arrays. The index
returns INCOMPLETE if any capture lacks required lifecycle/events. No stdout/stderr
concatenation is treated as chronological evidence. The `top5` logit field is not parsed
as retrieval. Capture PASS is only a capture check: tokenizer decoding, event semantics,
wrapper/schema span accounting, and completeness of the native debug facility still
require review. The command does not run as part of offline audit/tests.

A finite sample of decoded five-schema turns supports exactly those samples. Different
schema lengths can change token count without changing tool count. A partial retrieval
sample must report decoded/expected counts and missingness; it cannot establish a full
population reachability ceiling. Do not infer which cause is absent from first-token
agreement or from a different trained artifact succeeding.

## Review and next-step generation

The report is the input to review, not an LLM-written replacement for evidence. Record
claim ID, status (verified-by-author/inherited/hypothesis), exact receipt/field, scope,
falsifier, and superseded claims. The reviewer must identify any gap between the
measurement and its explanation, and retain disagreement even if the discussion closes.
For the current phase preserve D7 as unreproduced; do not certify QAT/numerical parity
from artifact rankings alone.

Choose **one** next action in order: repair the first decision-relevant prerequisite,
run the cheapest bounded discriminator that can change the decision, or stop. Record
why it wins over the alternatives, outcomes that would falsify the bet, and a time/run
cap. Review is capped at two revision rounds; unresolved blockers go to the maintainer
under SOP §4 or produce an explicit inconclusive stop. No auto-retrain, deployment,
holdout expansion, or retries selected for good answers.

## Where these tests live

`tests/test_experiment_rounds.py` sits in the repository test directory, which
`pyproject.toml` sets as the pytest path and `.github/workflows/release.yaml` runs as the
PyPI release gate. The modules under test live in `spike/mlx/`, outside the packaged
`needle*` tree. They import only the standard library, so this does **not** make MLX a
dependency of `main`, and no module name collides with `needle/`. The test module skips
at collection if `spike/mlx/` is absent, so a branch without the spike cannot take the
release train red. Whether spike-scoped tests belong in `tests/` at all is a maintainer
call under SOP §4, not something this file settles.

## Verification

```sh
.venv-mlx-spike/bin/python -m pytest -q tests/test_experiment_rounds.py
.venv-mlx-spike/bin/python -m pytest -q -m "not slow"
```

Synthetic controls corrupt copies, not original artifacts. Controls cover empty/hash-
mismatched manifests, missing/duplicate/wrong-gold rows, raw/verdict disagreement,
known scoring false positives, mislabeled debug logits, failed/timed-out children,
hand-calculated paired statistics, and immutable report output. Retain the failing
control receipt and subsequent passing check; a checklist alone is not proof.
