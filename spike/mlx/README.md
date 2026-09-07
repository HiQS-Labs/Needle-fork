# MLX fine-tuning spike — GH-5

Side quest. Runs on the **MBP 14" M4 Pro**, on branch `spike/mlx-finetune`, and never merges MLX
into `main`. Plan, gates and bounds: `PROJECT/1-INBOX/GH-5-MLX-FINETUNE-SPIKE.md`. Issue: #5.

## What is here

| file | role |
|---|---|
| `requirements-mlx.txt` | the only place `mlx` is named in this repo |
| `parity_check.py` | P1/P2 harness. **JAX reference side works today.** Loads a checkpoint (tiny fixture or real `.pkl`), runs fixed token batches through the Flax model, then through `san_mlx`, reports max \|Δlogits\| and argmax agreement. |
| `san_mlx.py` | the port target. One class per block of `needle/model/architecture.py`, each with the source line range it must match and a `NotImplementedError` until it does. Port in the order listed; run `parity_check.py --tiny` after each. |

## Scope: MLX on the **GPU**. Not the ANE, not a recompile.

`mlx.core.DeviceType` is exactly `['cpu', 'gpu']` — MLX has **no** Neural Engine backend, so no
result here is evidence about the ANE. That path is Orion's (Orion-fork#1). `san_mlx.py` is a
hand-written re-implementation of `architecture.py` that loads the same checkpoint; nothing is
compiled from the JAX source. See the "Scope boundary" table in the capture doc.

## Status (2026-09-07)

**P0 environment PASS** · **P1 parity PASS** (fp32 max |Δlogits| 4.172e-07, argmax 100%) ·
P0 training baseline in flight · P2-P4 not started.

Decisions, findings and the cross-machine contract live in
`PROJECT/1-INBOX/GH-5-MLX-FINETUNE-SPIKE.md`. Read it before changing anything here — it
records *why* the tolerance is what it is, and which limits P2 still has to resolve.

## Run

```bash
python3.11 -m venv .venv-mlx-spike            # MLX stays out of the system interpreter
.venv-mlx-spike/bin/python -m pip install -e '.[train]'
.venv-mlx-spike/bin/python -m pip install -r spike/mlx/requirements-mlx.txt

.venv-mlx-spike/bin/python spike/mlx/parity_check.py --tiny --dtype float32   # P1 gate: <= 1e-4
.venv-mlx-spike/bin/python spike/mlx/parity_check.py --tiny --dtype bfloat16  # deployed numerics
.venv-mlx-spike/bin/python spike/mlx/falsify_parity.py                        # prove the check can fail
.venv-mlx-spike/bin/python spike/mlx/parity_check.py --checkpoint checkpoints/needle2.pkl   # P2
```

`--dtype` exists because the fixture config defaults to **bfloat16** while the plan's 1e-4 is an
**fp32-vs-fp32** tolerance. Report both; never relax `--atol` to make a run pass. See Decision D1.

If the corpus is missing, build it — **do not re-extract on this laptop**, and pass `--pairs`
explicitly (its default points at a stale pre-v1 file here):

```bash
python3 utils/corpus/build_oracle_jsonl.py --pairs data/corpus-v1/pairs.jsonl \
        --out-dir data/corpus --check-max-len
```

Receipts go in `TESTS-RESULTS/<date>-mlx-spike/` — aggregates only.

## Rules that are not negotiable

- Do not edit `utils/corpus/`, `oracle/`, `needle/`, `tests/`, or `PROJECT/2-WORKING/`. A needed change there is a finding for #1.
- Do not commit `data/`. Public repo; the corpus holds real prompt text.
- Import `needle.model.finetune.render_example` for the chat template in P3 — do not re-implement it. Train/serve drift is the one failure #1 §6 calls out by name.
