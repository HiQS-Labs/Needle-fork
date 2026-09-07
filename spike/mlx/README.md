# MLX fine-tuning spike — GH-5

Side quest. Runs on the **MBP 14" M4 Pro**, on branch `spike/mlx-finetune`, and never merges MLX
into `main`. Plan, gates and bounds: `PROJECT/1-INBOX/GH-5-MLX-FINETUNE-SPIKE.md`. Issue: #5.

## What is here

| file | role |
|---|---|
| `requirements-mlx.txt` | the only place `mlx` is named in this repo |
| `parity_check.py` | P1/P2 harness. **JAX reference side works today.** Loads a checkpoint (tiny fixture or real `.pkl`), runs fixed token batches through the Flax model, then through `san_mlx`, reports max \|Δlogits\| and argmax agreement. |
| `san_mlx.py` | the port target. One class per block of `needle/model/architecture.py`, each with the source line range it must match and a `NotImplementedError` until it does. Port in the order listed; run `parity_check.py --tiny` after each. |

## Run

```bash
pip install -r spike/mlx/requirements-mlx.txt
python3 spike/mlx/parity_check.py --tiny                          # random-init tiny config, no download
python3 spike/mlx/parity_check.py --checkpoint checkpoints/needle2.pkl   # real weights (fetched by `needle finetune` on first run)
```

Receipts go in `TESTS-RESULTS/<date>-mlx-spike/` — aggregates only.

## Rules that are not negotiable

- Do not edit `utils/corpus/`, `oracle/`, `needle/`, `tests/`, or `PROJECT/2-WORKING/`. A needed change there is a finding for #1.
- Do not commit `data/`. Public repo; the corpus holds real prompt text.
- Import `needle.model.finetune.render_example` for the chat template in P3 — do not re-implement it. Train/serve drift is the one failure #1 §6 calls out by name.
