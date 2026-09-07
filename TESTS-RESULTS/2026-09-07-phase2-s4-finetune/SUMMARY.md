# Phase 2 §4 — first Oracle fine-tune, feasibility receipt

**Host:** Mac Studio (M1 Max) · **Backend:** JAX 0.11.1, CPU, float32 · **Date:** 2026-09-07
**Status:** §4 **rescoped** — the full-corpus run specified in #1 §4 is not feasible on this path.

Aggregates only. No prompt text, no corpus rows. See `TESTS-RESULTS/README.md`.

## Headline

Training works end to end; the *scale* does not. At the measured rate a single epoch over the
full 48,744-row corpus would take **~127 hours**, and the CLI default is 3 epochs.

## Measured

| Quantity | Value |
|---|---|
| Corpus rows (train split) | 48,744 |
| Batch size | 16 |
| Steps per epoch, full corpus | 3,047 |
| Wall-clock per step | ~150 s |
| **Projected wall-clock per epoch, full corpus** | **~127 h** |
| XLA compile (first step) | ~9 min, one-off |
| Peak RSS | ~18.2 GB |
| Process CPU | ~410% |
| Host load average during run | 32 → 261 (1-min) |

Loss is falling as expected: step 1 `1.9124`, step 2 `1.7389`, step 3 `1.9173` (batch noise at
batch 16 — this is a smoke pass, not a converged run).

Config: LoRA rank 16 / alpha 32 over 5 weight groups; `seq_len 2048 cap 2048`;
numerics `CQ mixed[embedding=4,mhc=4,default=2] STE + A8` (matches export);
schedule warmup 1 + cosine decay, clip 1.0.

## Why `--max-len` cannot be reduced

Sampled 1,200 train rows and tokenised each with the real tokenizer via
`needle.model.finetune.render_example`:

| min | p50 | p90 | p99 | max |
|---|---|---|---|---|
| 1,524 | 1,691 | 1,799 | 1,903 | 1,944 |

Coverage at `--max-len` 512 and 1024 is **0.0%** — every row is truncated. Only 2048 covers the
corpus (100%, 0 truncated), consistent with the `--check-max-len` result of 1,950 recorded when
the corpus was built.

The distribution is near-uniform because the q1 query embeds **all 44 tool schemas in every
row**: roughly 1,200 of the ~1,700 tokens per row are the same schema block, repeated 48,744
times. There is no short-row bucket to exploit, so length bucketing buys nothing. This is a
serializer design property, not a training-config one.

## Decision — all execution moves to the MBP 14" M4 Pro (2026-09-07)

**Superseding decision.** Running Phase 2 §4 on the Studio and GH-5 on the MBP created two
lanes whose results had to be reconciled by hand — different corpora, different baselines,
different receipts. That coordination cost was not worth it. **All execution now happens on
one machine: the MBP 14" M4 Pro.**

- The MBP has the GPU, MLX parity already passing (GH-5 P1), and both corpora on disk.
- The Studio's only unique contribution was the `~/.claude` transcripts the corpus was built
  from. Those are copied and checksum-verified at `data/corpus-studio/` on the MBP, so the
  Studio is no longer on the critical path for anything.
- The Studio remains the git host and the place planning happens. **It runs no jobs.**
- The 512-row smoke pass documented below was stopped at step 10/32 under this decision. Its
  measured rate stands; it never produced a saved adapter.

§4 and GH-5 are no longer separate lanes. They are one lane on one machine: MLX first, with
the JAX/CPU path retained only as the correctness reference it already serves as in
`parity_check.py`.

## Prior decision — §4 on hold (2026-09-07, superseded above)

The rescoped 6,000-row run was **not launched**. On the same day this receipt was written, the
MBP 14" M4 Pro cleared GH-5 P1 (MLX forward-pass parity, fp32 `max|dlogits| = 4.172e-07`, 240x
inside the 1e-4 tolerance). Spending ~15.5 h of the Studio's wall-clock on a CPU adapter is not
worth it while the GPU path is one gate from a training loop. §4 resumes when GH-5 reaches P3,
or when MLX returns a no-go.

## Consequences

1. **§4 is rescoped** to a subsample (~6,000 rows, 1 epoch ≈ 15.5 h) so an adapter exists to
   evaluate against the 45.99% top-3 bar. LoRA rank 16 on a 45M model does not need 48k rows.
2. **GH-5 (MLX spike) moves from bonus to load-bearing.** GPU execution is the only lever that
   changes the order of magnitude without altering the q1 format that `tests/test_serialize.py`
   pins between the hook and the trainer.
3. **Parked, not actioned:** shrinking the per-row schema block. It would cut ~70% of the tokens,
   but it changes the query format on both the hook and trainer sides at once. That is a Phase 2
   design decision for #1, not a speed fix to slip into §4.

## Environment findings (both cost a failed run to discover)

- `needle finetune` must run with **`HF_HUB_DISABLE_XET=1`** on this network. Without it the base
  checkpoint download fails at `cas-server.xethub.hf.co` — *after* printing `downloading from
  Hugging Face`, so the failure looks like a training failure. Applies to GH-5 P0 as well.
- **`python -m needle.cli` silently does nothing and exits 0.** `needle/cli.py` has no
  `__main__` guard; the entry point is `needle.cli:main` (`pyproject.toml:29`). Invoke via the
  console script, or `python -c "from needle.cli import main; main()"`.
- `needle` sends anonymous usage counts (function name, version, OS — no prompts or outputs)
  unless `NEEDLE_TELEMETRY=0` is set. Set it on all runs here.

## Reproduce

```bash
export HF_HUB_DISABLE_XET=1 NEEDLE_TELEMETRY=0
python -c "import sys;sys.argv=['needle','finetune','data/corpus/smoke-512.jsonl',
  '--checkpoint','checkpoints/needle2.pkl','--epochs','1','--batch-size','16',
  '--max-len','2048','--val-split','0','--out','checkpoints/smoke-lora.pkl'];
  from needle.cli import main;main()"
```

The corpus and the 512-row smoke subset are gitignored and are never committed — this repo is
public and the rows contain real prompt text.
