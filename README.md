# HiQS Needle Oracle — project story

## TLDR

We’re exploring whether a tiny local model can suggest useful next steps during software work—including testing, Git actions, and project governance—cheaply enough to run alongside a larger coding assistant. We have built and exercised the training/export pipeline, assembled private activity traces, audited their labels, and tested neural and simple statistical predictors. Useful recommendations remain unproven: label noise, a training/serving mismatch, and poor transfer from public coding-agent data have limited results.

Training the lightweight predictors on our own sessions improved the phase-aware model to 45.73% versus 43.52% for “repeat the last action,” but it missed the agreed gates. We now test whether task text and the latest completed tool result improve prediction of the same six next-action categories, using a bounded OpenHands sample and automatic offline comparisons. The manual usefulness trial stopped for time burden with no ratings. No human acceptance rate or production-ready Oracle has been established.

## What we have tried and learned

Status: September 12, 2026. This is HiQS's experimental fork of [Cactus Compute's Needle](https://github.com/cactus-compute/needle). Experimental branches are not all merged into `main`; an implemented tool or passing test does not imply a validated recommendation model.

| Work | Result and consequence | Evidence |
|---|---|---|
| Architecture and integration reconnaissance | Mapped the training, export, runtime and hook boundaries; distinguished previous integration attempts from measured model capability. | [Architecture](ARCHITECTURE.md), [findings](FINDINGS.md) |
| 44-label software-work and governance vocabulary | Built and froze the label-name contract, semantic mapper, session-based extraction and shared query serialization. High mapping coverage alone did not establish label correctness. | [Oracle plan #1](https://github.com/HiQS-Labs/Needle-fork/issues/1), [label contract](oracle/labels-v1.json) |
| Apple Silicon training and export | CPU training was impractical at the original scale; the MLX spike exercised GPU training, parity checks and export. That establishes an engineering path, not recommendation usefulness. | [MLX lane #5](https://github.com/HiQS-Labs/Needle-fork/issues/5) |
| Model ranking versus actual serving | Early ranking results did not establish useful native behavior. The tested native contract retrieved only five of 44 declared tools. | [Serving mismatch #12](https://github.com/HiQS-Labs/Needle-fork/issues/12) |
| Label correctness and source qualification | A 399-row audit estimated 77.84% population-weighted correctness. Error analysis and scoped mapper corrections followed; new sources still require qualification. | [Correction experiment #25](https://github.com/HiQS-Labs/Needle-fork/issues/25), [cross-agent audit #37](https://github.com/HiQS-Labs/Needle-fork/issues/37) |
| Strict fresh evaluation preparation | The frozen sampler can select 541 of 1,000 required rows under its session caps and label quotas. This lane remains blocked and lower priority. | [#25](https://github.com/HiQS-Labs/Needle-fork/issues/25) |
| Six-action OpenHands LoRA pilot | On 100 development actions, trained with 500 actions, LoRA scored 27% top-1 versus 37% for Markov-1. The pilot stopped. | [Experimental PR #42](https://github.com/HiQS-Labs/Needle-fork/pull/42) |
| Cheap phase-aware transition classifier | Scored 42% on the OpenHands development set, then 25.23% on 23,442 private actions across 63 sessions. OpenHands-fitted Markov-1 scored 28.78%; repeat-last scored 43.52%. The transferred classifier stopped. | [Private result](https://github.com/HiQS-Labs/Needle-fork/issues/1#issuecomment-5639743768) |
| Separate work-purpose classification | ModernBERT features scored 57.5% purpose accuracy on 40 records versus 50% TF-IDF; TF-IDF had better macro-F1. Area classification and rejection remained inadequate for deployment. | [Classification experiment #31](https://github.com/HiQS-Labs/Needle-fork/issues/31) |
| External datasets and grounded augmentation | TAWOS lacked coverage for the full eight-purpose task. A separate open PR supplies training-only augmentation tooling; no model improvement has been measured from it. | [Data qualification #35](https://github.com/HiQS-Labs/Needle-fork/issues/35), [augmentation PR #43](https://github.com/HiQS-Labs/Needle-fork/pull/43) |
| Independent Astra/Fable review | Reframed repeat-last as the baseline to beat and identified the untested in-domain comparison. A failed transfer experiment does not establish that private-trained models fail. | [Current synthesis on #1](https://github.com/HiQS-Labs/Needle-fork/issues/1#issuecomment-5641167454) |
| Private-trained transition comparison | Fitted on 45,127 actions from 296 sessions. Phase-backoff scored 45.73% overall and 40.81% on conditional change destinations; required 48.52% and 40.86%. Neither family passed; this round stopped. | [Receipt](https://github.com/HiQS-Labs/Needle-fork/blob/7f521b449c9d0f8351fdfc32c8c7180a44cbcf9f/TESTS-RESULTS/2026-09-11-private-transitions/SUMMARY.md), [PR #48](https://github.com/HiQS-Labs/Needle-fork/pull/48) |

## Next milestone

**Revised approach: [context-aware next-action prediction #51](https://github.com/HiQS-Labs/Needle-fork/issues/51).** Keep the six labels, add task text and the latest already-completed tool observation, and compare automatically against action-only and shuffled-context controls. A bounded CPU-only experiment comes first; no new manual ratings, neural training campaign, or serving integration. See the [frozen protocol](PROJECT/2-WORKING/CONTEXT-NEXT-ACTION.md).

Manual discovery [#49](https://github.com/HiQS-Labs/Needle-fork/issues/49) stopped for operator time burden after one eligible request and zero ratings. This pivot changes the input representation; it does not relabel earlier failures as passes.

### Previous milestone — completed, not instructions to repeat

**The agreed in-domain milestone ran and failed its gates.** Private training improved phase-backoff over public-data fitting, but not enough to qualify it. See the [result and exact counts](https://github.com/HiQS-Labs/Needle-fork/blob/7f521b449c9d0f8351fdfc32c8c7180a44cbcf9f/TESTS-RESULTS/2026-09-11-private-transitions/SUMMARY.md).

The frozen rule required the same family to beat repeat-last by five points overall and a training-derived conditional destination baseline by ten points. Phase-backoff improved by 2.2012 and 9.9479 points respectively; Markov-1 improved by 0 and 7.1078 points. Neither passed. Ordinary action-change accuracy was 14.06% for phase-backoff and 0% for Markov-1; detailed session distributions remain private.

Per that rule, these two models stop at this representation. The operator authorized the different input-representation experiment in #51; serving is not the automatic next step. The evaluation partition is reused development evidence, not fresh confirmation. Conditional destination accuracy assumes a switch occurred; it does not establish detecting switches live. These scores measure agreement with recorded labels, not human acceptance or whether an action was advisable.

The [collaborator briefing](doc/oracle-collaborator-summary.md) provides the detailed qualifications and source index. [XYZ-forge #467](https://github.com/HiQS-Labs/XYZ-forge/issues/467) owns the overall arc; [Needle-fork #1](https://github.com/HiQS-Labs/Needle-fork/issues/1) tracks this implementation. [ROADMAP.md](ROADMAP.md) points to current work and [FINDINGS.md](FINDINGS.md) preserves investigation history.

## Repository readiness and next steps

Historical #48 evidence links pin its published commit. Current docs are reconciled on main.
Per operator instruction, new offline work uses scoped, tested commits and pushes directly to main;
a new branch/PR requires a concrete isolation or integration need.

The findings cleanup and project story (#44/#45), [branch hygiene rules (#46)](https://github.com/HiQS-Labs/Needle-fork/pull/46), [adapter build-safety guard (#8)](https://github.com/HiQS-Labs/Needle-fork/pull/8), and governance stack (#6/#10) are merged into `main`. Integration verification passed: 384 non-slow tests and 11 slow build/finetune tests; six tests were skipped. This validates the engineering changes, not Oracle recommendation usefulness.

1. **Active experiment:** run [#51's context-aware probe](PROJECT/2-WORKING/CONTEXT-NEXT-ACTION.md) on main. Prior [#48](https://github.com/HiQS-Labs/Needle-fork/pull/48) and [#42](https://github.com/HiQS-Labs/Needle-fork/pull/42) remain historical experiment PRs; no whole-branch promotion.
2. **Deferred augmentation review (previous step 4):** wait for the operator to release #43's testing hold, then review its results before any integration decision.

Adapter builds with missing or full-precision training provenance now require an explicit
`--allow-numerics-mismatch` override; compatible QAT and adapter-free builds are unchanged.

**PR #43 is on an explicit operator testing hold.** Do not merge or modify its branch until that hold is released. Merged historical branches remain preserved pending retirement checks; no blanket branch cleanup has been performed.

---

## Upstream Needle package and usage

The package description, benchmarks and usage documentation below describe upstream Needle. They are not results for this fork's experimental Oracle. Installing `cactus-needle` alone does not install a validated HiQS next-action assistant.

![Needle](assets/banner.png)

# Needle 2

Needle 2 is an open 45M-parameter model for tool calling, device use and structured extraction. The whole model is a single 14MB binary that runs a full session in about 28MB of RAM. It is built on our Simple Attention Network findings, compressed to CQ2-bit with Cactus Quants, and baked into its own engine. On the benchmarks below, Needle 2 trades wins with other small models like FunctionGemma 270M, LFM2.5 230M and Apple FM, at 5x to 70x smaller, and 2 bits against their f16.

This repository is the Python package: inference, LoRA fine-tuning, and export. `pip install cactus-needle`, describe your tools, and call them from Python. The inference engine is fetched once from Hugging Face and cached; there is nothing else to build, and offline setup for air gapped devices is covered in [doc/apis.md](doc/apis.md).

- **Self-contained**: weights baked into a single 14MB engine; no separate model files to manage, and inference does no network.
- **Simple contract**: tool calls come back as structured data, text in, JSON out; a byte-level grammar compiled from your schemas constrains every token.
- **Confidence-gated**: every response carries a calibrated confidence score from a learned head; set a threshold, act above it, escalate below it.
- **Tool retrieval**: declare a large catalogue and a built-in retrieval head renders only the top five tools per turn, with the grammar constrained to that subset.
- **Bounded memory**: a 256-token sliding window with the tools pinned as KV sinks, so total memory stays near 28MB no matter how long the conversation runs.

Weights: [huggingface.co/Cactus-Compute/needle2](https://huggingface.co/Cactus-Compute/needle2) &middot; source: [github.com/cactus-compute/needle](https://github.com/cactus-compute/needle).

![Size-quality frontier: mobile-class and below](assets/frontier.png)

## Simple Attention Network

Needle 2 is a Simple Attention Network, our dense small-model recipe: a Hadamard MLP in place of the FFN, GQA attention, engram key-value memory, and multi-lane hyper-connections. See the paper for the design and ablations: [arXiv:2607.18363](https://arxiv.org/abs/2607.18363).

![Simple Attention Network architecture](assets/architecture.png)

Each block carries its update rule. Here x̂ is the RMS-normalised flattening of the four residual streams, H the orthonormal Walsh-Hadamard transform (a fixed matrix, applied in n log n time with no weights to read), (kₜ, vₜ) rows gathered from hashed n-gram tables, and P the doubly-stochastic normalisation of the routing logits A, computed by Sinkhorn iteration; a, b, g and all σ-gates are learned and input-dependent. Both attention and MLP residuals are sandwich-normed and gated, the engram sites fire at two layers, and decoding is constrained by a byte-level grammar compiled from the declared schemas.

## Quickstart

```sh
pip install cactus-needle
```

The runtime package does not install the training stack. Add the `train` extra
when using fine-tuning or checkpoint export:

```sh
pip install "cactus-needle[train]"
```

Needle reads your tool descriptions to decide what to call and how to fill arguments, so describing them well is the whole game.

**Simple**: decorate a function. The signature gives the argument types, the docstring is the tool description, and `run()` completes the loop: model picks the call, Needle executes your function, feeds the result back, and returns the final response with the executed tool results attached as `results`.

```python
import needle

@needle.tool
def get_weather(city: str):
    "Get the current weather for a city."
    return {"city": city, "temp_c": 27, "sky": "clear"}

agent = needle.Needle(tools=[get_weather])
print(agent.run("what's it like in Lagos right now?")["results"])
# [{'city': 'Lagos', 'temp_c': 27, 'sky': 'clear'}]
```

**Extraction**: to pull structured data out of text, declare the shape and call `extract()`. Pass a Pydantic model and you get a typed object back.

```python
from pydantic import BaseModel

class Invoice(BaseModel):
    vendor: str
    total: float
    due_date: str

invoice = needle.extract("Invoice from Acme Corp, $1,200.00, due 2026-09-01", Invoice)
print(invoice.vendor, invoice.total)   # -> Acme Corp 1200.0
```

Per argument descriptions and choices, value constraints compiled into the decode grammar, raw JSON schemas, driving the loop with `complete()`, the response contract, system facts, tool retrieval, and confidence gating are all covered in [doc/apis.md](doc/apis.md).

## Playground

Try any model in the browser: pick a preset, edit the tools or prompt, and Run. Follow-up queries continue the same conversation.

```sh
needle playground                      # base model, http://127.0.0.1:7860
needle playground --weights my.cact    # a tuned model
```

The server downloads and initializes the model before serving, so the first query is instant. The **Finetune on these tools** button runs the fine-tuning pipeline below from the UI and hands back a downloadable `.cact`.

## Environments

Ready-made tool surfaces in `needle.environments`: `smart_home`, `media_player`, `productivity`, `wearable`, `kitchen_appliance`, and `data_capture`. Each is a hand-curated set of tools whose enums, bounds, and descriptions map cleanly onto Needle's constrained decoding, with a ready agent and a frozen acceptance suite.

```python
from needle.environments import smart_home

smart_home.agent.complete("dim the study lights to 30 percent")
smart_home.run_tests()
```

`python -m needle.environments.smart_home` runs a suite from the shell. To adapt an environment to your product, swap the `Literal` values (rooms, contacts, categories) for your own and keep the shapes: closed sets as enums, bounded numbers, verbatim copy for free text, five tools or fewer. The full tool surfaces and the suite contract are in [doc/environments.md](doc/environments.md).

## Fine-tuning

Needle fine-tunes with LoRA on the frozen base and merges the adapter at export, so a run is cheap and the tuned model is still a single `.cact` that runs on the same engine. The workflow is: (optionally) synthesize data, LoRA fine-tune, then build a tuned `.cact`. See [doc/finetuning.md](doc/finetuning.md) for dataset sizing, reading the loss curve, and troubleshooting.

**Data format.** A JSONL file, one example per line. `reasoning` is optional; an off-topic example has `answers: []`.

```json
{"query": "dim the kitchen to 10", "tools": [{"name": "set_lights", "parameters": {"type": "object", "properties": {"room": {"type": "string"}, "brightness": {"type": "integer"}}, "required": ["room"]}}], "answers": [{"name": "set_lights", "arguments": {"room": "kitchen", "brightness": 10}}], "reasoning": "'kitchen' -> room; 'dim to 10' -> brightness 10"}
```

**1. Synthesize data (optional).** Needs `OPENROUTER_API_KEY`. Seed from a tool schema file, or expand an existing set:

```sh
export OPENROUTER_API_KEY=sk-or-...
needle generate-data --tools my_tools.json --num-samples 500 --output data.jsonl
needle generate-data --augment data.jsonl --num-samples 500      # expand an existing JSONL
```

Set `OPENROUTER_URL` to use an OpenAI-compatible gateway instead of the default OpenRouter endpoint.

**2. LoRA fine-tune.** The base checkpoint auto-downloads from Hugging Face if you do not pass `--checkpoint`. `--generate N` first synthesizes N more examples from the tools in your data (also needs `OPENROUTER_API_KEY`).

```sh
needle finetune data.jsonl --epochs 10
needle finetune data.jsonl --epochs 10 --generate 300 --lora-rank 16 --lora-alpha 32
```

Key options: `--epochs` (default 3), `--lora-rank` (16), `--lora-alpha` (32), `--lr` (1e-4), `--batch-size` (16), `--max-len` (1024), `--val-split` (0.1), `--checkpoint <base.pkl>`, `--checkpoint-dir <dir>` (default `checkpoints`), `--out <adapter.pkl>`, `--generate <n>`, `--model <id>` (default `deepseek/deepseek-v4-flash`), and `--workers <n>` (default 8). `--generate` uses the configured OpenRouter endpoint to synthesize extra examples before training. The adapter is written to `checkpoints/needle_lora.pkl` by default. A validation loss prints each epoch from the held out split.

Training is plain JAX and runs on any accelerator jax supports. On an NVIDIA machine install the CUDA build and the same command trains on the GPU:

```sh
pip install "cactus-needle[train,gpu]"
```

On Apple Silicon the `metal` extra trains on the GPU:

```sh
pip install "cactus-needle[train,metal]"
```

**3. Build a tuned `.cact`.** Merge the adapter into the base and quantize. The base auto-downloads if absent.

```sh
needle build checkpoints/needle2.pkl --lora checkpoints/needle_lora.pkl --out my_needle.cact
```

Add `--bits 2` for a smaller model (by default the export follows the checkpoint's declared per-layer bit map, falling back to 4 when the checkpoint declares none), or set `NEEDLE_HF_REPO=<you>/<model>` and pass `--upload` to publish the `.cact`. The counterpart `needle download <you>/<model>/my_needle.cact` pulls a published archive on any machine, and `needle download <platform>` (e.g. `macos-arm64`) fetches that platform's engine runner.

**4. Run it.** The engine is weights-agnostic, so a tuned `.cact` runs on it directly - no recompilation:

```python
import needle
agent = needle.Needle(weights="my_needle.cact", tools=[...])
agent.run("...")
```

## Telemetry

Cactus Compute collects strictly anonymous usage telemetry (function name, package version, OS — never your prompts, outputs, or data); opt out with `NEEDLE_TELEMETRY=0` or `DO_NOT_TRACK=1`.

## Citation

Needle 2 is built by the Cactus Compute team. If you use it in your work, please cite:

```bibtex
@misc{needle2_2026,
  title        = {Needle 2: A 45M-Parameter Foundation Tool-Calling Model for Tiny Devices},
  author       = {Ndubuaku, Henry and Mosoyan, Karen and Mroz, Jakub and Cylich, Noah and
                  Kumar, Satyajit and Sandhu, Parkirat and Shemet, Roman and Lee, Justin H.},
  year         = {2026},
  organization = {Cactus Compute, Inc.},
  howpublished = {\url{https://github.com/cactus-compute/needle}}
}
```

Reach out on founders@cactuscompute.com for partnerships, collaborations, synergies and deploying Needle2 in your product.
