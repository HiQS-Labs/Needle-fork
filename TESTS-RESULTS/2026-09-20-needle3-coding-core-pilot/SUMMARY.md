# Needle 3 six-action coding-core pilot — 2026-09-20

Rerun of the [#42](https://github.com/HiQS-Labs/Needle-fork/pull/42) pilot on upstream Needle 3
(Cactus 3, `cactus-needle==3.0.1`), with the six labels presented as one extraction tool carrying a
six-value enum. Tracking issue: [#66](https://github.com/HiQS-Labs/Needle-fork/issues/66). Branch
`experiment/needle3-pilot`. Plus one additive arm: Jev (`jev-1.13.0`) zero-shot on the same holdout,
the [#68](https://github.com/HiQS-Labs/Needle-fork/issues/68) "zero-shot baseline generator" use.

## Decision

**Stop this arm at the pre-registered falsifier.** Needle 3, fine-tuned the cheap way upstream ships,
scores **28% top-1** on the frozen 100-row holdout — below the **42%** line (Markov-1 37% + the
standing +5pp rule) and below Markov-1 itself. The new base model does not reverse #42's negative
result; it reproduces it almost exactly (Needle 2: 27%). Per the contract: no tuning, no synthetic
balancing, no larger run, no serving spike.

Jev zero-shot on the same rows scores **21%**, below every trivial baseline. Neither a fine-tuned
tiny model nor a hosted zero-shot decision model beats a first-order transition table on this task.

## Bet and falsifier

- Bet: a larger, laddered base with a classification-shaped output beats a first-order transition
  table on the same holdout by a margin that survives noise on 100 rows.
- Falsifier: Needle 3 top-1 below 42%. **Triggered** (28%).
- Reversibility: Easy. Additive branch, ignored data directory, `oracle/labels-v1.json` unchanged,
  no release-surface change on `main`.

## Inputs

- Base code: fork `main` `f7c7047` merged with upstream `cactus-compute/needle` `94df999`
  (v3.0.1 + one README commit); `needle/` is upstream plus the fork's two #8 hunks (`git diff
  94df999 -- needle/` = 34 insertions in `cli.py` and `model/finetune.py`, nothing else).
- Base weights: `needle3.safetensors` from `Cactus-Compute/needle3` via `needle download`
  (242,047,978 bytes; 121.0M parameters, 20 layers, d_model 768, 12 heads, 5 engram layers).
- Dataset: `nebius/SWE-rebench-openhands-trajectories`, revision
  `35455389ab51bf5e2306bfd436ef72d0f98bf882`. Licence **CC BY 4.0**. Dataset card:
  <https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories>. Authors as the card
  names them: Nebius (Trofimova et al., 2025). The pilot rows are a derived projection of the
  trajectories (six broad actions over a truncated issue text and the prior action labels), not a
  redistribution of the dataset.
- Preparation: `spike/coding_core/prepare_openhands.py --max-trajectories 100 --max-train 500
  --max-holdout 100`, exactly as #42: 34 trajectories scanned, 17 unresolved skipped, split by a
  hash of `instance_id` before caps. Train 500 actions from 11 instances; holdout 100 actions from 2
  disjoint instances. Pilot file hashes `733f93d0…` (train) / `f016551e…` (holdout) — identical
  regeneration is what the preflight asserts.
- Conversion: `spike/coding_core/to_needle3.py` — `query` and `system` verbatim from the pilot
  row; `tools` = one `next_action` tool, `action` enum of the six labels (tool sha256
  `f8bd9047…`); `answers` = `[{"name":"next_action","arguments":{"action":<label>}}]`; no
  `reasoning`. Converted file hashes `cc78a9f2…` (train) / `fbdd97ac…` (holdout).
- Labels: the six in `spike/coding_core/labels.json`, unchanged.

Raw prompts, trajectories, JSONL, adapter weights, `.cact` exports and machine-local paths are
intentionally absent from this public receipt.

## Results

Top-1 accuracy over all 100 holdout rows, none skipped. An empty `function_calls` list or an
out-of-enum value counts as a miss; there were none (0 empty, 0 suppressed, 0 out-of-enum, in every
Needle arm).

| Candidate | Top-1 | Notes |
|---|---:|---|
| Majority (`run_command`) | 26% | `baselines.py`, same rows |
| Repeat last | 22% | `baselines.py`, same rows |
| **Markov-1** | **37%** | `baselines.py`, same rows — the comparison baseline |
| `phase_backoff` (#48) | 42% | same script, same rows; context only, not part of #66's contract |
| Needle 3 base, untuned (control) | 20% | native engine, same tool; SOP Step 5 dynamic-range check |
| **Needle 3, 20 layers, LoRA** | **28%** | 121.0M params; the #66 arm |
| Needle 3, 7-layer rung, same adapter | 27% | 50.3M params, nearest Needle 2's 45M; predicts `read` 79× |
| Jev `jev-1.13.0` zero-shot | 21% | one Choice over the six criteria; macro-F1 0.142 |
| #42: Needle 2 (45M) MLX LoRA | 27% | historical, `TESTS-RESULTS/2026-09-11-coding-core-pilot` |

### Per-label recall (correct / support; predicted count)

| Label | Support | Needle 3 L20 | Needle 3 L7 | Base untuned | Jev |
|---|---:|---:|---:|---:|---:|
| `read` | 29 | 16 (40) | 23 (79) | 10 (36) | 13 (29) |
| `run_command` | 26 | 0 (8) | 0 (0) | 1 (7) | 1 (7) |
| `edit` | 19 | 5 (27) | 0 (6) | 2 (17) | 0 (8) |
| `search` | 19 | 7 (23) | 4 (10) | 6 (34) | 4 (20) |
| `run_tests` | 7 | 0 (2) | 0 (5) | 1 (6) | 3 (36) |
| `git` | 0 | — (0) | — (0) | — (0) | — (0) |

Needle 3 L20 confusion (rows = gold, columns = predicted; order edit, git, read, run_command,
run_tests, search): edit `[5,0,6,3,1,4]`, read `[2,0,16,3,0,8]`, run_command `[17,0,6,0,1,2]`,
run_tests `[2,0,1,2,0,2]`, search `[1,0,11,0,0,7]`. The dominant error is `run_command → edit`
(17 of 26), the same class #42 could not recover (`run_command` 0/26 there too).

### Needle 3 vs Jev on the same rows

Both correct 4, only Needle 3 24, only Jev 17, neither 55; the two arms make the same prediction on
only 8 rows. Jev's own confidence is informative in the negative: 68 rows below 0.5, 27 in
[0.5, 0.8), 5 at ≥ 0.8 (1 of those 5 correct). Its top-3 by returned probabilities covers 66/100,
reported as context only — the Needle arms have no top-3 counterpart here (native engine, one
grammar-constrained call per row).

### Confidence

Tuned Needle 3 weights report `confidence` as `None` on every row (fine-tuning does not update the
head; upstream documents this). The untuned base reported 0.17–0.96. Jev's distribution is above.

## Preflight measurements (contract, all met before training)

- Split, support and baselines reproduce #42 exactly: holdout `read` 29, `run_command` 26,
  `edit` 19, `search` 19, `run_tests` 7, `git` 0; majority 26% / repeat-last 22% / Markov-1 37%.
- Training-split support: `run_command` 138, `read` 123, `search` 88, `edit` 73, `run_tests` 67,
  `git` 11. No label at zero.
- Abstention / empty-answer rows after conversion: 0 (the converter refuses them; 500/500 and
  100/100 rows preserved).
- Token lengths with the real tokenizer (`render_example`, BOS/EOS counted): train min 406 /
  median 484 / max 546; holdout 418 / 462 / 509; cap 1024 → 0 rows truncated. `fit_max_len`
  bucketed the run to `seq_len 1024`. Target length 16–19 tokens.
- Boilerplate: the constant prefix (system line + the one tool) is 178 tokens; constant share of a
  row min 0.33 / median 0.37 / max 0.44 (train). Below the half-row caveat line.

## Run envelope

- Host: MacBook Pro 14" M4 Pro, 24 GB (the 2026-09-07 execution decision; the issue body's "Mac
  Studio" is superseded by it). Python 3.11.15, JAX 0.10.2 CPU float32, flax 0.12.8. Other work
  was running on the host throughout (1-min load 7–24), so wall times are upper bounds.
- Step-time probe (48 longest rows, batch 16, seq 1024): compile ≈ 23 s; steady steps 101 s and
  105 s; peak RSS 10.9 GB. Gate ≤ ~300 s/step: met.
- Training: `needle finetune needle3-train.jsonl --epochs 3 --batch-size 16 --lora-rank 16
  --lora-alpha 32 --max-len 1024 --val-split 0.1 --seed 0` → 450 train / 50 validation rows, 87
  steps (29/epoch), warmup 4, cosine decay, clip 1.0; numerics "CQ W4 STE + A8 (matches export)",
  5 LoRA weight groups. **Wall 6,790.6 s (1 h 53 min)**, user CPU 22,806.7 s, sys 6,293.5 s
  (≈ 4.3 cores average), max RSS 12.53 GB, peak footprint 16.68 GB. Epoch walls 2,619 s /
  2,514 s / 1,656 s; full-batch steps median 77 s (55–122 s with host load).
  Loss: epoch 1 train 2.9575 val 2.7249; epoch 2 train 2.5117 val 2.3702; epoch 3 train 2.3954
  val **2.3057**. Validation loss fell every epoch (step 6 gate: met). Adapter 7,906,600 bytes
  (sha256 `1a7e601e…`).
- Build: `needle build checkpoints/needle3.safetensors --lora <adapter> --out needle3-l20.cact
  --allow-numerics-mismatch` → 63.47 MB, 581 tensors, W4A8, 11.3 s wall (sha256 `fed14e7d…`).
  Without the override the re-ported #8 guard refuses the adapter ("does not declare its training
  numerics") because 3.0.1's `write_adapter` records no `qat_bits`, although 3.0.1 trains W4 STE by
  construction; the override is the plan's stated remedy, not a silently dropped guard.
  Rung: `--layers 7` → 26.38 MB, 218 tensors, 9.6 s (sha256 `650a2fee…`). Depth chosen from the
  checkpoint's ladder counts (`rung()` per depth): 6 → 33.0M, **7 → 50.3M**, 8 → 52.2M; nearest to
  45M is 7. Full table in `rung-params.json`.
- Numerics caveat (from the plan): local fine-tuning trains and exports at CQ W4 + A8; the
  published `needle3.cact` is ~2-bit Cactus Quants (35.34 MB). #42 was CQ mixed 2-bit QAT + A8 on
  MLX. The comparison is between the shipped local pipelines, not like-for-like numerics.
- Evaluation (native engine 3.0.1, one `complete()` per row, `reset()` between rows,
  `auto_date=False`, same `system` as training): L20 17.3 s wall for 100 rows (median 0.17 s/row,
  peak RSS 105 MB); L7 6.8 s (0.07 s/row, 76 MB); base 82.2 s (0.71 s/row — the base emits a
  think block; 137 MB). Row 0 re-scored after row 99 reproduced in every arm.
- Jev: 100 requests, 66,528 input tokens, 29.1 s wall (median 0.28 s/request), model seen
  `jev-1.13.0`; question frozen at commit `ffd4084` (`questions_sha256 e97bc1c4…`) before the run.
  Rows are public CC BY 4.0 data, so no repository-visibility gate applied.
- Verification: `pytest -q -m "not slow"` 581 passed / 7 skipped (after the merge);
  `-m slow` 18 passed; the re-ported guard's refuse-tests were watched go red with the guard mutated
  off and green restored; `tests/test_to_needle3.py` 12 passed.

## Interpretation

Three arms, one answer. The fine-tuned 121M model lands at 28%, the 50M rung at 27%, Needle 2 at
27%: the base model's size and architecture are not what limits this task at 500 training rows.
The trained model's error is structural, not noisy — it maps `run_command` (the majority class,
26 of 100) to `edit` 17 times and never predicts it correctly, exactly as #42 did. The untuned base
scores 20%, so the adapter did move the model (+8 points, and validation loss fell monotonically);
it just moved it to a place a transition table already beats.

Jev's 21% is the useful negative for the #68 map: with the same context a frontier-hosted decision
model does no better than repeat-last, and it says so — 68% of its answers are below 0.5
confidence. On the purpose/area task (#67, #69) the same model reproduces frontier annotation on
~9 of 10 rows; here the state carries almost no signal it can read. The gap is the task, not the
model: "what a coding agent does next" from an issue snippet and a label history is closer to the
agent's own trajectory than to anything in the text.

The lowest-cost follow-up, if this direction is revisited, is still the one #42 named: a small
explicit state/transition classifier against Markov-1 — `phase_backoff` from #48 already sits at
42% on these rows without a neural model. Not authorized by this issue.

## What this does not establish

- Nothing about the 44-label contract, the private corpus, or human usefulness.
- Nothing about Needle 3's quality on its intended tasks (tool calling, extraction) — the smoke
  query answered correctly; this pilot measures one off-distribution projection.
- The holdout is 100 rows from 2 instances with no `git` support; the +5pp gate was fixed in
  advance for that reason. A different sample could move any of these numbers by several points;
  none of them is near 42%.
- Jev was not decomposed (one Choice question, no Score/Noul factors); #68's decomposition tax
  was not paid here, deliberately, to keep the comparison to one zero-shot call per row.

## Provenance

`preflight.json` (conversion counts, support, token stats, hashes), `baselines.json`,
`rung-params.json`, `eval-l20.json`, `eval-l7.json`, `eval-base.json` (metrics, confusion,
per-row index/gold/prediction, weight hashes, timing), `jev/results.json` and
`jev/requests.jsonl` (metrics, per-row choice/confidence/probabilities, request/response hashes),
`train-log.txt` (the timestamped `needle finetune` log with the `/usr/bin/time -l` envelope).
No query text is stored anywhere under this directory.
