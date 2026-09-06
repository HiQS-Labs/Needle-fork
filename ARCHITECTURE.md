# Architecture

High-level map of `needle-fork` (package: `cactus-needle`), produced via a 3-lane parallel recon (Sonnet subagents) over the codebase-memory knowledge graph plus direct source reads. 810 nodes / 3046 edges indexed; 40 Python files, 4 static playground assets.

## What it is

A 14MB tool-calling foundation model ("needle") for tiny/edge devices, plus the full toolchain around it: JAX/Flax training and quantization, a compiled native inference engine invoked from Python, LoRA finetuning, CLI, and a local playground UI. Single runtime dependency: `huggingface_hub`. Training/GPU/Metal support is opt-in via `pyproject.toml` extras (`train`, `gpu`, `metal`).

## Entry points

| Entry point | File | Reached via |
|---|---|---|
| `needle.cli:main` | `needle/cli.py` | `pyproject.toml` console script `needle` |
| `run.main` | `needle/model/run.py` | `needle run` |
| `export.main` | `needle/model/export.py` | **dead code** — not wired to CLI or `pyproject.toml`; `needle build` uses `finetune.build_main` instead |
| `playground.server:main` | `needle/playground/server.py` | `needle playground` |

`needle/cli.py` is a hand-rolled `argparse` dispatcher (subcommands: `run`, `finetune`, `generate-data`, `build`, `download`, `fetch`, `playground`). Every dispatched command fires a telemetry ping (`needle/_telemetry.py`) before running. Import of `needle.cli` has a side effect: it installs an XLA/absl log-noise filter unconditionally at module load.

## The three layers

### 1. Model / inference core (`needle/model/`)

- **`architecture.py`** — the model, a Flax `linen` module `SimpleAttentionNetwork`. Not a plain transformer: `HadamardMLP` replaces the FFN with a Walsh-Hadamard-transform (no learned dense matrix), `Engram` is a hashed n-gram embedding side-channel injected into specific layers, and `Stack` mixes parallel residual lanes via a Sinkhorn-normalized "mHC" gate. GQA attention with RoPE and sigmoid-gated output. Two presets: `needle` (d_model=768, 27 layers) and `base` (d_model=512, 27 layers).
- **`run.py`** — no-KV-cache decode (`generate`/`batch_generate`): re-runs the full buffer through `model.apply` every step, O(n²), used for simple/direct generation and confidence/entropy introspection.
- **`decode.py`** — the real inference path: a hand-rolled, KV-cached mirror of the architecture math (`forward_cached`, jitted), plus a `pmap`-parallel batched rollout (`batched_generate`) built for RL/finetuning-style sampling. It manually re-walks the Flax param pytree by hardcoded key paths — a change to `architecture.py`'s module tree silently breaks this file.
- **`quantize.py`** — two schemes: simple fake-quant (QAT) and "CQ" (Hadamard-rotated Lloyd-Max codebook vector quant, 2/3/4-bit + 1.58-bit ternary). Wired directly into `architecture.py`'s forward pass for training, and reused by `export.py` so QAT numerics match the deployed binary.
- **`export.py`** — packs a checkpoint into the deployment `.cact` binary format using the same codebooks as `quantize.py`. Reached only via `finetune.build_main` (`needle build`).
- **`finetune.py`** — two bundled responsibilities: synthetic training-data generation via the OpenRouter API (`needle generate-data`), and local LoRA finetuning over attention projections (`needle finetune`), with QAT noise applied during training. Also owns `render_example`, the chat-template prompt builder that `run.py` depends on.

### 2. Runtime SDK, agent tooling, environments

- **`needle/__init__.py`** — the `Needle` class, the public SDK surface (`complete`, `embed`, `run`, `reset`). Binds the native `libneedle` engine via `ctypes`, either as a process-global singleton (default) or, when custom `weights=` (a tuned `.cact`) is passed, isolated in a subprocess.
- **`needle/_worker.py`** — that subprocess primitive (`FineTuneWorker`): spawns itself as a child process, speaks length-prefixed JSON over stdin/stdout, loads the native library in the child. Explains its graph shape (high fan-in, zero fan-out) — every `Needle` method has a `self._worker` branch.
- **`needle/agent/tools.py`** — the tool-schema compiler: `@needle.tool`, `Field`, `build_schema` introspect Python signatures + docstrings + type hints into JSON-schema tool specs for constrained decoding. Pure stdlib, no I/O.
- **`needle/agent/fetch.py`** — despite the package name, this is unrelated to "agents": it's the engine-binary/weights downloader (HuggingFace Hub), called by `needle download`/`needle fetch` and by `needle/__init__.py`'s library-path resolution.
- **`needle/environments/`** — 6 duck-typed example modules (`smart_home`, `media_player`, `productivity`, `wearable`, `kitchen_appliance`, `data_capture`), each declaring `TOOLS`/`SYSTEM`/`TEST_CASES` and a lazy `agent` singleton via `_harness.py`. Covered by a contract suite (`tests/test_environments.py` — registry/module agreement, tool surface, test-case categories, tool execution), but **not imported by the CLI, the SDK, or the training code** — at runtime they are invoked manually (`python -m needle.environments.<name>`) or from the README/`doc/environments.md` examples.

