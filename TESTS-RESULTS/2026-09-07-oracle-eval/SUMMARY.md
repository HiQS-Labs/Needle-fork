# Oracle evaluation — first model scoring in this repo

**Date:** 2026-09-07 · **Runtime:** MLX/GPU, float32 · **Gate:** issue #1 §5
**Corpus:** `data/corpus-studio/oracle-holdout.jsonl` — the **Studio** corpus, the one used for
anything scored (25,684 rows; 200 sampled, reservoir, seed 0).
**Adapter:** `data/spike-mlx/mlx-lora-adapter.pkl` — GH-5 P3, rank 16 / alpha 32, **one epoch on
the 2,000-row fixture**.

## Result

All three columns are the **same 200 rows**. The static baseline uses **train-split** label
frequencies, so it never sees the holdout answers.

| | top-1 | top-3 |
|---|---|---|
| static majority class (`read_file`, `run_script`, `search_code`) | 12.50% | 44.00% |
| base checkpoint, untuned | 3.50% | 17.00% |
| **tuned (MLX LoRA)** | **22.00%** | **46.00%** |
| **tuned − static** | **+9.50pp** | **+2.00pp** |

- **top-1: a real win.** 44 hits vs 25 on identical rows, z ≈ 2.51, p ≈ 0.012.
- **top-3: not distinguishable.** +2.00pp is **4 rows out of 200**, against a 95% CI of ±6.91pp
  (z ≈ 0.40, p ≈ 0.69).

**The 45.99% bar is not cleared, and 46.00% must not be read as clearing it.** That figure comes
from a different sample; on *these* rows the static baseline is 44.00%. The bar itself moves by
~±2pp with the sample, which is the same size as the entire measured effect.

## The control did its job

The untuned base scores **17.00%** top-3 — far *below* the static baseline. That is the expected
shape and it matters: it proves the scorer has real dynamic range and does not flatter everything
handed to it. The tuned model's gain over base (17.00% → 46.00%) is unambiguous. Fine-tuning
worked; what is unproven is whether it beats *guessing the three most common labels*.

## Two readings, not yet separated

1. **n=200 is too small** — my own subsample choice. A 1,000-row run narrows the CI to ~±3pp.
   Launched 21:01 the same evening.
2. **top-3 may be a weak gate for this label distribution.** Three labels dominate the corpus, so
   static top-3 starts at 44%. A model can rank substantially better — as top-1 shows — while
   barely moving top-3. If that holds at n=1000, it is a finding about the **metric in #1 §5**,
   not about the model, and the surface may need a different gate.

## Method notes

- **Scored on MLX, not `run.py`.** JAX/CPU generation measured **223 s/row** (670.3 s for 3 rows,
  24 new tokens). MLX scores at **14.2 s/row**, peak 2.21 GB.
- **Per-candidate teacher forcing.** The 44 labels share only 31 distinct first tokens (six collide
  on one), so first-token ranking would mis-rank the crowded `run_*` family. Each candidate is
  scored in full — #1 §5's "per-label sequence probability".
- **Sum and mean rankings both reported.** They diverge sharply (tuned top-3: 46.00% sum vs 39.00%
  mean; base: 17.00% vs 4.50%). Sum is the true sequence log-probability; mean normalises length.
  Reporting one alone would have hidden a real length bias.

## Caveats that bound the claim

- Candidates are scored with an **empty reasoning block**, so this measures `P(label | prompt)`.
  The deployed hook generates a `<think>` block first. Gold reasoning would leak the answer;
  generating one costs a forward pass per row. Constant across models, so **deltas are valid**;
  absolute numbers carry this caveat.
- The adapter is **one epoch on the 2k fixture**. This is a floor on what training can do.
- Full precision, no QAT — see GH-5 D6.

## Files

`raw-metrics.json` · logs in `data/spike-mlx/logs/eval-{base,tuned}.json` (gitignored)
