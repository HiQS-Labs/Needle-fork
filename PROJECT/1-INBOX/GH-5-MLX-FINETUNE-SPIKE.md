---
title: "GH-5 — MLX fine-tuning spike (side quest, MBP 14\" M4 Pro only)"
status: In progress
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
| **§5 harness built and run** (`spike/mlx/eval_oracle.py`). First model scoring in this repo. On 200 holdout rows: tuned **top-1 22.00%** vs static 12.50% (**significant**, z≈2.51) but **top-3 46.00% vs static 44.00% — NOT distinguishable** (+4 rows, CI ±6.91pp). Untuned base control scores 3.50% / 17.00%, so training clearly worked; what is unproven is whether it beats guessing the three commonest labels. Receipt: `TESTS-RESULTS/2026-09-07-oracle-eval/`. | **A 1,000-row run** (launched 21:01, ~4 h) to separate two readings: n=200 is too small, or **top-3 is a weak gate** for a distribution where three labels dominate and static starts at 44%. If the latter holds, it is a finding about the metric in #1 §5, not about the model. |

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

- [x] **PASS** — `mlx` 0.32.2, `mx.default_device()` = `Device(gpu, 0)`; GPU smoke 2048³ fp32 matmul ×10 → 1.92 ms, **8,931 GFLOP/s**. `jax.default_backend()` = `cpu`, as `doc/finetuning.md` predicts.
- [~] **IN FLIGHT** — JAX/CPU baseline: `needle finetune` on the fixed 2,000-row subset, `--max-len 2048`, 1 epoch. ~10 min of JAX compilation before step 1; 113 steps at batch 16. Wall-clock, peak RSS and final loss land in `p0-jax-baseline.json`.
- Gate: both recorded in `TESTS-RESULTS/2026-09-07-mlx-spike/`. Environment half done; baseline half pending.

### P1 — Forward-pass parity on the tiny fixture

- [x] Ported all blocks to `spike/mlx/san_mlx.py`. Per-layer weights are sliced off **axis 0**, where `nn.scan(variable_axes={"params": 0})` stacked them — the documented trap, and the mapping is explicit in the module docstring.
- [x] `parity_check.py --tiny` — **PASS in fp32**: max |Δlogits| **4.172e-07**, argmax agreement **100%**.
- [x] `falsify_parity.py` — the check is **not vacuous**: 3 of 4 injected faults caught (see Findings F2).
- Gate: **met in fp32.** The tolerance is stated in Decision D1 below, not hand-waved, and both dtypes are reported.

### P2 — Parity on the real base checkpoint

- [x] **PASS on a restated criterion (Decision D4).** Relative 2.669e-05 at seq 512, argmax 100%,
      top-3 99.98%. The literal 1e-4 *absolute* gate is unreachable by construction — the real
      model's logits reach 2,322-9,643, so 1e-4 absolute is a relative 1.1e-8 to 4.3e-8, below
      fp32 machine epsilon.
- [x] Cause of the residual identified and **local to the port**, so not a no-go: the real
      checkpoint stores **fp16** params. Casting the same weights to fp32 gives 3.054e-04
      absolute = **4.1e-08 relative**, i.e. machine-exact. The residual is fp16 rounding order
      between two runtimes, ~35x *below* fp16's own epsilon (9.77e-04).
- [x] **Two genuine port bugs found and fixed**, both invisible on the fp32 fixture — see D4.
- [x] Relative error is **flat across seq 32/128/512** (2.8e-05 -> 2.2e-05), ruling out accumulation.
- [x] `flash=True` confirmed on the real checkpoint (absent from its config, so the dataclass
      default applies) and **ruled out as the cause** — forcing `flash=False` gives a byte-identical
      delta. **F3 limit 1 closed.**
- [ ] Quant-aware path (`--qat-bits auto`) still unexercised — `parity_check` runs `quant=False`.
      Carried into P3/P4 as F3 limit 2.

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

---

## Scope boundary: this spike tests **MLX on the GPU. It does not touch the ANE.**

