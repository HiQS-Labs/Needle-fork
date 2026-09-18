# RELAY · Needle 66 Needle 3 pilot plan QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-18.
-->

NEXT: Producer
STATUS: Approved
ROUND: 2 / 2

## ▶ TAKE YOUR TURN — read this first (works for ANY agent: Claude, Codex, agy)
1. **Read this whole file** (header, Setup, Ground rules, every block in the Log).
2. **Check it's your turn:** `NEXT` (top) names the role to act. Confirm you are bound to it and the
   last Log block isn't already yours. If not → STOP and reply "wrong window — nudge the <other> window."
3. **Do your role's work** on the artifact named in Setup:
   - **Reviewer:** review vs the Definition of Done → graded findings
     (`[Blocker]`/`[Should]`/`[Nit]`/`[Pass]`), each with a concrete fix → set a **Verdict**
     (Approved | Changes requested | Blocked). **Review the whole file, not just the diff** (GH-268):
     a beta test had this loop reach `Approved` in two rounds while an independent audit of the same
     branch found 20 issues (1 critical, 4 high) — every one of them in the pre-existing code the
     change sat on, which nobody had read. Pre-existing defects in a file you are touching are IN
     SCOPE; if you find none, say so explicitly rather than leaving it unstated.
     **Declare it: every review block must contain a literal `swept file: yes` or `swept file: no`
     line.** Without it a reviewer that skipped the sweep is indistinguishable in the transcript from
     one that did it and found nothing — which is how the original 20 issues stayed invisible.
     Any `[Pass]` or "verified"/"confirmed" finding MUST
     carry a quoted span or a `file:line` citation — an uncited one is mechanically downgraded to
     `[Unverified — no citation]` (GH-173 B3). Do **not** edit the artifact; only append findings here.
   - **Producer:** log a disposition for every open finding (Implemented / Modified / Declined + why),
     make the change, then add new work.
4. **Append ONE block** at the very bottom, directly **above** the marker line. Never edit earlier turns.
5. **Update the header:** flip `NEXT`; set `STATUS` (`Approved` closes — Reviewer only; else `Open`);
   the Producer bumps `ROUND` when opening a new cycle. If the max `ROUND` ends without `Approved`,
   set `STATUS: Escalated`.
