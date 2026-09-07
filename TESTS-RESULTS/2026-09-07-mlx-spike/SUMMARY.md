# GH-5 MLX fine-tuning spike — MBP 14" M4 Pro

**Date:** 2026-09-07 · **Machine:** noel's MacBook Pro 14" (Apple M4 Pro, 12 cores / 16 ANE, 25.8 GB, macOS 15.6)
· **Branch:** `spike/mlx-finetune` · **Issue:** [#5](https://github.com/HiQS-Labs/Needle-fork/issues/5)

Side quest. Nothing here is Phase 2 work and nothing here lands on `main`.

## Gate status

| Gate | Result |
|---|---|
| **P0** environment | **PASS** — `mlx` 0.32.2 on `Device(gpu, 0)`, 8,931 GFLOP/s fp32 |
| **P0** JAX/CPU baseline | see `p0-jax-baseline.json` |
| **P1** tiny-fixture parity | **PASS in fp32** — max \|Δlogits\| **4.172e-07** vs a stated 1e-4, argmax agreement 100% |
| **P1** falsification | **3 of 4** injected faults caught; one gap recorded below |
| **P2** real-checkpoint parity | **PASS on a restated (relative) criterion** — see P2 below. Relative 2.67e-05, argmax 100%, top-3 99.98%. The literal 1e-4 **absolute** gate is unreachable by construction. |
| **P2** falsification | **3 of 4** caught on the real model, including the Sinkhorn fault the tiny fixture missed |
| P3–P4 | not yet run |

## P0 — environment

| | |
|---|---|
| `mlx` | 0.32.2, `mlx.core.default_device()` = `Device(gpu, 0)` |
| MLX GPU smoke | 2048³ fp32 matmul, 10 reps: **1.92 ms**, **8,931 GFLOP/s** |
| `jax.default_backend()` | **`cpu`** — as `doc/finetuning.md` states, `jax-metal` is not viable, so JAX means CPU here |
| JAX / Flax / optax | 0.10.2 / 0.12.8 / 0.2.8, Python 3.11.15 in an isolated `.venv-mlx-spike` |

The venv is deliberate: MLX is installed **only** there, never in the system interpreter, so it
cannot become an implicit dependency of `main` (issue #5 bound).

### Corpus

`data/corpus/oracle-train.jsonl` was **not** present on this laptop, so it was built —
**not re-extracted**. The extractor was never run against this machine's own `~/.claude`
(it would silently yield a different, smaller corpus). Input was the Studio-derived
v1 corpus already on disk at `data/corpus-v1/pairs.jsonl`:

```
python3 utils/corpus/build_oracle_jsonl.py --pairs data/corpus-v1/pairs.jsonl \
        --out-dir data/corpus --check-max-len
```

| | |
|---|---|
| train / holdout rows | 61,629 / 13,280 (session-level split inherited as-is) |
| longest rendered row | **1,950 tokens** against the 2,048 cap — no row truncates |
| labels present | 43 of 44 |
| **abstain rows (`"answers": []`)** | **0 in both splits (0.00%)** — see finding below |
| fixed P0/P3 subset | first 2,000 rows, `sha256[:16] = 522283369fd4005e` |

### 🚨 Finding: the corpus has zero abstain rows

`doc/finetuning.md:22` — *"Include off topic examples with `"answers": []`. The built in
generator produces about 1 in 8. **Without them the tuned model calls a tool on everything.**"*
This corpus has **none**, in either split, and `no_action` has no support.

It is structural rather than a converter bug: every pair in `pairs.jsonl` is a real tool call,
so there is nothing to convert into an abstention. Consequences for the main lane — a model that
can never abstain, a **vacuous** abstention precision/recall in #1 §5 (no holdout positives), and
an every-turn hook that fires on every turn, which #1 §6 names as worse than silence. Reported to
#1; out of bounds to fix here.

`data/corpus/pairs.jsonl` on this laptop is the **stale pre-v1 corpus** (`label_raw`/`label_merged`,
no `label`), which `serialize.to_finetune_row` cannot consume. That is a local staleness, not a
defect in `main`; noted so the next session does not point `--pairs` at it by default.

## P1 — forward-pass parity on the tiny fixture

The full forward pass is ported in `spike/mlx/san_mlx.py`: `ZCRMSNorm`, RoPE, the Engram
uint32 n-gram hash + table gather + tap convolution, GQA `MultiHeadAttention` with q/k
`ZCRMSNorm`, `HadamardMLP` over Walsh matrices, `Block`, and the MHC lane machinery
(`hpre`/`hpost`/Sinkhorn residual mixing) with per-layer weights sliced off axis 0 where
`nn.scan` stacked them.

### The tolerance, stated — not relaxed

The gate asks for a tolerance stated explicitly. **The fixture's own config defaults to
`bfloat16`**, and the 1e-4 in the plan is written as an *fp32-vs-fp32* number. Both are
reported, and `parity_check.py --dtype` makes each reproducible:

| activation dtype | max \|Δlogits\| | relative | argmax agreement | vs 1e-4 |
|---|---|---|---|---|
| **float32** | **4.172e-07** | 4.94e-07 | **100%** | **PASS** (240× inside) |
| bfloat16 (fixture default) | 8.570e-03 | 9.74e-03 | **100%** | over |

The bf16 number is **not** a port defect. bf16 carries ~8 mantissa bits, so its epsilon is
≈3.9e-3 and a relative error of 9.7e-3 is the expected accumulation of independent rounding
between two runtimes. Argmax agreement stays 100%, i.e. the two models make identical
predictions. Reported rather than buried, because a bf16 GPU training path would have to be
re-checked against this number, not against the fp32 one.

### Proving the check is not vacuous

`AGENTS.md` §6 — a check that cannot fail is decorative. `spike/mlx/falsify_parity.py`
injects faults into the MLX side only (fp32, atol 1e-4):

| injected fault | max \|Δ\| | |
|---|---|---|
| *control:* perturb a weight **both** sides read | 4.172e-07 (unchanged) | confirms both read the same weights |
| RoPE sin sign flipped | 5.498e-01 | **caught** |
| Engram indices shifted +1 | 6.360e-02 | **caught** |
| `_rms_unit` epsilon 1e-6 → 1e-2 | 3.524e-03 | **caught** |
| Sinkhorn 20 → 3 iterations | 1.174e-05 | **NOT caught** |

**The harness is insensitive to Sinkhorn iteration count at this scale** — 3 iterations already
converge closely enough on a 2-lane / 2-layer fixture that the difference hides under 1e-4.
Recorded rather than hidden: it means P1 passing does **not** prove the Sinkhorn loop count
matches, and P2 on the real checkpoint (27 layers, 4 lanes) is where that would surface.

## Caveats

- P1 is the **tiny random-init fixture**, 2 layers / 2 lanes / d_model 64. It proves the port's
  math, not its behaviour at the real model's scale. That is P2.
- The port implements the **non-flash** attention path. The tiny fixture sets `flash=False`; if
  the real checkpoint sets `flash=True`, JAX uses `jax.nn.dot_product_attention` and any
  difference there will show up in P2.
- The quantisation path (`_aq`, `maybe_quant_kv`) is **not** ported — under `quant=False` both
  are the identity in JAX, so P1 does not exercise them. `--qat-bits auto` is P2/P3 scope.
- Receipts carry aggregates only. No corpus rows, prompt text or commands.

---

## P2 — parity on the real `needle2.pkl` (27 layers, 4 lanes, fp16 weights)

### Verdict: PASS, on a criterion I restated and am flagging rather than burying

**The literal gate — max |Δlogits| ≤ 1e-4 absolute — fails, and no correct port could pass it.**
The real model's logits reach **2,322–9,643** depending on sequence length, so 1e-4 absolute is a
**relative 1.1e-8 to 4.3e-8** — below fp32 machine epsilon (1.19e-7). The tolerance was written
for the tiny fixture, whose logits are ~0.89.

| seq | max \|Δ\| | \|logits\|max | **relative** | argmax | top-3 |
|---|---|---|---|---|---|
| 32 | 6.567e-02 | 2,322 | 2.828e-05 | 100% | 100% |
| 128 | 1.963e-01 | 7,789 | 2.520e-05 | 100% | 99.87% |
| 512 | 2.002e-01 | 9,262 | 2.162e-05 | 100% | 100% |
| 512 (2 batches, receipt) | 2.573e-01 | 9,643 | **2.669e-05** | **100%** | 99.98% |

**Relative error does not grow with sequence length** — 2.8e-05 → 2.2e-05 from seq 32 to 512.
That rules out an accumulating bug.

### Why the residual exists — measured, not assumed

The real checkpoint stores **float16** params; the tiny fixture stores float32. Casting the same
real weights to float32 and re-running:

| params | max \|Δ\| | relative |
|---|---|---|
| as stored (float16) | 2.594e-02 | ~3.5e-06 |
| cast to float32 | **3.054e-04** | **4.1e-08** |

4.1e-08 relative is machine-exact. **The port is correct; the residual is fp16 rounding order
differing between two runtimes**, which is not something a port can or should eliminate. For
scale: fp16 epsilon is 9.77e-04, so the observed 2.7e-05 is ~35× *below* the precision of the
weights themselves.

### The gate found two real port bugs

Both were invisible on the float32 fixture and only appeared against fp16 weights:

1. **`ZCRMSNorm` computed `1 + scale` in float32.** JAX evaluates it in the *param's* dtype.
   With fp16 params, `1 + scale` resolves to ~1e-3 near zero, so upcasting first made the port
   **more accurate than the reference** — a silent mismatch. This was the dominant term.
2. **`attn_gate` applied sigmoid in float32.** JAX applies it in the param dtype, then casts.

### Ruling out the two limits carried from P1

- **`flash=True` is NOT the cause.** The real checkpoint omits `flash` from its config, so the
  dataclass default `True` applies — confirmed. But forcing `flash=False` gives a *byte-identical*
  delta (2.2363e-01 both ways), so JAX's `dot_product_attention` and its manual path agree, and
  the port's manual-only implementation is sound. **F3 limit 1 closed.**
- An 11-way config ablation on random float32 weights — `mhc_lanes=4`, `flash=True`,
  `rope_theta=1e5`, `max_seq_len=2048`, `kv_window=256`, `act_bits`/`kv_bits`, `weight_bits`,
  explicit `attn_dim`, `num_layers=27`, and the full real shape (d_model 512 / h8 / kv4) — **all
  pass at ≤1.9e-06**. No architecture feature is mishandled.

### Falsification at real scale — F2 resolved, and a new gap

Injected faults, MLX side only, threshold scaled to the model's logits (rtol 1e-4 → atol 0.232):

| injected fault | max \|Δ\| | tiny fixture | **real checkpoint** |
|---|---|---|---|
| *control:* weight both sides read | 6.567e-02 (unchanged) | — | — |
| RoPE sin sign flipped | 6.106e+01 | caught | **caught** |
| Engram indices shifted +1 | 6.136e+01 | caught | **caught** |
| **Sinkhorn 20 → 3 iterations** | **3.365e+02** | *not caught* | **CAUGHT** (5,000× clean) |
| `_rms_unit` epsilon 1e-6 → 1e-2 | 6.470e-02 | caught | **not caught** |

**F2 is resolved exactly as predicted:** the Sinkhorn iteration count is unverifiable on a
2-layer/2-lane fixture and is verified on the real 27-layer/4-lane model.

**New finding (F4): the two fixtures catch different faults.** The real model's activations make
`_rms_unit`'s epsilon negligible, so that fault hides there — while the tiny fixture catches it.
Neither alone is sufficient; **falsification must run on both**, and the P1 and P2 receipts should
be read together rather than treating the later one as superseding the earlier.
