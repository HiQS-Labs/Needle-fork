# Standard Operating Procedure (SOP): Finetune, Quantization, and Eval Campaigns

> **Scope & relationship to the other docs:**
> - **`GUIDING-PRINCIPLES.md`** is the canonical source for the durable/reversible/DRY bar and fork
>   discipline. Nothing here restates it.
> - **`AGENTS.md`** owns repo-wide behavioral governance: danger commands, the reversibility scale,
>   blast-radius sizing, and "verified beats plausible."
> - **`SOP.md` (this file)** is a tactical, step-by-step procedure for **running and recording a
>   finetune, quantization, or evaluation campaign** against this model — the closest thing this repo
>   has to a heavy, repeatable, artifact-producing process — plus, in §4, the procedure for
>   **adjudicating a contested decision** that such a campaign surfaces.

This covers designing, executing, verifying, and recording evidence from a LoRA finetune run, a
quantization sweep (`quantize.py`'s fake-quant or CQ codebooks), or an accuracy/eval benchmark
against a checkpoint — and, in §4, how to settle a judgment call the run surfaces so it stays
settled.

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

## 4. Adjudicating a contested decision

A campaign regularly surfaces a judgment call that the numbers alone do not settle —
keep a label or merge it, ship a threshold or move it, accept a regression or block on
it. This is the procedure for those. It is deliberately heavier than "decide and move
on", because these are the decisions that get silently re-litigated six weeks later by
someone who cannot find why it went the way it did.

Use it when a decision (a) changes a published contract or a shared surface, (b) would
be expensive to reverse, or (c) has already been argued once. Skip it for a reversible
local call — `AGENTS.md` §8 still applies.

1. **Fix the measurement before adjudicating anything the measurement drives.**
   -> expect the number you are about to decide on to have survived a deliberate attempt
   to break it. If the decision rides on a count, a score, or a coverage figure, audit how
   that figure is produced *first*. `AGENTS.md` §6 is the rail: *an empty input passes
   every check*, and a threshold applied to a buggy measurement is a check that reports
   confidence it never earned. In practice this step has dissolved the decision outright
   more than once — the Phase 2 `pkg_manage` question turned out to be two bugs in our own
   labeler, not a question (see `PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md`).

2. **Adjudicate against the governance docs explicitly, naming which rail bears.**
   -> expect a citation, not a vibe. `GUIDING-PRINCIPLES.md` for the durable/reversible/DRY
   trade, `AGENTS.md` §3 for the reversibility read, `SOP.md` for campaign procedure. Where
   two rails pull against each other, say so and pick — `GUIDING-PRINCIPLES.md` is explicit
   that the tension *is* the decision, not something to average away.

3. **Check the reversibility asymmetry before anything else decides it.**
   -> expect an `Easy / Costly / One-way door` read on *each* option, per `AGENTS.md` §3.
   Options are rarely symmetric, and when one is Easy to undo and the other is not, that
   usually settles it on its own. Prefer the option that keeps the expensive move available
   later; consolidation applied downstream (at a dataloader, a projection, a view) beats the
   same consolidation baked into a canonical source.

4. **Get independent feedback — `/consult` — and state the degrade if it fails.**
   -> expect a cross-model read, or an explicit note that there wasn't one. Advisors are
   advisory; the operator breaks ties. Two things must be recorded honestly: when advisors
   fail (auth, entitlement, an unreachable backend), say so rather than quietly proceeding;
   and when only one answered, label it a single-model read, not a consult — one model that
   agrees with the framing you handed it is corroboration, not verification.

5. **Codify the outcome in at least two places that are easy to find later.**
   -> expect one of them to be where the decision would actually bite. A decision recorded
   only in a doc gets re-litigated by whoever is reading the code. Land it in at least:
   - the **code or contract** the decision governs — at the constant, flag, or schema field
     itself, so it is read at the moment someone is tempted to change it; and
   - a **durable record** — the `PROJECT/**` doc that owns the work, plus `CHANGELOG.md` per
     `PROJECT/PDDA.md` if it is consequential (`AGENTS.md` §7).

   Include *why*, the rails it was decided against, and what would have to change for the
   answer to change. A decision without its reasoning is re-argued from zero.

6. **Guard it with a test that you have watched fail.**
   -> expect red, then green. Where the decision is expressible as an invariant, assert it,
   then mutate the thing it guards and confirm the test goes red — `AGENTS.md` §6: a check
   that cannot fail is decorative and worse than nothing. This is what stops a written-down
   decision from quietly reverting.

## 5. Anti-patterns (apply `AGENTS.md` §6 here specifically)

- **Trusting exit code 0 as the verdict.** A training loop or export that exits cleanly can still
  have produced a checkpoint nobody can load, or a quantized model that silently diverges. Step 5
  exists because of this.
- **An empty dataset or empty eval set passes every check.** Before trusting an eval score or a
  finetune's "it converged," confirm the input actually had rows — a bad path or a filter that
  matched nothing yields a technically-successful run over zero data.
- **Iterating against a checkout you also rely on for other work.** A campaign that downloads large
  artifacts or writes to shared caches is easiest to reason about from a clone or scratch directory
  you're willing to throw away.
- **Adjudicating a decision on a number you have not audited.** A threshold applied to a buggy
  measurement produces a confident, wrong answer that then gets written down as settled. §4 step 1
  exists because this has already happened here once.
- **Recording a decision in exactly one place.** A decision that lives only in a doc is invisible to
  whoever is editing the code, and a decision that lives only in a code comment is invisible to
  whoever is reading the plan. §4 step 5 requires both.

## 6. Repeatable evidence gates for each experimental round

Use the [round contract and commands](doc/experiment-rounds.md) for testing, analysis,
and next-step generation in every phase. Freeze the question, inputs, expected count,
comparisons, falsifier, thresholds, and resource cap before measurement. Retain complete
raw evidence and immutable run identities; derive published counts from the offline
`spike/mlx/audit_round.py` report rather than terminal excerpts or remembered summaries.

PASS, FAIL, and INCOMPLETE describe individual evidence checks, not whether a model is
useful. Both FAIL and INCOMPLETE block dependent claims, but a FAIL is a contradiction
and outranks an INCOMPLETE when choosing what to repair first. Gates a script can decide
are reported separately from gates only a person can close; the overall disposition
cannot read PASS while a review gate is open. A comparator must never be fitted on the
rows it is scored against, and the audit measures that disjointness rather than trusting
a file's name. Current offline checks establish
identity, available raw-output scoring, and paired arithmetic; served-token semantics,
sampling independence, causal interpretation, and product decisions still require an
explicit evidence-linked review. Do not turn those unknowns green by assertion.

**Accepting an implementation is not disposing of a round.** They are separate decisions
and both are required. *Implementation acceptance* asks whether the gates run, whether
their negative controls were witnessed failing, and whether limits are documented.
*Round disposition* asks what the evidence supports, and is written by a person. A review
can be complete while its evidentiary verdict is INCOMPLETE — that is a finished review,
not an unfinished one. Record the disposition in its own document pinned to the machine
report's hash; never edit the report to mark a human judgment PASS. An issue closes when
every requirement is either met or **explicitly deferred with an owner and a reopen
condition** — a deferred requirement is not an implemented one, and must not be quietly
checked off. [`GH-14-ROUND-DISPOSITION.md`](PROJECT/1-INBOX/GH-14-ROUND-DISPOSITION.md) is
the worked example.

Choose one bounded next action from the first unresolved prerequisite or the cheapest
experiment that can change the decision; record its falsifier and stop cap. Two review
revision rounds maximum, then a named blocker, explicit stop, or maintainer adjudication
under §4. Preserve dissent and superseded claims. Debugging follows reproduce → trace →
falsify → cross-reference; every implemented gate must have a witnessed negative control.
