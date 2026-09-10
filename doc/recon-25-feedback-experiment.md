# Recon Map — #25 reviewed-feedback experiment

Commit: `ef890052461f2bce8c22b5af1b0ca1ac8e7bc804` · Mode: source reads + private aggregate probes
· Lanes: data, training, evaluation/operations

## Subject and change class

The subject is the path from private Claude transcript events to q1 training rows, a reviewed
correction treatment, and paired MLX evaluation. This is a cross-module data-contract change before
an isolated training campaign. Model architecture, export numerics, the native engine, and the
frozen label vocabulary are outside the first change.

## The seams

| Seam | Location | Crosses | Breaks if |
| --- | --- | --- | --- |
| Transcript event extraction | `utils/corpus/extract_claude_transcripts.py:43-77,107-141` | Private JSONL → session/action sequence | A source event cannot be identified after a mount or copy |
| Session split | `utils/corpus/extract_claude_transcripts.py:109-119` | Source path → train/holdout | The same transcript path gets a different mount prefix |
| Audit draw | `utils/corpus/sample_for_audit.py:77-96` | Raw call → blind sample + held-back label | Event ordinal/tool-use identity is discarded |
| Training serializer | `utils/corpus/serialize.py:74-116` | Request/history/label → q1 row | A correction lacks the exact preceding context |
| Training loader | `needle/model/finetune.py:194-251` | JSONL → token IDs and loss mask | A made-up `weight` or `hard_negative` field is silently ignored |
| MLX trainer | `origin/spike/mlx-finetune:spike/mlx/train_lora.py:120-149,211-248,321-392` | Frozen rows/config → adapter + receipt | Arms change row count, validation split, schedule, seed, or hashes |
| MLX scorer | `origin/spike/mlx-finetune:spike/mlx/eval_oracle.py:54-68,114-203` | Frozen rows/artifact → label ranks | Reservoir draws differ, identities are omitted, or outputs overwrite |
| Paired analysis | `origin/spike/mlx-finetune:spike/mlx/audit_round.py:41-63,104-142,157-255` | Aligned predictions → paired result | Rows/gold/config differ or session dependence is hidden |

## Call paths in

`~/.claude/projects/**/*.jsonl` → `iter_steps` → extractor pair loop →
`serialize.to_finetune_row` → private Oracle JSONL → `finetune.load_jsonl` → MLX token-level
cross-entropy → adapter → per-label sequence scoring → aligned paired comparison.

The current audit takes a second route: transcript tool-use blocks → `measure_taxonomy.iter_calls` →
`sample_for_audit.draw` → blind auditors/adjudicator → `analyze_audit_causes`. It retains the session
path and rendered call, but not the source event required to rejoin the first route.

## State

- The Mac Studio corpus under the mounted historical checkout and this machine's
  `data/corpus-studio` copy are byte-identical: 74,428 pairs, 48,744 train rows, 25,684 holdout rows.
  Full SHA-256 equality was verified for all three files.
- The frozen audit has 399 rows across 83 recorded sessions and 26 high-confidence correction
  judgments. Only 13/26 have one exact session/tool/rendered-text match; one is a first action, so
  only 12 form a unique q1 context. Only one of those contexts occurs in canonical Studio training.
- Replaying the sampler against the current mounted source fails: 64,335 renderable calls now versus
  the frozen 64,050, with different population, allocation, sample, and sorter hashes.
- Current MBP transcripts produce 2,806 q1 pairs from 17 usable sessions. Aggregate probes found no
  exact q1, full-row, or normalized pair-content overlap with the frozen Studio corpus. That is a
  candidate pool, not a labelled final holdout.
- Raw transcripts, audits, rendered rows, and checkpoints remain private and gitignored. Public
  receipts contain hashes, counts, configuration, and aggregate results only.

## Contracts

- `serialize.to_finetune_row` is the single q1 writer; a correction builder must call it rather than
  reproduce the chat template.
- `labels-v1.json` / taxonomy `v1.0.0` remains frozen during this comparison.
- Training is generative token-level cross-entropy, not a 44-class head. A corrected target removes
  supervision for the old label and adds token-level competition; it is not a named sequence-level
  hard-negative loss.
- MLX stays optional and off main's runtime dependency surface. Campaign execution uses the existing
  `origin/spike/mlx-finetune` implementation in an isolated clone after the data gate lands.
- Session separation and exact model-input/content separation are measured independently. Duplicate
  natural inputs within one side are reported; the predeclared test rejects cross-boundary overlap.

## Build, failure, and rollback today

The main non-slow suite is the merge gate. New identity and overlap assertions require witnessed red
controls. A failed or incomplete data gate stops before training. MLX training is isolated, uses its
existing memory preflight, and writes disposable adapters under ignored `data/`. Rollback is deleting
generated private artifacts and reverting additive tooling; no checkpoint format or release contract
changes.

## Unknowns

| Unknown | Why it matters | What settles it |
| --- | --- | --- |
| At least 1,000 reviewable rows across 30 eligible fresh sessions, plus protected-subset support | Row count alone cannot establish power under session clustering | Freeze the inventory and report session sizes; fewer rows/sessions makes the experiment `INCOMPLETE`, and the final session-resampled interval rather than an independent-row calculation gates the fixed five-point claim |
| Stable namespace values across machines | Relative paths can collide between different sources | Require an explicit non-secret source namespace in each manifest and test cross-namespace noncollision |
| Exact recoverability of the 13 ambiguous legacy audit rows | Guessing would fabricate q1 context | No current evidence can settle it; exclude them unless an older immutable source snapshot reproduces the full audit |
| Best correction exposure | Too little has no effect; too much can overfit | One predeclared matched-control treatment, followed by fresh evaluation; no tuning against the holdout |

## Current-state radius

The first change reaches private transcript extraction, corpus/audit manifests, their tests, and
public aggregate receipts; later campaign work reaches only the isolated MLX spike and disposable
adapters. Runtime SDK users and native-engine behavior do not change.