### 3. Playground (local dev UI)

`needle/playground/server.py` is a stdlib `ThreadingHTTPServer` serving static `index.html`/`app.js`/`style.css` plus 7 JSON/binary routes (`/model`, `/load-model`, `/complete`, `/reset`, `/finetune`, `/finetune/status`, `/download/<name>`). Fully local — no remote backend; `/finetune` spawns a background thread running the same `generate_dataset` → `finetune_local` → `build_main` pipeline as the CLI, then hot-swaps the loaded model. No dedicated test file covers the HTTP layer itself.

## Cross-cutting contracts

- **Checkpoint format** (`format_version: 2`, `{params, config, step, run}` pickle) — the contract between `finetune.py` (writer) and `run.py`/`export.py` (readers).
- **`.cact` binary format** — documented in `export.py`'s module docstring; the boundary between the Python training/export side and the native C engine.
- **LoRA adapter dict** (`{lora, scale, base, rank, qat_bits, qat_bits_map}`) — between `finetune_local` and `build_main`.
- **Environment variables** (verified by sweeping every `os.environ`/`getenv` call under `needle/`):
  - Telemetry (`needle/_telemetry.py`): `NEEDLE_TELEMETRY=0`, `DO_NOT_TRACK`, or `CI` disable it; `NEEDLE_TELEMETRY_URL` overrides the endpoint.
  - Native engine (`needle/__init__.py:47,51`): `NEEDLE{generation}_LIB_PATH`, falling back to legacy `NEEDLE_LIB_PATH`.
  - Finetuning (`needle/model/finetune.py:26,81,489`): `OPENROUTER_URL`, `OPENROUTER_API_KEY`, `NEEDLE_HF_REPO` (upload target for `needle build --upload`).
  - Set as defaults, not read as config: `TF_CPP_MIN_LOG_LEVEL` / `GRPC_VERBOSITY` (`needle/cli.py:109-110`, XLA log noise), `ENABLE_PJRT_COMPATIBILITY` (`needle/model/finetune.py:13`, must precede JAX backend init), `NEEDLE_STRICT_VALIDATE` (`needle/environments/_harness.py:12`).

## Build & release

`pyproject.toml`: package `cactus-needle`, Python `>=3.9`, single runtime dep `huggingface_hub`. `.github/workflows/release.yaml` runs a **daily automated PyPI release train**: cron-gated to fire once at ~09:00 Pacific (or manual dispatch), runs `pytest -m "not slow"`, auto-bumps patch version from the latest git tag, builds, publishes to PyPI, and pushes a new tag — skips entirely if nothing changed.

## Test coverage shape

15 test files under `tests/` cover: build/export, environments contract, fetch/lib-path resolution, finetune pipeline, data generation, inference, LoRA target selection, the runtime-vs-train dependency split (`test_packaging.py`), the release workflow's git logic, prompt rendering/building, tool-schema decorator, weights/checkpoint loading, and the `_worker.py` subprocess. **Gap**: no test references the playground at all (`rg 'playground|_Handler|load-model|finetune/status' tests/` returns nothing), so the HTTP layer is covered only indirectly, through the finetune/engine functions its routes call.

## Known dead code

- `needle/model/export.py:536` (`def main(args)`) — unreferenced: not wired into `needle/cli.py`, not in `pyproject.toml`'s `[project.scripts]`, and the module has no `if __name__ == "__main__"` block, so there is no `python -m` path to it either. `needle build` reaches export through `finetune.build_main` → `export.write_export` instead. The rest of `export.py` is live: `write_export` is called from `needle/model/finetune.py:441,479`, and `read_export`/`write_export` are exercised by `tests/test_build.py` and `tests/test_finetune.py`.
