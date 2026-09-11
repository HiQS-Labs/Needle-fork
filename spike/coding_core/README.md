# Coding-core pilot

This reversible spike projects software-agent trajectories into six broad next actions. It does
not modify or replace the canonical 44-label Oracle contract.

The default source is Nebius's `SWE-rebench-openhands-trajectories`, pinned to commit
`35455389ab51bf5e2306bfd436ef72d0f98bf882`. The dataset is CC BY 4.0; see its
[dataset card](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories) and cite
the authors when publishing derived results. Raw text and generated rows stay below ignored
`data/`; only sanitized aggregate receipts belong in Git.

```sh
python spike/coding_core/prepare_openhands.py --max-trajectories 100 \
  --outdir data/coding-core/pilot
python spike/coding_core/baselines.py \
  --train data/coding-core/pilot/pilot-train.jsonl \
  --holdout data/coding-core/pilot/pilot-holdout.jsonl \
  --out data/coding-core/pilot/baselines.json
python spike/mlx/train_lora.py data/coding-core/pilot/pilot-train.jsonl \
  --out data/coding-core/pilot/mlx-lora.pkl \
  --receipt data/coding-core/pilot/train-receipt.json
python spike/mlx/eval_oracle.py \
  --holdout data/coding-core/pilot/pilot-holdout.jsonl \
  --labels spike/coding_core/labels.json \
  --adapter data/coding-core/pilot/mlx-lora.pkl \
  --receipt data/coding-core/pilot/eval-receipt.json
```

Preparation uses the standard-library datasets-server rows API, so it does not download the single
2.08 GB Parquet file or add a project dependency. It verifies the live dataset revision before
fetching and scans at most 100 source trajectories by default; `--input-jsonl` supplies an offline
export and makes no network request.

The preparation step keeps resolved trajectories by default, splits by `instance_id` before row
caps, refuses malformed/unknown tool calls, and will not overwrite an existing output directory.
`think`, task-management, and finish calls end the contiguous coding-action sequence; they are not
silently forced into one of the six labels. Synthetic balancing is intentionally deferred until
the measured label distribution shows a specific shortage.

## First bounded run (2026-09-11)

The first run stopped at its promotion gate. On a 100-row, two-instance OpenHands holdout, the
adapter reached 27% top-1 accuracy, versus 26% for the majority baseline and 37% for Markov-1.
Because the adapter did not beat the strongest cheap baseline, this arm does not proceed to
synthetic balancing, a larger training run, private-corpus evaluation, or one-enum serving. See
`TESTS-RESULTS/2026-09-11-coding-core-pilot/SUMMARY.md` for the aggregate receipt and limitations.
