# Standard Operating Procedure (SOP): Finetune, Quantization, and Eval Campaigns

> **Scope & relationship to the other docs:**
> - **`GUIDING-PRINCIPLES.md`** is the canonical source for the durable/reversible/DRY bar and fork
>   discipline. Nothing here restates it.
> - **`AGENTS.md`** owns repo-wide behavioral governance: danger commands, the reversibility scale,
>   blast-radius sizing, and "verified beats plausible."
> - **`SOP.md` (this file)** is a tactical, step-by-step procedure specifically for **running and
>   recording a finetune, quantization, or evaluation campaign** against this model — the closest
>   thing this repo has to a heavy, repeatable, artifact-producing process.

This covers designing, executing, verifying, and recording evidence from a LoRA finetune run, a
quantization sweep (`quantize.py`'s fake-quant or CQ codebooks), or an accuracy/eval benchmark
against a checkpoint.

---

## 1. Governance

- **Verified beats plausible (`AGENTS.md` §6):** any accuracy, latency, or "the finetune worked"
  claim must be backed by a retained log or output you can point to — not a remembered impression of
  a terminal that already scrolled away.
- **Isolate anything that downloads or trains at scale.** A finetune or quantization sweep can pull
  large checkpoints via `huggingface_hub` and write to `~/.cache/cactus-needle/`. Run it from a
  disposable clone or a scratch working directory when you're iterating on the pipeline itself, so a
  bad run doesn't leave the main checkout in a confusing state.
- **File the issue before the campaign, not after.** A finetune/eval campaign is exactly the kind of
  non-trivial work `AGENTS.md`'s issue-first rail is for — open the tracking issue first so the
  motivation and success criteria are on record before you spend GPU/API time.
- **A confirmed defect gets filed immediately.** If a campaign surfaces a real, reproducible bug
  (a quantization scheme that diverges, an export that doesn't round-trip, a checkpoint format
  mismatch), file the GitHub issue as soon as the repro is confirmed — don't hold it for a later
  summary. Only genuinely ambiguous findings get *offered* rather than filed outright.

## 2. Standard workflow

```
[1. Intake]              -> open the tracking GitHub issue, state success criteria
        |
        v
[2. Preflight]            -> pytest -q -m "not slow" (and -m slow if the change touches
        |                     build/finetune) all green before spending real time/tokens
        v
[3. Baseline]             -> run the unmodified path once, capture its output as the
        |                     comparison point
        v
[4. Campaign execution]   -> the finetune / quantize / eval run itself
        |
        v
[5. Verification]         -> load the resulting checkpoint/.cact and confirm it actually
        |                     runs and produces sane output — not just that the job exited 0
        v
[6. Record evidence]      -> commit logs/metrics/config alongside the change, or attach
        |                     them to the tracking issue
        v
[7. Report & close]       -> summarize result on the issue; open follow-up issues for
                              anything the campaign surfaced but didn't fix
```

## 3. Step-by-step

### Step 1: Intake

1. Open the tracking GitHub issue: what checkpoint/config, what's being changed, what "success"
   means (a target metric, a qualitative behavior, a bug repro).
2. Note which entry points are in scope: `needle finetune`, `needle generate-data`, `needle build`,
   or a direct call into `needle/model/decode.py`/`quantize.py`.

### Step 2: Preflight

```bash
pytest -q -m "not slow"
```

Run the `slow` end-to-end build/finetune tests too if the change touches `finetune.py`,
`export.py`, or `architecture.py`:

```bash
pytest -q -m slow
```

Both green before proceeding. This is a self-check, not the campaign's evidence — it just confirms
you're not about to spend real time on a broken base.

### Step 3: Baseline

Before changing anything, run the existing path once and keep its output:

```bash
needle run --checkpoint <base.pkl> --query "<representative query>" --tools <tools.json> > baseline.out
```

`needle run` takes a **`.pkl` checkpoint**, not a `.cact` — `run.py:load_checkpoint` unpickles the
v2 checkpoint dict. `--temperature 0` (the default) is greedy, which is what you want for a
comparable baseline. This is what step 5 compares against.

### Step 4: Campaign execution

Run the actual finetune, quantization sweep, or eval. Examples:

```bash
# Finetune — JSONL path is POSITIONAL; --checkpoint auto-downloads from HF if omitted
needle finetune <data.jsonl> --checkpoint <base.pkl> --out <adapter.pkl> \
  --epochs 3 --lora-rank 16 --qat-bits auto

# Build / export — checkpoint is POSITIONAL; --bits accepts only "2" or "4"
needle build <base.pkl> --lora <adapter.pkl> --bits 4 --out <model.cact>
```

`--qat-bits auto` (the default) matches the checkpoint's own export scheme — override it only when
you are deliberately testing a mismatch between training and export numerics.

Capture stdout/stderr to a log file rather than letting it scroll away — you need it for step 6
regardless of outcome.

### Step 5: Verification

**Load the actual artifact and run it — don't trust a clean exit code as the verdict.**

A `.cact` is not loadable by `needle run` (that path takes a `.pkl`). Exercise the exported artifact
through the runtime SDK or the playground instead:

```bash
# Structural round-trip: does the .cact parse back with the geometry you expect?
python3 -c "from needle.model.export import read_export; print(read_export('<out.cact>'))"

# Behavioral: run the tuned weights through the native engine
python3 -c "
import needle
a = needle.Needle(tools=open('<tools.json>').read(), weights='<out.cact>')
print(a.complete('<same query as baseline>'))"

# Or interactively
needle playground --weights <out.cact>
```

Compare against the Step 3 baseline. For a quantization change, confirm the exported `.cact`
round-trips: the bit-packing in `export.py` and the codebooks in `quantize.py` must agree, or the
loaded model silently produces garbage rather than erroring. For a finetune, confirm the adapter
actually changes behavior in the direction intended — a LoRA run that trains cleanly but has no
measurable effect is a finding, not a pass.

### Step 6: Record evidence

Keep the artifacts that make the result checkable later:

- The run log (command + output), not just a paraphrase of it.
- The config/checkpoint identifiers used (base checkpoint path or HF revision, LoRA rank, bit
  width, dataset).
- Anything quantitative (loss curve, eval score, before/after comparison).

Attach these to the tracking issue, or commit them under a dated path if the repo has a place for
retained run artifacts. Do not let evidence live only in a terminal that's about to be closed.

### Step 7: Report and close

1. Summarize the result on the tracking issue: what was tried, what happened, whether it met the
   success criteria from Step 1.
2. If the campaign surfaced a separate defect, file it now (see Governance) rather than folding it
   into this issue's closeout.
3. Close the issue, or hand it off with a clear next step if the result was inconclusive.

## 4. Anti-patterns (apply `AGENTS.md` §6 here specifically)

- **Trusting exit code 0 as the verdict.** A training loop or export that exits cleanly can still
  have produced a checkpoint nobody can load, or a quantized model that silently diverges. Step 5
  exists because of this.
- **An empty dataset or empty eval set passes every check.** Before trusting an eval score or a
  finetune's "it converged," confirm the input actually had rows — a bad path or a filter that
  matched nothing yields a technically-successful run over zero data.
- **Iterating against a checkout you also rely on for other work.** A campaign that downloads large
  artifacts or writes to shared caches is easiest to reason about from a clone or scratch directory
  you're willing to throw away.
