# #59 round two — richer context failed the follow-up rule

On 40 previously unevaluated issues, richer context scored **52.5%**, below old
context (**57.5%**) and both leading action-only baselines (**60%**). Shuffled rich
context also scored **52.5%**. Do not invest in training/distillation or further
prompt tuning of this refresh on this quiz. This is a bounded negative result,
not proof that context or next-action prediction can never work.

## Same-case results

| Predictor | Correct / 40 | Accuracy | Six-label macro-F1 | Accuracy on 29 action-change cases |
|---|---:|---:|---:|---:|
| Majority | 10 | 25.0% | .0667 | 20.69% |
| Repeat last | 11 | 27.5% | .2540 | 0.00% |
| First-order Markov | 24 | 60.0% | .4247 | 62.07% |
| Phase backoff | 24 | 60.0% | .4820 | 55.17% |
| Qwen, old q2 context | 23 | 57.5% | .4129 | 65.52% |
| Qwen, rich q3 context | 21 | 52.5% | .3983 | 62.07% |
| Qwen, shuffled q3 context | 21 | 52.5% | .3566 | 51.72% |

The pre-score rule required rich context to beat the strongest action baseline,
old context and shuffled context by at least 5pp each, with nondegraded macro-F1
against the strongest baseline. Actual margins: **−7.5pp, −5pp, 0pp**; macro-F1
also decreased. The binding accuracy threshold was 65% (26/40); the result was five
correct cases short. No gate adjustment or near-pass designation.

Paired q3 versus q2: zero q3-only correct cases, two q2-only correct cases.
Versus shuffled: four correct-only cases each. These are descriptive counts, not
statistical confirmation. One deterministic-temperature call per arm does not
measure inference variability. The refresh bundles multiple changes; it does not
identify their individual effects.
"Previously unevaluated" means unused issue IDs in this project's earlier scored
partitions, not a guarantee of absence from a frontier model's pretraining data.

q3 recall: edit 6/8, read 5/10, command 7/10, tests 3/6, search 0/6. There are no Git
targets. Macro-F1 retains the fixed six-label denominator, with zero F1 for the absent
Git class; no claim of full six-action coverage. Exact next recorded action is not
human usefulness or the uniquely correct next action.

## Collection and disclosed adaptation

All three requests used `qwen/qwen3.8-max-0902`, API-reported provider Alibaba,
temperature zero, low reasoning, 4,096 total output-token cap, no tools or file access.
Prompts were frozen in [round one](SUMMARY.md), with identical cases and corrected
labels, and all responses were locked before grading. One case per source issue;
the eligible pool contains 1,722 rows, but **only 40 cases were model-scored**.
Training-only baselines use the refreshed 10,000-row training partition.

The initial client disabled reasoning, which this endpoint forbids. Two attempts
returned HTTP 400; the retained validation message named mandatory reasoning and
provider_name was null. No predictions or token usage were returned. Filed #60 and
witnessed the request regression test fail before fixing it. Under the operator's
explicit authority to adapt round two, the retry rule was amended publicly **before
any valid prediction/scoring** for three corrected requests, no further retries.
All other model, sampling, temperature, token-budget and decision settings stayed
fixed. This protocol deviation is disclosed, not treated as zero retry history.

Successful inference took 188.02 seconds total and reported **$0.180610** in token
costs (q2 .049632, q3 .064862, shuffled .066116). Conservative preflight estimated
$0.666496 for the three requests and $0.905339 with one reserved retry, including
possible cache-write pricing; provider price filtering was enabled. This is not an
account-level spending lock. Failed validations reported no usage; the earlier CLI
plan review has no reliable dollar accounting. No downloads or local neural training.

The client follows the documented [chat-completion contract](https://openrouter.ai/docs/api_reference/overview),
[reasoning parameters](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens),
and [provider price filter](https://openrouter.ai/docs/guides/routing/provider-selection#max-price).
Source attribution: [Nebius SWE-rebench OpenHands trajectories](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories),
CC BY 4.0; pinned revision and source digest are retained in the round-one manifest.

## Verification and replay

493 non-slow tests passed, 6 skipped, 11 deselected. Malformed, duplicate, missing,
empty and invalid-label predictions are rejected. Altered locked predictions fail
raw-response comparison; changed packets fail hash validation. A deliberately all-wrong
fixture scores zero and fails the follow-up rule. Independent confusion arithmetic
matches all three model metrics; independently refitting action baselines reproduces
the frozen baseline vectors. Repeated scoring is identical. All 13 old panel hashes
still match; held PR #43 remains untouched.

[Aggregate metrics and response hashes](round2-metrics.json) contain no raw examples.
Raw responses, requests, failed-attempt receipts and answer keys remain ignored.

```sh
.venv-mlx-spike/bin/python -m spike.coding_core.context_refresh_eval score \
  --data data/context-refresh-round1 --out data/context-refresh-round2-corrected
```

That command only replays retained results; it makes no model calls. Collection is
a separate `collect` mode requiring an explicit credential file, deadline and fresh
output directory. The recipe is not authorization to rerun this completed experiment.

## Decision

Close #59 as a completed negative experiment and #60 as a verified client fix.
Preserve q3 tooling and evidence, but stop this exact-context-refresh investment.
Before another model round, decide whether the product needs exact recorded-action
prediction or a narrower output such as action-change detection / a short list of
plausible next steps. Those need their own labels and success criteria; they are
options, not validated pivots or instructions to launch another campaign. The old
manual trial still has zero ratings; no acceptance rate or deployable Oracle exists.
The operator's two-hour wall maximum was not approached.