Stated first because misreading it is the expensive mistake. Umbrella
[XYZ-forge#467](https://github.com/HiQS-Labs/XYZ-forge/issues/467) goal 1 is *"shift the
baseline governance routing entirely to the M1 Max ANE"*, so "the MLX spike passed" is very
easy to hear as "the ANE path is proven." **It is not, and it cannot be.**

| question | answer |
|---|---|
| Is Needle's forward pass running under MLX? | **Yes** — ported and verified at fp32 max \|Δlogits\| 4.172e-07 (P1). |
| Is Needle *training* under MLX? | **Not yet** — that is P3 (LoRA loop) and P4 (full epoch). |
| Is any of this "recompiling" Needle? | **No.** `san_mlx.py` is a hand-written re-implementation of `architecture.py`, weight-compatible with the same checkpoint. Nothing is compiled from the JAX source. |
| Is any of this running on the **ANE**? | **No.** |
| Could MLX reach the ANE? | **No.** `mlx.core.DeviceType` exposes exactly `['cpu', 'gpu']`; `mx.default_device()` is `Device(gpu, 0)`. MLX has no Neural Engine backend, so no MLX result — however good — is evidence about the ANE. |

**The ANE path is Orion's**, tracked in [Orion-fork#1](https://github.com/HiQS-Labs/Orion-fork/issues/1)
(CoreML/ANE runtime), and it inherits its own constraint from Phase 1: fp32 program I/O is
rejected by M1-generation ANE and accepted by M4, so ANE work must design fp16-only program
boundaries. That is a different runtime, a different repo, and a different set of gates.

What a **go** on this spike would actually buy: faster *training* iteration on Apple Silicon GPU
for Phase 3/4, and a second numerically-verified implementation of the forward pass. It buys
**nothing** toward ANE inference.

---

## Decisions — codified 2026-09-07 (MBP session)

Recorded here **and** at the place each one bites, because this spike runs on one machine
while Phase 2 runs on another and a decision that lives in only one of them gets re-litigated
or, worse, silently contradicted.

### D6 — Build the eval harness before the QAT port, and before P4

**Decided 2026-09-07 after P3, under /ponytail + /debug-mantra.** The question put was
"port the CQ STE quantisation-aware path to MLX, or run a matched fp32 JAX baseline?"
**The answer is neither, yet.**

**First, a correction to this document's own earlier sizing.** P3's report and #7 both said a
second runtime "must reimplement the Lloyd-Max codebook, the Hadamard rotation and the
nearest-codeword search". Measured, that is wrong:

| Probe | Result |
|---|---|
| `cq_ste` (`quantize.py:354`) | **one line** — `w + stop_gradient(cq_quantize(w) - w)` |
| `_cq_codebook_np`, `_cq_hadamard_np` | `@lru_cache` **numpy constants**, keyed only on `(bits, group_size)` |
| `cq_quantize` | ~12 lines of array math |
| MLX ops needed | `searchsorted`, `pad`, `argmin`, `stop_gradient` — **all present** |

The codebook and the Hadamard matrix do not depend on the weights, so they are **imported, not
ported**. The real port is ~25 lines. The earlier estimate was off by an order of magnitude and
was about to drive a decision.

**But the port still is not next**, for a reason the sizing error was hiding. Ponytail rung 1 —
*does this machinery need to exist at all?* — is **unanswerable today**, because:

- **There is no model evaluation anywhere in this repo.** No top-3 scorer, no holdout accuracy.
- `measure_taxonomy.py`'s "baseline top-3" is the **static majority-class frequency** — the bar
  the model must beat, computed from label counts alone. It never runs a model.

So porting QAT would produce an adapter whose benefit cannot be quantified. **That is the actual
rabbit hole: not the port's size, but shipping an unverifiable artifact.** It is also why the
45.99% bar cannot currently be claimed as cleared, however well training goes.

**The eval harness is therefore next**, because it:

1. is required regardless of which way the QAT question falls — it is #1 §5, an explicit
   requirement, not speculative work;
2. **converts the QAT question from an argument into a measurement**: score the *same* adapter
   fp32-merged and CQ-exported; the delta is the answer;
3. is the gate on shipping anything at all;
4. may retire the QAT port entirely, at no cost, if the PTQ delta proves small.

Deferring a ~25-line port costs almost nothing. Deciding it by argument costs the whole lane.

**Ponytail bound on the harness itself:** subsample the 25,684-row holdout for a decision-grade
signal rather than scoring all of it, and say so in the receipt.

### D1 — Parity tolerance: fp32 is the gate, bf16 is measured and reported

**The 1e-4 in this plan is an fp32-vs-fp32 number, but the fixture's config defaults to
`bfloat16`.** Both are reported; neither is quietly dropped.

| activation dtype | max \|Δlogits\| | relative | argmax | vs 1e-4 |
|---|---|---|---|---|
| **float32** | **4.172e-07** | 4.94e-07 | 100% | **PASS**, 240× inside |
| bfloat16 (fixture default) | 8.570e-03 | 9.74e-03 | 100% | over |

bf16 carries ~8 mantissa bits (epsilon ≈3.9e-3), so 9.7e-3 relative is the expected
accumulation of independent rounding between two runtimes — **not** a port defect. Predictions
are identical either way.

**The rule:** judge the *port* in fp32; judge a *bf16 GPU training path* against the bf16
number. Never relax `--atol` to make a run pass.
*Also codified in:* `spike/mlx/parity_check.py --dtype` help text, `TESTS-RESULTS/2026-09-07-mlx-spike/SUMMARY.md`.

### D2 — MLX is installed only in an isolated venv

`.venv-mlx-spike` (Python 3.11), never the system interpreter. `python3` on this laptop is
3.14 and has no `pip` on PATH; `python3.11 -m pip` works.

`.venv-mlx-spike/` is excluded via **`.git/info/exclude`, not `.gitignore`** — `.gitignore` is
outside this branch's bounds (only `spike/mlx/` and this doc may change). That exclusion is
**local to this clone** and will not travel; another clone must redo it.

### D3 — The corpus is built here, never re-extracted here

`data/corpus/oracle-train.jsonl` did not exist on this laptop. It was built from the
**Studio-derived** v1 corpus already on disk. The extractor was **never** pointed at this
machine's own `~/.claude` — doing so silently yields a different, smaller corpus.

```sh
python3 utils/corpus/build_oracle_jsonl.py --pairs data/corpus-v1/pairs.jsonl \
        --out-dir data/corpus --check-max-len
```

⚠️ **`--pairs` must be passed explicitly on this laptop.** It defaults to
`data/corpus/pairs.jsonl`, which here is the **stale pre-v1 corpus** (`label_raw` /
`label_merged`, no `label`) that `serialize.to_finetune_row` cannot consume. Local staleness,
not a defect in `main`.

Result: 61,629 train / 13,280 holdout, longest rendered row **1,950 tokens** against the 2,048
cap (nothing truncates), 43 labels present. Fixed P0/P3 subset = first 2,000 rows,
`sha256[:16] = 522283369fd4005e` — **pin this hash before comparing any P3 loss curve to
JAX's**, or the curves are not measuring the same data.

---

### D4 — On the real checkpoint the parity gate is RELATIVE, not absolute

Recorded because it changes a stated gate, and because "the number moved so I changed the
threshold" is exactly the move that should never pass unchallenged.

**Why absolute cannot work here.** The tiny fixture's logits are ~0.89, so 1e-4 absolute is a
sane 1.1e-4 relative. The real checkpoint's logits are **2,322-9,643**, where the same 1e-4
absolute means **1.1e-8 to 4.3e-8 relative** — below fp32 machine epsilon (1.19e-7). It is not a
strict gate, it is an impossible one, and no correct port could ever pass it.

**The threshold, justified rather than picked.** `rtol = 1e-4`, i.e. the port must agree to
within one ten-thousandth of the logit scale. The weights themselves are fp16, whose epsilon is
9.77e-04, so this demands agreement ~10x tighter than the precision of the weights being
compared. Observed: **2.67e-05**, another ~4x inside that.

**What makes it honest rather than a fudge:** the same gate, at real scale, still catches injected
faults by 3 orders of magnitude (RoPE 6.1e+01, Engram 6.1e+01, Sinkhorn 3.4e+02 against a clean
6.6e-02), and the port is machine-exact (4.1e-08) once the fp16 confound is removed. The
criterion was loosened; the *evidence* was not.

**Both numbers are always reported.** `parity_check.py` prints absolute, relative, argmax and
top-3 on every run, and `--gate abs|rel` names which one decided. Absolute stays the gate on the
tiny fixture.

*Also codified in:* `spike/mlx/parity_check.py --rtol/--gate` help, the P2 section of
`TESTS-RESULTS/2026-09-07-mlx-spike/SUMMARY.md`.

### D5 — Two fp16-only port bugs, and why the fp32 fixture could not see them

JAX evaluates some expressions in the **param's** dtype, not the module's. With fp32 params the
two are the same and the bug is invisible; with the real fp16 params they diverge:

1. `ZCRMSNorm` — JAX computes `1 + scale` in fp16. Upcasting `scale` first (the obvious thing to
   write) makes the norm *more accurate than the reference*. Near zero, fp16 resolves `1 + scale`
   to ~1e-3. This was the dominant error term.
2. `Block.attn_gate` — JAX applies `sigmoid` in the param dtype, then casts.

**Rule for the rest of the port:** match the reference's dtype flow exactly, including where it is
*less* precise. A port that is more accurate than its reference is still wrong.

## Findings

### F5 — 🚨 The tuned model does not beat the static top-3 baseline (a finding for #1 §5)

**Measured 2026-09-07**, 200 holdout rows, all three columns the same rows, static baseline built
from **train-split** frequencies so it never sees holdout answers:

| | top-1 | top-3 |
|---|---|---|
| static majority class | 12.50% | 44.00% |
| base checkpoint, untuned | 3.50% | 17.00% |
| **tuned (MLX LoRA)** | **22.00%** | **46.00%** |

**top-1 is a real win** — 44 hits vs 25, z ≈ 2.51, p ≈ 0.012. **top-3 is not**: +2.00pp is *four
rows*, against a ±6.91pp CI (z ≈ 0.40, p ≈ 0.69).

**The 45.99% bar is not cleared.** 46.00% must not be read as clearing it — that figure is from a
different sample, and on *these* rows the static baseline is 44.00%. The bar moves ~±2pp with the
sample, which is the size of the whole measured effect.

The untuned control matters here: it scores **below** static (17.00% vs 44.00%), which is the
right shape and proves the scorer has dynamic range rather than flattering everything. So
fine-tuning unambiguously worked; the open question is only whether it beats a trivial guess.

**Two readings, not yet separated** — a 1,000-row run was launched to decide:

1. **n=200 is too small.** ±6.91pp swamps a 2pp effect; 1,000 rows gives ~±3pp.
2. **top-3 may be the wrong gate.** Three labels dominate the corpus, so static top-3 starts at
   44%. A model can rank much better — as top-1 shows — while barely moving top-3. If this holds
   at n=1000 the metric is the problem, and #1 §5's surface gate needs rethinking, not the model.

Caveats bounding the claim: the adapter is **one epoch on the 2k fixture** (a floor, not a
ceiling), scoring uses an **empty reasoning block** so it measures `P(label|prompt)` rather than
the deployed generate-then-call path, and it is full precision (D6).

### F1 — 🚨 The corpus has **zero** abstain rows (a finding for #1, not fixable here)

`build_oracle_jsonl.py` emitted **0 rows with `"answers": []`** in *both* splits (0.00% of
61,629 train / 13,280 holdout), and `no_action` has no support.

This contradicts what #1 §3 requires and what `doc/finetuning.md:22` warns about:

> *"Include off topic examples with `"answers": []`. The built in generator produces about 1 in 8.
> **Without them the tuned model calls a tool on everything.**"*

It is structural, not a bug in the converter: every pair in `pairs.jsonl` is a real tool call, so
the converter has nothing to turn into an abstention. The off-topic slice has simply not been
built yet by anyone.

**Why this is urgent for the other machine:** a full Phase 2 training run on this corpus
produces a model that can never abstain; #1 §5's abstention precision/recall is **vacuous**
(no positives exist in the holdout); and #1 §6's every-turn hook would fire a recommendation on
every single turn — the exact failure §6 names, *"an Oracle that emits noise every turn trains
the operator to ignore it, which is worse than silence."* That is hours of GPU/CPU time spent
before the gap surfaces at eval.

**Reported to #1.** Not fixed here — out of bounds, and it is a main-lane data decision.

### F2 — The parity harness is insensitive to Sinkhorn iteration count

`spike/mlx/falsify_parity.py`, fp32 @ atol 1e-4, faults injected into the MLX side only:

| injected fault | max \|Δ\| | |
|---|---|---|
| *control:* perturb a weight **both** sides read | 4.172e-07, unchanged | confirms both read the same weights |
| RoPE sin sign flipped | 5.498e-01 | caught |
| Engram indices shifted +1 | 6.360e-02 | caught |
| `_rms_unit` epsilon 1e-6 → 1e-2 | 3.524e-03 | caught |
| **Sinkhorn 20 → 3 iterations** | **1.174e-05** | **NOT caught** |

On a 2-layer / 2-lane fixture, 3 Sinkhorn iterations already converge under the tolerance.
**P1 passing therefore does not prove the Sinkhorn loop count matches.**

**RESOLVED at P2, exactly as predicted.** On the real 27-layer / 4-lane checkpoint the same
injected fault moves max \|Δ\| to **3.365e+02** against a clean 6.567e-02 — ~5,000x, caught
decisively. The Sinkhorn iteration count is now verified.

### F4 — The two fixtures catch *different* faults; run falsification on both

P2's falsification surfaced the mirror image of F2: `_rms_unit` epsilon 1e-6 -> 1e-2 is **caught
on the tiny fixture (3.524e-03) and NOT caught on the real checkpoint (6.470e-02 vs a clean
6.567e-02)**. Real activations are large enough that the epsilon is negligible.

So neither fixture alone is a sufficient falsification target, and the later receipt does **not**
supersede the earlier one — the P1 and P2 falsification tables must be read together. Any future
change to `san_mlx.py` should re-run `falsify_parity.py` against both.

### F3 — Two port limits that P2 must resolve

1. **Non-flash attention only.** The tiny fixture sets `flash=False`, so the port implements the
   manual softmax path. If `needle2.pkl` sets `flash=True`, JAX takes
   `jax.nn.dot_product_attention` and any difference surfaces at P2 — attributable to the path,
   not the weights.
2. **Quant path unported.** Under `quant=False` both `_aq` and `maybe_quant_kv` are the identity
   in JAX, so P1 never exercised them. `--qat-bits auto` is P2/P3 scope, and P0's baseline is
   already training under `CQ mixed[embedding=4,mhc=4,default=2] STE + A8`.

   **Still open after P3, and re-sized (D6).** P3 trains full precision, so its curve is not
   comparable to the QAT baseline's and its adapter is not deployable without
   `--allow-numerics-mismatch` (PR #8). The port itself is **~25 lines**, not the multi-day job
   this document previously implied — the codebook and Hadamard matrix are cached numpy
   constants that are imported rather than ported. It is deferred behind the eval harness on
   purpose: the harness is what decides whether the port is needed at all.

---

## Cross-machine contract

Two machines, one plan. What each must not assume about the other:

| | |
|---|---|
| **This laptop (MBP 14" M4 Pro)** owns | GH-5 only: `spike/mlx/`, this doc, `TESTS-RESULTS/*-mlx-spike/`, branch `spike/mlx-finetune`. |
| **The Studio** owns | Phase 2 (#1) and the canonical corpus extraction. |
| Shared, must not diverge | `oracle/labels-v1.json`, `utils/corpus/serialize.py`, `needle/model/finetune.render_example`. The spike **imports** these; it never re-implements them. |
| Not shared | `data/**` (gitignored, per-machine), `.venv-mlx-spike/`, `.git/info/exclude`, `checkpoints/`. |

**Before acting on this doc from another machine, check:** the `updated:` date in the
frontmatter, the Status table, and issue #5's comment thread — the issue carries each gate as
it lands and is the faster read.

**A change needed in `utils/corpus/`, `oracle/`, `needle/`, `tests/` or the #1 plan is a
finding to post on #1** (see F1), never a commit on this branch. That bound is what keeps the
two machines from fighting over the same files.
