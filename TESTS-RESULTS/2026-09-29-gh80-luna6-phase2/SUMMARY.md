# GPT 6 Luna Phase 2: no observed quality improvement

**GPT 6 Luna Medium scored 43/48 and 41/48 (87.50%, grade B), versus historical GPT 5.6 Luna Medium 44/48 and 43/48 (90.625%, grade B).** The observed mean difference is **−3.125 percentage points**. Both candidate calls completed. This is a repeated-fixture historical comparison, not evidence of a general model regression.

Canonical issue: [Needle #80](https://github.com/HiQS-Labs/Needle-fork/issues/80). Predecessor: [#13 Phase 2](https://github.com/HiQS-Labs/Needle-fork/issues/13#issuecomment-5608848865). Run date: September 29, 2026 Pacific / September 30 UTC.

| Measure | GPT 5.6 Luna Medium (September 9) | GPT 6 Luna Medium (this run) |
|---|---:|---:|
| Full scores, out of 48 | 44 / 43 | 43 / 41 |
| Mean score | 90.625% | 87.500% |
| Fixture grade | B | B |
| Exact verdicts, out of 12 | 11 / 11 | 12 / 10 |
| Relevant citation points, out of 12 | 12 / 12 | 12 / 12 |
| Semantic points, out of 24 | 21 / 20 | 19 / 19 |
| Critical false SUPPORTED verdicts | 0 / 0 | 0 / 0 |
| Observed candidate tool events | 0 / 0 | 0 / 0 |
| Client wall seconds | 29.954 / 33.039 | 29.099 / 25.162 |
| Actual billed cost | Not measured | Not measured |

Historical timing rounded from retained original receipts; timings include CLI/runtime overhead and do not establish p95 or a model-only speed difference. Mean new wall time 27.131s. No current pricing assumption or subscription-to-API billing equivalence is used.

## What improved and what did not

- **Preservation:** both new answers recognize divergent branches and local-only commits without suggesting reset. Historical r2 lost a point for offering reset without preservation; new r2 gains that point.
- **CI uncertainty:** new r1 correctly says UNKNOWN when the only passing check belongs to the old head. New r2 repeats the historical CONTRADICTED label while accurately explaining the evidence gap. One verdict point improves across the two calls.
- **Classifier explanation:** both new G02 answers describe generic classification changes without explaining command invocation versus argument text, wrappers/subcommands, and focused executed regression evidence sufficiently. Four points lost relative to the historical pair.
- **Deployment uncertainty:** new r2 says CONTRADICTED while explaining that external deployments are unobserved. The correct verdict is UNKNOWN; semantic reasoning remains credited. One verdict point lost.
- **Persistent omissions:** both still omit the issue #2 blocker in the planning summary and the actual primary-checkout/AgentChorus change scope in PR526. New r2 mentions the retired CPU path, but does not fully satisfy the frozen planning requirement.
- **Grounding and containment:** all citations are valid and relevant to the claims made. Both return one complete 12-case answer, make no false critical all-clear, and show no tool events or executed mutation claims. Citation correctness alone does not compensate for missing analysis.

## Per-case scores

| Case | 5.6 r1 | 5.6 r2 | 6 r1 | 6 r2 |
|---|---:|---:|---:|---:|
| G01 | 2 | 2 | 2 | 2 |
| G02 | 4 | 4 | 2 | 2 |
| G03 | 3 | 3 | 3 | 3 |
| G04 | 4 | 4 | 4 | 4 |
| G05 | 3 | 3 | 4 | 3 |
| G06 | 4 | 4 | 4 | 4 |
| G07 | 4 | 4 | 4 | 4 |
| G08 | 4 | 3 | 4 | 4 |
| G09 | 4 | 4 | 4 | 4 |
| G10 | 4 | 4 | 4 | 4 |
| G11 | 4 | 4 | 4 | 4 |
| G12 | 4 | 4 | 4 | 3 |

## Scoring review and sensitivity

The original rubric/key/grader are unchanged. An independent GPT 6 Astra Medium call reviewed anonymized A/B responses with candidate identity, prior scores and coordinator scores withheld. It proposed 40/36; the coordinator's saved initial review proposed 43/42. Final reconciled scores are **43/41**, adjudicated by the coordinator, not claimed as unanimous reviewer agreement.

[Per-case adjudication](review/final.json) explains every difference. Exact-SHA check requests, stale approval, safe post-revert inspection, the zero-retry boundary, and correct deployment uncertainty prose receive the same semantic-equivalence treatment as the historical accepted answers. The reviewer correctly identified an additional G02 r2 omission, accepted in the final score. Review transcripts and both initial reviews are retained. These are judgment-based fixture grades; different strictness can move the letter, so the raw answers and dimensions matter more than the B.

G05 was already known to be ambiguous. The official UNKNOWN key is preserved. Excluding only its verdict point gives **88.298% (83/94)** for GPT 6 versus **92.553% (87/94)** historically: the no-improvement conclusion survives. This is sensitivity analysis, not a replacement grade.

## Method, identity and limitations

- Exactly two sequential fresh requests selected `gpt-6-luna`, `model_reasoning_effort="medium"`, via Codex CLI 0.159.1, original adapter plus model-ID-only substitution, and existing consult capture. Both completed without repair, retry, or model substitution. Separate reviewer call is not a third candidate run.
- The explicit full prompt is byte-identical to historical Luna: SHA-256 `1863e246efa8215d944cf4c8a49753a3b0b8710ad6a5ee1b3c1bbfe51f472003`. Packet SHA-256 `dc19001fd5d1b4ad68f96516edb4c9b4538364689410450c5d33513e8ee5431b`. All 12 cases and 19 evidence sources are unchanged.
- Inputs were committed before inference at `714628a` and `59809eb`. Key and old outputs stayed outside the minimal candidate checkout until both requests finished. Candidate checkout contained only QUESTIONS.md and packet.json. The public source snapshots remain September 9 observations.
- **Ambient context is not identical:** the old run had XYZ repository instructions; the new run used a minimal checkout. CLI/runtime/system context may also have changed. `--ignore-user-config` does not establish absence of all global instructions. Historical input counts were about 32.7K; new counts about 27.9K. Identical explicit prompts do not make this a controlled model-only experiment.
- Requested model/effort and successful CLI completion are recorded; no independent backend model attestation is emitted. Both new calls report zero reasoning-output tokens despite requesting Medium. Do not infer that Medium was ignored or that a different model ran from that counter alone.
- These 12 previously seen development fixtures, repeated twice, are not 24 independent held-out cases. No contemporaneous 5.6 control, generalization test, real next-action prediction, always-on readiness or deployment qualification was measured.
- Actual billed cost is unavailable. No current rate or inferred billing estimate is presented.

## Token receipts

| Counter | r1 | r2 |
|---|---:|---:|
| Input | 27,901 | 27,897 |
| Cached input (subset) | 7,936 | 7,936 |
| Output | 1,387 | 1,197 |
| Reasoning output (reported) | 0 | 0 |

## Verification and reproduction

[Artifact checks](verification/artifacts.json) confirm 12 nonempty case IDs, both frozen prompts, unchanged input hashes, distinct threads, one raw answer per run matching parsed JSON, complete receipts and zero candidate tool events. [Original grader controls](verification/grader-controls.json) include a positive example plus witnessed rejection of empty, duplicate, missing, flipped, invented-citation and critical-false-support mutations. Repository preflight: **545 passed, 7 skipped, 11 deselected** in an isolated Python 3.12 environment with declared test/train extras; no runtime source changed. Initial missing-dependency failures are recorded in [environment notes](verification/environment-notes.md).

Regrade the retained answers from this directory with `python3 grade.py expected.json runs/r1-answer.md` and repeat for r2; verify controls with `python3 grade.py expected.json --controls`. These scripts score structure/verdicts; semantic points require source review. [Execution provenance](execution/provenance.json), raw [r1](runs/r1-events.jsonl) / [r2](runs/r2-events.jsonl), receipts, full prompts, the original model adapter, and the actual run driver are retained. The driver records this machine's original paths; resolve the relay-xyz harness and adjust those paths for another machine. Do not put expected.json or historical outputs in a new candidate checkout.

**Outcome:** completed negative comparison. No prompt tuning, new model call or product promotion follows automatically.