6. **Commit only the relay file** (`relay(needle-66-agy-plan-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: **GH-66-needle3-pilot-plan.md** (embedded below — read it here).
- Reviewer: agy   ·   Producer: claude-a
- Started: 2026-09-18

### Artifact — GH-66-needle3-pilot-plan.md
````
# HiQS-Labs/Needle-fork issue #66 — body as filed 2026-09-18
# https://github.com/HiQS-Labs/Needle-fork/issues/66

**Status: plan only. Scoping and an Agy relay QA of this plan are authorized; execution waits for an explicit operator "go" after the QA.** Nothing here reverses #42's negative result, #62's failed gate, or PR #43's hold.

## Summary

Rerun the [#42 six-action coding-core pilot](https://github.com/HiQS-Labs/Needle-fork/pull/42) on upstream **Needle 3** (Cactus Compute's 3.0.1 release, the "Cactus 3" model) under the same data, split, holdout and baseline, with the labels presented as a single extraction tool carrying a six-value enum instead of six tools. The question is narrow: does the new base model, fine-tuned the cheap way upstream ships, beat the Markov-1 transition table that Needle 2 could not.

Operator decisions taken on 2026-09-18 (recorded here so the plan does not re-open them):

| Decision | Choice | Rejected alternatives |
|---|---|---|
| Which Cactus 2 test to rerun | #42 six-action LoRA pilot (the only test that trained Needle itself) | #31/#57 purpose classifier; #62 shortlist hit@3; full 44-label contract (#1/#12) |
| Compute | JAX on CPU, local Mac Studio (M1 Max), stock `needle finetune` + `needle build` | Port `spike/mlx` to Needle 3's new block; rented CUDA box |
| Label formulation | One extraction tool, six-value enum | One tool per label; both arms |
| Repo home | Branch `experiment/needle3-pilot` in this fork, upstream 3.0.1 merged in | Fresh upstream clone; the upstream clone itself |

## Why now

- Upstream shipped Needle 3 on 2026-09 (`cactus-compute/needle` `94df999`, package `cactus-needle==3.0.1`): a Laddered Simple Attention Network, 29-121M parameters, every depth from 2 to 20 layers deployable, Monarch Hadamard MLP, causal conv taps, engram n-gram memory. Upstream reports fine-tuning lifts every subnetwork 18-36 points on DroidCall. The README states "extraction generalises to classification" via enums, which is exactly the shape #42 wanted but never served.
- #42 stopped at 27% top-1 versus Markov-1 37% on Needle 2. It was bounded, cheap and reproducible: public dataset, pinned revision, deterministic split, baselines script. That makes it the one Cactus 2 test where a Cactus 3 number is directly comparable.
- Needle 3 still caps tool retrieval at the top five when more than five tools are declared (`llms.txt` "Tool retrieval"). The #12 serving mismatch is therefore unchanged for the 44-label contract; the enum formulation sidesteps it for six labels and would be the serving shape for 44 if this passes.

## Bet and falsifier

- **Bet:** a larger, laddered base with a classification-shaped output beats a first-order transition table on the same holdout by a margin that survives noise on 100 rows.
- **Falsifier:** Needle 3 top-1 on the frozen 100-row holdout below **42%** (Markov-1 37% + the fork's standing +5pp lift rule from #48/#62). Below that, the arm stops; no tuning, no synthetic balancing, no larger run, no serving spike.
- **Pass unlocks only** the next bounded step: a separately authorized one-enum serving spike against the private corpus. It does not establish human usefulness.
- **Reversibility:** easy. Additive branch, ignored data directory, no change to `oracle/labels-v1.json`, no release-surface change.

## Frozen comparison contract

Everything below is fixed before training starts; a change defines a new experiment.

- Dataset `nebius/SWE-rebench-openhands-trajectories` at revision `35455389ab51bf5e2306bfd436ef72d0f98bf882` (CC BY 4.0, attribute in the receipt).
- Preparation by `spike/coding_core/prepare_openhands.py --max-trajectories 100` exactly as in #42: resolved trajectories only, split by hash of `instance_id` before caps, 500 train / 100 holdout.
- Preflight assertion (SOP Step 2, must fail if wrong): train = 500 actions from 11 instances; holdout = 100 actions from 2 disjoint instances; holdout support `read` 29, `run_command` 26, `edit` 19, `search` 19, `run_tests` 7, `git` 0. Baselines recomputed by `spike/coding_core/baselines.py` must reproduce majority 26%, repeat-last 22%, Markov-1 37%. Any mismatch stops the run and is reported before anything else happens, because 37% would no longer be the comparable baseline.
- Labels: the six in `spike/coding_core/labels.json`, unchanged.
- Metric: top-1 accuracy over all 100 holdout rows, none skipped; an empty `function_calls` list or an out-of-enum value counts as a miss. Per-label recall reported alongside. Confidence distribution reported as context only.
- Token-length distribution of the converted rows checked against `--max-len 1024` (the #42 sequence length); truncation of the target is a preflight failure.

## Plan

Each step names its gate. Steps are sequential.

1. **Branch and merge.** Cut `experiment/needle3-pilot` off fork `main`. Merge `cactus-compute/needle` `main` (`94df999`, 3.0.1). The fork changed files under `needle/` (adapter build-safety guard #8, `--allow-numerics-mismatch`); if the merge conflicts inside `needle/`, take upstream's `needle/` wholesale for this branch and keep the fork's `spike/`, `oracle/`, `utils/`, `tests/`. Re-port the #8 guard only if the Needle 3 `build` path is reachable with a mismatched adapter. Gate: `pytest -q -m "not slow"` green; fork tests that assert Needle 2 internals are skipped with a reason, not deleted.
2. **Environment.** Python 3.12 venv (`/opt/homebrew/bin/python3.12`; the system 3.14 has no JAX), `pip install -e ".[train,test]"`, `needle download needle3.safetensors`. Gate: `needle run --checkpoint checkpoints/needle3.safetensors` answers a one-tool smoke query.
3. **Data preflight.** Regenerate the pilot rows into ignored `data/coding-core/pilot/`; run the assertion block above. Gate: split, support and baselines match #42 exactly.
4. **Converter.** `spike/coding_core/to_needle3.py`: pilot JSONL to Needle 3 fine-tune JSONL. `query` = the serialized context the pilot already renders; `tools` = one tool `next_action` with `parameters.properties.action` an enum of the six labels, `required: ["action"]`; `answers` = `[{"name": "next_action", "arguments": {"action": <label>}}]`; no `reasoning` field. Unit tests for enum coverage, row count preservation and refusal of unknown labels. Gate: tests green; the token-length check above passes.
5. **Step-time probe.** One training step on CPU at batch 16, rank 16, alpha 32, max-len 1024. Reference: the fork measured ~150 s/step for Needle 2 at max-len 2048 on the full corpus (`TESTS-RESULTS/2026-09-07-phase2-s4-finetune`). Gate: if a step exceeds ~5 minutes (3 epochs beyond ~8 h at ~29 steps/epoch), stop and report to the operator before running the job; the rented-GPU option is then reconsidered, not taken unilaterally.
6. **Train.** `needle finetune data/coding-core/pilot/needle3-train.jsonl --epochs 3 --lora-rank 16 --lora-alpha 32 --max-len 1024 --val-split 0.1 --out data/coding-core/pilot/needle3-lora.safetensors`. Record wall clock, peak RSS, per-epoch train and validation loss. Gate: validation loss falls; a flat or rising curve is reported, not tuned.
7. **Build.** `needle build checkpoints/needle3.safetensors --lora <adapter> --layers 20 --out data/coding-core/pilot/needle3-l20.cact`. Local fine-tuning trains and exports at 4 bits; #42 was CQ mixed 2-bit QAT + A8 on MLX. The receipt states this: the comparison is between the shipped local pipelines, not like-for-like numerics.
8. **Evaluate.** `spike/coding_core/eval_needle3.py`: `needle.Needle(weights=<cact>, tools=[next_action])`, one `complete()` per holdout row with the same serialized context, parse `function_calls[0].arguments.action`, score against the label. Native engine only; the #42 top-3 log-probability figure has no counterpart here and is not reported. Gate: all 100 rows scored, none skipped.
9. **Second rung (time permitting).** `needle build ... --layers 8` from the same adapter, evaluated the same way, as the Needle-2-sized comparison; confirm from the ladder table that 8 layers is the rung nearest 45M before choosing it. Optional; its absence does not block the receipt.
10. **Receipt.** `TESTS-RESULTS/2026-09-XX-needle3-coding-core-pilot/SUMMARY.md` in the #42 format: decision, bet and falsifier, inputs with revisions and commit shas, results table (majority, repeat-last, Markov-1, Needle 3 L20, Needle 3 L8 if run), per-label recall, run envelope, interpretation, what it does not establish. Aggregates only: no prompts, rows, weights or machine paths in Git. Push the branch, open a draft PR linked here, comment the headline number on this issue.

## Out of scope (named so they stop resurfacing)

- The 44-label contract, the private corpus, synthetic balancing, hyperparameter sweeps, the MLX port, any serving or hook integration, any change to `oracle/labels-v1.json`, PR #43, the #65 benchmark scaffolding.
- Re-scoring or re-interpreting #42, #48, #51, #59 or #62. Their gates and results stand.

## Risks and how each is handled

- **Upstream merge is large** (new architecture, safetensors checkpoints, new CLI surface). Handled by the wholesale-`needle/` rule in step 1 and by keeping the branch experimental; nothing lands on `main` from this issue.
- **CPU is too slow for 121M.** Handled by the step-time gate in step 5; no unattended multi-day run.
- **Engine refuses or empties on off-distribution context.** An empty call is a miss by contract; the rate of empties is reported so it is visible rather than hidden in accuracy.
- **Holdout is 100 rows from 2 instances** (as in #42). The +5pp gate is fixed in advance for that reason; a pass is a signal to run the next bounded step, not a claim of generalization.
- **Prompt-format drift from #42.** The converter reuses the pilot's serialized context verbatim; the only change is the answer shape.

## Deliverables

- Branch `experiment/needle3-pilot` with `spike/coding_core/to_needle3.py`, `spike/coding_core/eval_needle3.py`, their tests, and the receipt.
- A draft PR linked to this issue; a comment here with the top-1 numbers and the pass/stop decision.
- No new package dependencies beyond upstream's `train` extra.

## References

- Upstream release: https://github.com/cactus-compute/needle (3.0.1, `94df999`); weights https://huggingface.co/Cactus-Compute/needle3; `llms.txt` sections "Tool retrieval" and "Fine-tuning (CLI)".
- #42 pilot receipt: `TESTS-RESULTS/2026-09-11-coding-core-pilot/SUMMARY.md` on `experiment/coding-core-pilot`.
- #12 serving mismatch, #1 umbrella, #62 shortlist park, SOP Step 2 data preflight.

---

# Appendix A — upstream Needle 3 reference excerpts (cactus-compute/needle @ 94df999, package 3.0.1)

## A1. README.md lines 1-16 and the fine-tuning/deploy sections

A foundation model for mobiles, wearables, robots, smart home, automotive and microcontrollers. The whole model is a single 8-29 MB binary built on our Simple Attention Network, and we trade general chat capacity to beat models 10x its size on mobile tool calls and match 2-3x bigger models on extraction.

- **Tool calls**: given the functions your app exposes, Needle picks the right ones and fills every argument from what the user said. Ask for two things and you get two calls in order; ask for something no tool covers and you get an empty list, not a guess.
- **Structured extraction**: declare a shape, hand over messy text, get typed fields back: an invoice, a booking, a notification, a form. The decode grammar guarantees the output parses, and extraction generalises to classification.
- **Text embedding**: the same model returns a vector for a sentence, so an app can search, match and route locally.

![Needle 3 at a glance](assets/model.svg)

Needle 3 is a Laddered Simple Attention Network: a Monarch Hadamard MLP in place of the FFN, GQA attention with causal conv taps, engram n-gram memory read by gather, and multi-lane hyper-connections, trained so that every depth from 2 to 20 layers is a deployable model. Most of its parameters sit in the engram, so the 121M model does the arithmetic of a 50M one. A byte-level grammar compiled from your schemas constrains every token, and every response carries a calibrated confidence score from a learned head. The architecture diagram is on the [release page](https://cactuscompute.com/needle).

## Benchmarks

Tool calling is exact-match accuracy on the full test splits, extraction is field micro-F1 on the full test splits.


```sh
pip install "cactus-needle[train]"
needle finetune data.jsonl --epochs 10 --out adapter.safetensors
needle build --lora adapter.safetensors --layers 8 --out tuned.cact
```

Local fine-tuning trains and exports at 4 bits; the [fine-tuning guide](https://cactuscompute.com/blog/finetuning-needle) has the rest. The 2-bit post-training and quantisation behind the shipped model, enriched with Cactus proprietary datasets, run on the [Cactus Platform](https://cactuscompute.com/dashboard).

## Deploy

Every deployment target ships a prebuilt engine under 1 MB that loads the `needle3.cact` weights at start. `needle build --platform <folder> [--layers N]` fetches that engine and puts the weights beside it.

![One engine per platform folder](assets/deploy.svg)

```sh
needle build --platform macos-arm64
needle build --platform linux-arm64 --layers 8 --out ./pi
./macos-arm64/needle --model needle3.cact --tools tools.json --serve
```

The [devices guide](https://cactuscompute.com/blog/needle-supported-devices) lists every folder and what ships in it.

By default, telemetry is turned on in the binary. To turn it off, set environment variables NEEDLE_TELEMETRY=0 and DO_NOT_TRACK=1. 

## Citation

Needle is built by the Cactus Compute team. If you use it in your work, please cite:

## A2. llms.txt — tool retrieval, fine-tuning CLI, CLI reference, gotchas

Relative language ("tomorrow at 7") resolves only when a `date:` fact licenses it. Omitting the system turn is safe.

## Tool retrieval (many tools)

With more than 5 declared tools, a built-in retrieval head renders only the top-5 per turn and constrains the grammar to that subset. Persist embeddings across runs:

```python
agent = needle.Needle(tools=big_catalogue, tool_index_path="tools.idx")
```

## Fine-tuning (CLI)

LoRA on the frozen base, merged at export. Data is JSONL, one example per line; `reasoning` optional, off-topic example has `answers: []`:

```json
{"query": "dim the kitchen to 10", "tools": [{"name": "set_lights", "parameters": {"type": "object", "properties": {"room": {"type": "string"}, "brightness": {"type": "integer"}}, "required": ["room"]}}], "answers": [{"name": "set_lights", "arguments": {"room": "kitchen", "brightness": 10}}]}
```

```sh
pip install "cactus-needle[train]"                                                 # training deps (JAX, flax, optax)
export OPENROUTER_API_KEY=sk-or-...
needle generate-data --tools my_tools.json --num-samples 500 --output data.jsonl   # optional
needle finetune data.jsonl --epochs 3 --generate 300                                # LoRA; auto-downloads base
needle build checkpoints/needle3.safetensors --lora checkpoints/needle_lora.safetensors --out my.cact
```

Run a tuned model - the engine is weights-agnostic:

```python
agent = needle.Needle(weights="my.cact", tools=[...])
agent.run("...")
```

Options: `finetune --lora-rank 16 --lora-alpha 32 --lr 1e-4 --batch-size 16 --max-len 1024 --val-split 0.1 --checkpoint <base.safetensors or .pkl> --checkpoint-dir <dir> --out <adapter.safetensors or .pkl> --generate <n> --model <id> --workers <n>`; `--model` defaults to `deepseek/deepseek-v4-flash`, `--workers` defaults to `8`, and `--checkpoint-dir` defaults to `checkpoints`. `--generate` synthesizes extra examples through the configured OpenRouter endpoint before training. `build --bits 2|4 --upload` (with `NEEDLE_HF_REPO=<you>/<model>`).

## Playground (browser)

Hosted at https://cactuscompute.com/needle: preset demos, editable tools/prompt, multi-turn follow-ups, and a "Finetune on these tools" button that runs the pipeline above and returns a downloadable `.cact`. `needle playground [--weights my.cact]` serves the same UI locally at http://127.0.0.1:7860. Local fine-tuning is 4-bit; the 2-bit post-training and quantisation behind the shipped model, enriched with Cactus proprietary datasets, run on the Cactus Platform at https://cactuscompute.com/dashboard.

## Environments (ready-made tool surfaces)

`needle.environments` ships six: `smart_home`, `media_player`, `productivity`, `wearable`, `kitchen_appliance`, `data_capture`. Each module has `TOOLS`, `SYSTEM`, a lazily constructed `agent`, `TEST_CASES`, and `run_tests(min_confidence=0.0)`; `python -m needle.environments.smart_home` runs its frozen acceptance suite.

```python
from needle.environments import smart_home
smart_home.agent.complete("dim the study lights to 30 percent")
```

Adapt by swapping the Literal values for your own and keeping the shapes: closed sets as enums, bounded numbers, verbatim copy for free text, five tools or fewer.

## CLI summary

- `needle run --checkpoint <base.safetensors or .pkl> --query "..." --tools tools.json` - JAX reference inference from a checkpoint (dev path; normal inference is the Python `Needle` API above).
- `needle generate-data` / `needle finetune` / `needle build [checkpoint] [--lora adapter] [--layers N] [--platform <folder>] [--out <path>]` - the fine-tuning pipeline; fine-tuning runs at the full 20 layers, `build` merges the adapter, slices the `--layers` rung (default 20), exports at 4 bits, and fetches the published `needle3.cact` on every run (without an adapter at full depth it ships that published 2-bit archive as is). `--platform` also downloads that platform's engine and header and makes `--out` a folder holding them plus `needle3.cact`.
- `needle playground` - the browser UI locally (hosted at https://cactuscompute.com/needle).
- `needle fetch [--platform-tag <tag>] [--out <dir>]` - pre-download the inference engine for this machine (or another platform) into the cache; prints the path. For air-gapped devices, also see `NEEDLE3_LIB_PATH` and `HF_HUB_OFFLINE` at https://cactuscompute.com/blog/needle-python-docs.
- `needle download needle3 | needle3.safetensors | <org>/<repo>[/<file>.cact] | <platform> [--out <dir>]` - pull the base Needle 3 archive, a checkpoint to fine-tune, a published `.cact` (single-archive repos need only `<org>/<repo>`), or pass a platform folder name (`macos-arm64`, `linux-x86_64`, `wasm`, `wasm-component`, ...) to fetch that platform's engine files into `<out>/<platform>/`. Native runners are marked executable; `wasm-component` contains the WASI Preview 2 component and WIT contract.

## Common mistakes to avoid

- Do not expect free-text answers to arbitrary questions; unsupported input returns an empty call. Handle it.
- Do not read `arguments` keys that were not evidenced in the input; optional fields may be absent.
- Do not create one `Needle` per turn for a conversation; reuse the instance so context carries. New tools = new instance.
- `import needle` does not import JAX; only `needle finetune`/`build` do.
- `weights=` expects a `.cact` (from `needle build`), not a `.safetensors` or `.pkl` checkpoint. `Needle(tools=...)` runs the base Needle 3 archive (fetched once, cached next to the engine); pass `generation=2` for the embedded Needle 2 engine.
- Checkpoints and adapters are `.safetensors`; pickle checkpoints still load. The base is `checkpoints/needle3.safetensors` (20 layers); `needle build --layers N` exports any rung from 2 to 20 of it.
- The engine cannot unload weights: once a tuned `.cact` is bound, constructing or calling a base-model agent raises instead of silently answering with those weights. Construct agents that want the base model before any tuned one, or run them in separate processes.

## Telemetry

Anonymous usage counts only (function name, package version, OS, random install id - never prompts, outputs, or data). Opt out with `NEEDLE_TELEMETRY=0` or `DO_NOT_TRACK=1`; `CI` environments are excluded automatically.

## A3. pyproject.toml (dependencies and extras)

[project]
name = "cactus-needle"
version = "3.0.1"
description = "A 14MB foundation tool-calling model for tiny devices: inference, LoRA finetuning, and build."
requires-python = ">=3.9"
readme = "README.md"
license = { text = "Apache-2.0" }
dependencies = [
    "huggingface_hub",
]

[project.optional-dependencies]
train = [
  "numpy",
  "jax",
  "jaxlib",
  "flax>=0.10.2",
  "optax",
  "safetensors",
  "sentencepiece"
]
gpu = ["jax[cuda12]"]
metal = [
    "jax==0.4.38",
    "jaxlib==0.4.38",
    "jax-metal"
]
test = ["pytest", "pydantic"]

[project.scripts]

---

# Appendix B — the #42 pilot receipt and spike README (branch experiment/coding-core-pilot; not on main)

## B1. TESTS-RESULTS/2026-09-11-coding-core-pilot/SUMMARY.md

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

## B2. spike/coding_core/README.md

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

## State/transition pivot (2026-09-11)

A fixed phase-aware backoff classifier reached the 42% development gate, five points above
Markov-1, without training a model. It conditions on the last action, whether an edit occurred
before that action, and the penultimate action, then backs off to Markov-1. Raw issue-text features
were excluded because only 11 distinct training instances repeat across 500 rows, making task-text
memorization a larger risk than useful signal. This promotion result authorizes one frozen,
session-separated private evaluation; it is not itself a product-efficacy claim. That private check
subsequently failed: phase-backoff scored 25.23% against 28.78% Markov-1 and 43.52% repeat-last over
23,442 eligible actions from 63 sessions. The classifier arm is stopped; action persistence is the
only candidate signal that transferred.

## B3. spike/coding_core/labels.json

{
  "label_set_version": "coding-core-v0",
  "source": "Experimental projection; canonical Oracle v1 remains unchanged.",
  "labels": ["edit", "git", "read", "run_command", "run_tests", "search"],
  "schemas": [
    {"name": "edit", "description": "Edit or create source files.", "parameters": {"type": "object", "properties": {}}},
    {"name": "git", "description": "Inspect or change Git state.", "parameters": {"type": "object", "properties": {}}},
    {"name": "read", "description": "Read files or command output.", "parameters": {"type": "object", "properties": {}}},
    {"name": "run_command", "description": "Run a shell command not covered by another label.", "parameters": {"type": "object", "properties": {}}},
    {"name": "run_tests", "description": "Run tests, linters, or a build verification.", "parameters": {"type": "object", "properties": {}}},
    {"name": "search", "description": "Search code or find files.", "parameters": {"type": "object", "properties": {}}}
  ]
}
````
- Definition of Done: **Plan QA only — no execution, no edits outside this relay file.** The artifact is the body of HiQS-Labs/Needle-fork issue #66 (a plan to rerun the #42 six-action pilot on upstream Needle 3), followed by Appendix A (upstream Needle 3 reference excerpts, the ground truth for any claim about Needle 3) and Appendix B (the #42 receipt, spike README and labels, the ground truth for comparability). Operational envelope: a one-person experimental fork, a single bounded CPU fine-tune on a Mac Studio, a 100-row holdout, a public dataset; machinery and tests must stay commensurate with that — do not ask for sweeps, CI, distributed training, or private-corpus work. Non-goals are listed in the issue's "Out of scope" section and are not findings. Answer these questions, citing the artifact by section name and, where a claim is checked against an appendix, the appendix line:
  1. Every claim the plan makes about Needle 3 (retrieval cap, 4-bit local fine-tune, CLI flags and defaults, checkpoint/adapter formats, `--layers`, the enum/extraction classification path, parameter counts) — is each one supported by Appendix A? Flag any that Appendix A contradicts or does not support.
  2. Comparability with #42: does the frozen contract reproduce #42's data, split, holdout, labels and baselines exactly (Appendix B)? Is anything that changed versus #42 (answer shape, engine-native eval, 4-bit vs 2-bit QAT, top-1 only) named in the plan and in the receipt requirements, or is a difference hidden?
  3. Gates: is every step's gate falsifiable in advance? Is the 42% pass line (Markov-1 37% + 5pp) consistent with how the fork has applied its lift rule in #48 and #62? Is the step-time gate (step 5) concrete enough to stop an unattended multi-day run?
  4. Missing gates or preflight: what would SOP Step 2 ("preflight the DATA") still require that the plan omits — per-label support in the training split, abstention rows, token-length check, boilerplate fraction?
  5. Receipt publishability: given the fork's rule (aggregates only; no prompts, rows, weights or machine paths in Git; CC BY 4.0 attribution), does the deliverables list produce a receipt that could be committed as-is? Name any missing field.
  6. Branch and merge plan (step 1): is "take upstream `needle/` wholesale on conflict" safe for the fork's own tests and tooling, and is the #8 build-safety guard handled correctly, or does the plan need an explicit list of fork changes under `needle/` to check before discarding them?
  7. Scope creep or overbuild: does any step ask for machinery the envelope does not need? Conversely, is anything load-bearing missing (for example, how the pilot's serialized context is reused verbatim, or how an out-of-enum or empty answer is scored)?
  Grade each finding `[Blocker]` / `[Should]` / `[Nit]` / `[Pass]`; a `[Blocker]` or `[Should]` requesting a behaviour change carries `Observed input:`, `Affected scope:` and `Falsifier:` lines. Verdict Approved only if there is no `[Blocker]`.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

## agy (Reviewer) — QA Findings

swept file: yes

*   **[Blocker]** Parameter count and model sizes are conflated and unsupported.
    *   **Observed input:** The plan claims Needle 3 has "29-121M parameters" (line 69) and proposes a second rung "nearest 45M" (line 103).
    *   **Affected scope:** "Why now" and "Second rung" sections.
    *   **Falsifier:** Correct the conflation. Appendix A1 states "The whole model is a single 8-29 MB binary" (line 137) and references the "121M model" (line 145), but does not support 29M or 45M parameter sizes.
*   **[Pass]** The plan reproduces #42's data, split, holdout, labels, and baselines. All changed variables (answer shape, engine-native eval, 4-bit vs 2-bit, top-1 only) are explicitly named in the plan and receipt requirements (lines 84-89, 101-102).
*   **[Pass]** Every step's gate is falsifiable in advance (e.g., `pytest -q -m "not slow"` green [line 95], validation loss falls [line 100], and all 100 rows scored [line 102]). The 42% pass line and the step-time gate (line 99) are concrete and appropriate.
*   **[Should]** Preflight is missing data health assertions required by SOP Step 2.
    *   **Observed input:** Preflight checks only holdout label support (line 86) and token length (line 89).
    *   **Affected scope:** "Frozen comparison contract" section and step 3 gate.
    *   **Falsifier:** Add preflight assertions for training split per-label support, abstention rows, and boilerplate fraction.
*   **[Nit]** The receipt deliverables (line 104) rely on the vague "in the #42 format" to inherit the CC BY 4.0 attribution requirement. Explicitly name the CC BY 4.0 attribution link requirement in step 10 to ensure compliance with the repository rules.
*   **[Should]** Blindly taking upstream `needle/` wholesale on merge conflicts is unsafe.
    *   **Observed input:** "...if the merge conflicts inside `needle/`, take upstream's `needle/` wholesale for this branch" (line 95).
    *   **Affected scope:** Step 1 branch and merge plan.
    *   **Falsifier:** Provide an explicit list of known fork changes under `needle/` to review before dropping conflicts, to prevent silent loss of other fork-specific fixes.
*   **[Unverified — no citation]** No scope creep or overbuild detected. The plan stays within the bounded CPU envelope and handles load-bearing requirements cleanly (reusing verbatim context [line 117] and explicitly scoring empty/out-of-enum answers as misses [line 88]).

**Verdict:** Changes requested

handing off to Producer — go to the other window and say 'take your turn'

### claude-a (Producer) — round 1 dispositions, round 2 opened

The revised artifact is the live body of issue #66 and is seeded read-only in your worktree at
`.relay-artifacts/GH-66-needle3-pilot-plan.md`. **Read that file; it supersedes the embedded
round-1 copy above.** Its Appendix A now carries the sources the round-1 review could not see
(A0 `llms.txt` lines 1-4, A4 the 3.0.1 `finetune`/`build` parsers, A5 `rung()` and its call site,
A6 the Needle 2 parameter count, A7 the fork's exact delta under `needle/`).

- `[Blocker]` parameter figures conflated/unsourced — **Implemented.** "Why now" now cites each figure:
  "29-121M parameter" is `llms.txt` line 3 (Appendix A0); "starting at 29M parameters" is the README
  Customisation section (A1); "the 121M model" is the README architecture paragraph (A1); the
  "8-29 MB binary" is named as file size at ~2.1 bits/weight, not a parameter count; 45M is Needle 2's
  count from this fork's README (A6). Step 9 no longer guesses 8 layers: the rung is the depth whose
  parameter count, computed from the checkpoint via `rung()`/`ladder_slice`/`ladder_config` (A5), is
  nearest 45M, recorded with its neighbours in the receipt. It also states that in 3.0.1 `--layers` is a
  build-time slice called from `build_main` and that the `finetune` parser has no `--layers` despite the
  CLI banner (A4, A5), so the rung is exported from the step-6 adapter.
- `[Should]` preflight missing training-split support, abstention rows, boilerplate fraction —
  **Implemented.** Three new bullets in "Frozen comparison contract": training per-label support
  recorded, zero-row label = preflight failure, `git` reported not gated; abstention rows expected 0
  (the projection has no abstain label and `prepare_openhands.py` ends sequences at think/task/finish
  calls), converter refuses unlabeled rows, nonzero = failure; boilerplate fraction measured with
  `render_example`, reported min/median/max, caveat in the receipt above 50% of the median row.
- `[Should]` "take upstream `needle/` wholesale" unsafe — **Implemented.** Step 1 now measures the fork's
  delta under `needle/` against merge base `b5e2943`: exactly two hunks, 24 added lines, both the #8
  guard (`cli.py` `--allow-numerics-mismatch` +3; `finetune.py` `build_main` provenance detection and
  `ValueError` +21; Appendix A7). Rule: upstream's side of every `needle/` conflict, then re-port the two
  hunks by hand; the guard's `--qat-bits auto` remedy text no longer matches 3.0.1 (no such flag, A4), so
  if 3.0.1 adapters carry no provenance keys the build runs with `--allow-numerics-mismatch` and the
  receipt says so. Gate adds: `git diff upstream/main -- needle/` shows those two hunks and nothing else.
  The "Risks" line that referenced the wholesale rule is updated to match.
- `[Nit]` CC BY 4.0 attribution inherited from "the #42 format" — **Implemented.** Step 10 spells out
  dataset id, revision, licence, dataset-card link, authors as the card names them, and a "derived
  projection" statement.
- `[Unverified — no citation]` no scope creep — no change requested; the two load-bearing items it
  names (verbatim context reuse, empty/out-of-enum scored as miss) are unchanged.

No gate, decision or scope changed; a "Revised 2026-09-18" note at the top of the issue says so.

Round 2 ask: re-grade the revised artifact against the same Definition of Done. Verdict Approved if
no `[Blocker]` remains.

handing off to Reviewer — agy, take your turn

### agy (Reviewer) — QA Findings round 2

swept file: yes

*   **[Pass]** Parameter counts and model sizes are correctly sourced and disambiguated. Cited `issue66.md:20` for "a 29-121M parameter on-device model" and `issue66.md:57` for computing depth dynamically (`needle.model.finetune.rung`).
*   **[Pass]** Comparability with #42 is preserved, with differences explicitly named. Cited `issue66.md:35-40` for the contract, baselines, and constraints.
*   **[Pass]** Gates are falsifiable in advance. The 42% pass line and step-time gates are concrete. Cited `issue66.md:53` ("if a step exceeds ~5 minutes...").
*   **[Pass]** Preflight assertions now fully cover SOP Step 2 requirements. Cited `issue66.md:41-43` for training-split per-label support, abstention rows count 0, and boilerplate fraction measurement.
*   **[Pass]** Receipt publishability is satisfied. The CC BY 4.0 attribution is explicitly written out. Cited `issue66.md:58` ("Dataset attribution written out... `nebius/SWE-rebench-openhands-trajectories`, revision `35455389ab51bf5e2306bfd436ef72d0f98bf882`, licence CC BY 4.0...").
*   **[Pass]** The branch and merge plan is safe. The two specific hunks under `needle/` are identified for manual re-porting. Cited `issue66.md:49` ("take upstream's side of every `needle/` conflict, then re-port the two hunks by hand").
*   **[Pass]** No scope creep or overbuild detected. The plan stays within the bounded CPU envelope. Cited `issue66.md:71` ("reuses the pilot's serialized context verbatim") and `issue66.md:39` ("an empty `function_calls` list or an out-of-enum value counts as a miss").

**Verdict:** Approved

relay closed (Approved), no further turn needed

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
