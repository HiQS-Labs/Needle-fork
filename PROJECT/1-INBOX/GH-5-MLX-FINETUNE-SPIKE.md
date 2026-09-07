---
title: "GH-5 — MLX fine-tuning spike (side quest, MBP 14\" M4 Pro only)"
status: Queued
created: 2026-09-07
updated: 2026-09-07
owner: noelsaw1
goal: >
  Determine, on a machine that is not the daily driver and on a branch that never merges
  MLX into main, whether the Oracle's LoRA fine-tune can run under MLX on Apple Silicon GPU
  with parity to the JAX path and a speedup worth adopting for Phase 3/4.
related:
  - https://github.com/HiQS-Labs/Needle-fork/issues/5
  - https://github.com/HiQS-Labs/Needle-fork/issues/1
  - https://github.com/HiQS-Labs/XYZ-forge/issues/467
context_tags: [side-quest, mlx, spike, finetune, apple-silicon, phase-3]
effort: 3
complexity: 4
risk: 2
phases: 5
branch: spike/mlx-finetune
---

# GH-5 — MLX fine-tuning spike

## Status

| What was just completed | What's next |
|---|---|
| Spike scaffolded: issue #5, this capture doc, `spike/mlx/` with the JAX reference side of a parity harness working and the MLX side stubbed block-by-block against `architecture.py` line refs. | On the **MBP 14" M4 Pro**: P0 (install `mlx`, record the JAX/CPU baseline), then P1 (port the forward pass, pass the tiny-fixture parity check). |

## Why this is a side quest and not Phase 2 work

Phase 2 §4 trains on **JAX/CPU** — decided 2026-09-07, recorded in #1 §4, `CHANGELOG.md` and
XYZ-forge#467. `doc/finetuning.md` states `jax-metal` is not viable on current JAX, so on Apple
Silicon JAX means CPU. That is acceptable for a 45M LoRA and it is the path the main lane owns.

MLX would put the same training on the GPU. Whether that is *worth* anything is an empirical
question with a bounded cost, so it runs on the machine that is not the daily driver, on a branch
that cannot merge, consuming the corpus the main lane already builds. **If it works it is a
bonus for Phase 3/4. If it does not, nothing on `main` changes.** Either outcome is complete.

## Bounds — read before touching anything

- **Only `spike/mlx/` and this doc change on this branch.** No edits to `utils/corpus/`,
  `oracle/`, `needle/`, `tests/`, or the #1 plan. A needed change there is a *finding* to report
  on #1, not a commit here.
- **MLX is never a dependency of `main`.** `spike/mlx/requirements-mlx.txt` is the only place it
  is named.
- **The corpus is an input, not an output.** `data/corpus/oracle-train.jsonl` (q1 format,
  `--max-len 2048`) is produced by the main lane's `build_oracle_jsonl.py`. The spike does not
  re-extract, relabel or reserialize. Session-level holdout is inherited as-is.
- **Receipts go in `TESTS-RESULTS/`** per the Message 4 protocol already adopted in this repo:
  aggregates only, never prompt text.

## Phases — each gate is a receipt, each can be a no-go

### P0 — Environment

- [ ] `pip install -r spike/mlx/requirements-mlx.txt` on the M4 Pro; `python3 -c "import mlx.core as mx; print(mx.default_device())"` reports the GPU.
- [ ] Record the **JAX/CPU baseline on the same machine**: `needle finetune` on a fixed 2,000-row subset of `oracle-train.jsonl`, `--max-len 2048`, 1 epoch — wall-clock, peak RSS, final loss. This is the number P4 compares against; without it P4 has no meaning.
- Gate: both recorded in `TESTS-RESULTS/<date>-mlx-spike/`.

### P1 — Forward-pass parity on the tiny fixture

- [ ] Port `SimpleAttentionNetwork` to `spike/mlx/san_mlx.py`, block by block, against these source lines in `needle/model/architecture.py`: `ZCRMSNorm` (46), RoPE (97–118), `Engram` + `_sinkhorn` (169–207), `MultiHeadAttention` GQA (209–278), `_walsh_matrix` + `HadamardMLP` (280–303), `Block` (305), the top-level model.
- [ ] `python3 spike/mlx/parity_check.py --tiny`: same random-init tiny checkpoint (`tests/conftest.py::tiny_checkpoint` config) loaded into both; fixed token batches; report max |Δlogits| and argmax agreement.
- Gate: max |Δ| under a tolerance you state in the receipt (fp32 vs fp32 should be ~1e-4; state it, do not hand-wave). Argmax agreement 100% on the fixture.

### P2 — Parity on the real base checkpoint

- [ ] `python3 spike/mlx/parity_check.py --checkpoint <needle2.pkl>` (the checkpoint `needle finetune` downloads on first run). Includes the quant-aware path if `--qat-bits auto` applies.
- Gate: same tolerance as P1 on real weights. **If this fails and the cause is not local to the port, stop and record — that is a complete no-go.**

### P3 — LoRA training loop in MLX

- [ ] Rank 16 / alpha 32 on the same five projections as `finetune.py:23` (`q_proj`, `k_proj`, `v_proj`, `gate_proj`, `out_proj`); same batch 16, lr 1e-4 warmup+cosine, clip 1.0, `max_len 2048`; same rendered prompt/target as `finetune.render_example` (import it — do not re-implement the chat template).
- [ ] Train on the same fixed 2,000-row subset as P0; compare the loss curve to JAX's on the same rows.
- Gate: loss tracks JAX within noise; adapter weights saved in a shape `needle build --lora` accepts, or a documented converter.

### P4 — The number that decides

- [ ] Full `oracle-train.jsonl`, 1 epoch, MLX/GPU vs the P0 JAX/CPU baseline: wall-clock per epoch, peak memory.
- [ ] Export the MLX-trained adapter through `needle build` and evaluate on the session-level holdout with the same §5 metrics; compare to the JAX-trained adapter.
- Gate: **go** if P1–P3 passed, speedup ≥ 2×, and the adapter round-trips through `needle build` to comparable holdout accuracy. Otherwise **no-go**, with the reason.

## Anti-goals

- Not a rewrite of `needle/model/`. `san_mlx.py` is a spike artifact until a go decision promotes it through a normal PR.
- Not a second corpus, taxonomy, serializer, or eval. The spike proves a *runtime*, not a *model*.
- Not a Phase 2 dependency. #1 §4 proceeds on JAX regardless of this doc's outcome.

## Reproducing on the MBP

```bash
git fetch origin && git checkout spike/mlx-finetune
pip install -r spike/mlx/requirements-mlx.txt
python3 spike/mlx/parity_check.py --tiny        # P1: JAX reference runs today; MLX side raises NotImplementedError per block
```

The corpus must be present at `data/corpus/oracle-train.jsonl` (copy from the Studio, or re-run
`utils/corpus/extract_claude_transcripts.py` + `build_oracle_jsonl.py --check-max-len` over the
Studio's transcripts via the SMB share). It is gitignored; never commit it — this repo is public.
