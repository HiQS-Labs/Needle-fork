# Coding-core OpenHands pilot — 2026-09-11

## Decision

**Stop this experimental arm at the cheap promotion gate.** The adapter's 27% top-1 accuracy did
not beat the 37% Markov-1 baseline. This result does not support spending more compute, synthesizing
class-balancing data, evaluating against the private corpus, or building the one-enum serving path.

This is a bounded negative result, not evidence that next-action prediction is impossible. The
holdout contains only 100 actions from two repository instances and has no `git` examples.

## Bet and falsifier

- Bet: collapsing coding trajectories to six broad actions would let a small LoRA adapter beat
  majority, repeat-last, and first-order Markov baselines cheaply enough to justify a serving spike.
- Falsifier: failure to meaningfully beat the strongest baseline on a source-domain holdout stops
  the arm before synthetic data or a larger run.
- Reversibility: Easy. This projection is additive and leaves `oracle/labels-v1.json` unchanged.

## Inputs

- Base code: `9d1934c`
- Dataset: `nebius/SWE-rebench-openhands-trajectories`
- Dataset revision: `35455389ab51bf5e2306bfd436ef72d0f98bf882`
- License: CC BY 4.0; attribution and dataset card:
  <https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories>
- Preparation: 34 trajectories scanned, 17 unresolved trajectories skipped; split by a hash of
  `instance_id` before row caps
- Selection: Hugging Face rows API offset 0; at most 100 trajectories; caps of 500 train and 100
  holdout actions; resolved trajectories only; 20% hash bucket assigned to holdout
- Train: 500 actions from 11 instances
- Holdout: 100 actions from 2 disjoint instances
- Holdout support: `read` 29, `run_command` 26, `edit` 19, `search` 19, `run_tests` 7, `git` 0

Raw prompts, trajectories, JSONL, adapter weights, and machine-local paths are intentionally absent
from this public receipt.

## Results

| Candidate | Top-1 accuracy |
|---|---:|
| Majority (`run_command`) | 26% |
| Repeat last | 22% |
| Markov-1 | **37%** |
| MLX LoRA adapter | 27% |

The adapter's top-3 accuracy was 68% using summed sequence log-probability and 52% using
length-normalized log-probability. Top-1 by supported label was `read` 21/29, `edit` 6/19, and zero
for `search`, `run_tests`, and `run_command`.

## Run envelope

- Training: MLX GPU, CQ mixed QAT + A8, sequence length 1024, LoRA rank 16, micro-batch 2
- Training rows: 450 train / 50 internal validation from the 500-row training partition
- Training: 29/29 steps, 361.2 seconds, 5.84 GB peak; final loss 0.8256, validation loss 0.8055
- Evaluation: all 100 holdout rows scored, none skipped; 50.6 seconds, 1.68 GB peak
- The initial full-batch configuration was rejected before training because its projected 35.6 GB
  exceeded the 12 GB memory limit; micro-batch 2 completed within the limit.
- Verification: 13 focused tests passed; full non-slow suite: 195 passed, 6 skipped, 6 deselected.

## Interpretation

The model fit the small training slice but did not convert that fit into better next-action ranking
than a transition table. The lowest-cost follow-up, if this direction is revisited, is to test a
small explicit state/transition classifier against Markov-1—not to enlarge this generative run.
