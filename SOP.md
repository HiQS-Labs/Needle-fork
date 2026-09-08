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
settled, and in §5 how local docs stay synchronised to the GitHub issues that govern them.

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

**Then preflight the DATA, not only the environment.** A green test suite says the code runs; it
says nothing about whether the corpus can teach what you need. Before building on a dataset, assert
its shape in a form that **can fail**:

- **Per-label support**, against the support floor, **split governance vs coding**. An aggregate row
  count hides a subgroup at 6.8%.
- **Every required slice actually exists.** Not "the converter handles abstentions" — the measured
  count of them.
- **Token-length distribution against `--max-len`**, plus what fraction of each row is constant
  boilerplate.
- **What a trivial baseline scores.** If a frequency table is already strong, your metric may not be
  able to see your model at all (Step 5).

This is a rail because skipping it cost a full day here: a taxonomy, extractor, corpus, JAX
baseline and a complete MLX training port were built before anything measured whether the data
could teach the task. Three defects were latent from the first corpus build — zero abstention rows
in both corpora against `doc/finetuning.md:22`, governance at 6.8% of rows while being the entire
point of the model, and ~80% of every prompt being the same 44 embedded schemas. See
`LESSONS-LEARNED.md` lesson 1.

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

**Before launching anything long, unattended, or memory-hungry:**

- **Compute the resource requirement from the config and refuse your own run if it does not fit.**
  Do not launch on a feeling that it looks "tight". A batch-16 / seq-2048 run here needed **~54 GB**
  of retained attention activations — one `[B,H,S,S]` matrix per layer across 27 layers — on a 24 GB
  host with ~8.7 GB already in use. **It took the machine down: a reboot, not an OOM.** The
  arithmetic takes ten seconds; naming a risk out loud is not mitigating it.
- **Do not trust a framework's memory cap.** `mx.set_memory_limit` is advisory — measured, a step
  peaked at 13.4 GB against a 12 GB cap and allocated straight through without raising. A
  unified-memory GPU framework starves the kernel rather than getting OOM-killed, so the blast
  radius is the **host**, not the process.
- **Write logs somewhere that survives a restart.** `/private/tmp` is wiped on reboot; the crash
  above took ~1.5 h of baseline logs with it.
- **Commit before you launch.** ~2 h of uncommitted work was in the tree when that machine went
  down. It survived; it did not have to.
- **Watch a PID, not a pattern.** A `pgrep -f` watcher matched its own command line, and later
  reported `cpu=0.0%` for a job running at 341% because it read the `zsh` wrapper rather than the
  Python child. Also note a **GPU job looks idle** — MLX training ran at 30% CPU / 960 MB RSS
  against the JAX baseline's 600% / 8.7 GB. "Nothing is spinning" is not evidence it stopped.

See `LESSONS-LEARNED.md` lessons 6 and 9.

### Step 5: Verification

**Load the actual artifact and run it — don't trust a clean exit code as the verdict.**

Three rails on the numbers themselves, before the artifact checks below:

- **Report the subgroup alongside the aggregate, always.** An aggregate is a weighted average
  dominated by the majority class, and it will hide the minority you actually care about. Measured
  here: aggregate top-3 **47.00%** looked like a pass, while the governance split — the reason the
  model exists — sat at **19.1%** and was invisible at 6.8% of rows.
- **Compare against a trivial baseline computed on the SAME rows.** Aggregate top-3 47.00% against a
  quoted 45.99% bar reads like clearing it; the same-sample static baseline was **46.70%**, so the
  real margin was three rows in a thousand (z≈0.13). **Comparing a measurement to a bar computed on
  other rows manufactures a result.** Run an untuned control too — the base model scoring *below*
  the static baseline is what proved the scorer had dynamic range rather than flattering whatever it
  was handed.
- **Any correlation claim needs a null control.** Shuffle or randomise the thing you claim is
  predictive and re-measure; report the **lift**, not the raw rate. A prompt→commit correlation
  showed 68.8% of prompts followed by a commit within 15 minutes, which sounds decisive — but
  shuffled timestamps scored 30.3% purely from commit density. The finding is the **+38.5pp lift**,
  and without the control the headline would have been mostly artifact. This is `AGENTS.md` §6's
  "a check that cannot fail is not a check" applied to statistics.

See `LESSONS-LEARNED.md` lesson 2.

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

## 5. Source of truth: the GitHub issue wins

This repo is worked from **more than one machine at a time** — the Studio runs the Phase 2 lane,
the MBP runs side quests — and from more than one branch and session per machine. The GitHub
issue on the server is the only surface all of them can see. A `PROJECT/**` doc on an unmerged
branch is invisible to the other machine, and a decision recorded only there is a decision the
other machine will unknowingly contradict.

So:

> **The GitHub issue is the canonical, actionable source of truth. Local docs, ROADMAP rows and
> receipts are projections of it. Where they conflict, the issue wins — unless verified local
> evidence contradicts the issue's premise, in which case you neither obey nor override it
> silently: you post the finding, and if confidence is low you stop and ask.**

### 5.1 Read the issue first, and read it fresh

-> expect the issue, not your memory of it, and not the local doc. Before acting on a plan,
`gh issue view <n> --comments`. The body is often the *oldest* thing in the thread: a later
comment may supersede it, and a plan revised in comments while the body still shows the original
sketch is normal, not an anomaly. If the body and a comment disagree, the comment thread is the
later state — say which one you followed.

### 5.2 Sync local docs to the issue, and push findings back up

-> expect the two to agree after your change, in both directions:

- **Down:** when the issue moves, update the local `PROJECT/**` doc, its Status table and its
  ROADMAP row so a cold session on the other machine is not led by a stale plan.
- **Up:** when local work produces a result, a decision or a contradiction, **post it to the
  issue in the same iteration that produced it** — not in a later summary. Until it is on the
  issue it does not exist for anyone else. This is the same "file it immediately" rule as §1's
  confirmed-defect rail, applied to findings and decisions rather than bugs.

Comment on the issue; do **not** silently rewrite its body to match local reality. The thread is
the audit trail, and an edited body destroys the record of what was believed when.

### 5.3 On conflict, the issue wins — by default

-> expect the default to be "follow the issue," because it is the shared state. A local doc that
disagrees is usually the stale one.

### 5.4 The carve-out: the issue does not win against verified evidence

An issue is a plan written at a moment in time. It can be **wrong about the world**, and this has
already happened repeatedly here:

- #1 named `rebalance.db`'s `clio_prompts` as the corpus source. It has no tool-call column, so
  it cannot supply a supervision target at all.
- #1 §5/§6 build the hook on a `min_confidence` floor. Fine-tuning does not update the confidence
  head, so a tuned model reports `confidence` as `None` and the mechanism does not exist.
- #1 §3 requires an `"answers": []` abstain slice at roughly 1 in 8. The built corpus has 0.00%.

In each case, obeying the issue literally would have burned hours. **Verified local evidence — a
measurement you can point at, with a receipt — outranks a plan's assumption about reality.** But
it does not license you to quietly do something else:

1. Post the contradiction to the issue, with the measurement and how to reproduce it.
2. Propose the specific edit the issue needs.
3. Then proceed on the evidence, saying plainly in the commit and the comment that you did.

### 5.5 When confidence is low, stop and raise it with the operator

-> expect a question, not a guess. Do not resolve the conflict yourself when **any** of these
holds:

- the issue is **newer** than your evidence, or you cannot tell which came first;
- following the issue would **discard verified work**, or spend more than ~an hour before the
  conflict would surface on its own;
- the conflict touches a decision already adjudicated under **§4** — reopening one unilaterally
  is how a settled call gets silently reversed;
- the action is **Costly or a one-way door** on `AGENTS.md` §3's scale;
- **two issues disagree with each other**, or an issue disagrees with its own umbrella;
- the fix would cross a stated **bound** (another lane's files, another machine's data).

When you raise it, give the operator a decision, not a puzzle: both readings, the evidence
behind each, your recommendation, and what you will do if they do not answer. Then wait.

### 5.6 Which artifact carries what

| artifact | role | authority |
|---|---|---|
| **GitHub issue + comments** | decisions, plan, current state | **canonical, actionable** |
| `PROJECT/**` doc | execution detail for one effort | projection of the issue; must name its issue |
| `ROADMAP.md` row | pointer/ledger | projection; per `PROJECT/PDDA.md` |
| `TESTS-RESULTS/**` receipt | measured evidence | **authoritative for what was measured** — this is what can outrank a plan |
| `CHANGELOG.md` | end-of-iteration record | historical; never the current plan |

A receipt beats a doc on *what happened*. An issue beats a doc on *what to do*. A doc that
contradicts both is stale — fix it in the same commit that discovers it.

### 5.7 When a decision changes, codify it *before* you build on it

§5.2 says push findings up in the same iteration. This is the stricter case that governs a
**reversal**: a pivot, a rescope, an abandoned approach, or a corrected estimate that drove a
choice.

> **Update every doc and issue carrying the old decision BEFORE starting the new work — not after
> it lands, and not "once it settles".**

-> expect a stale decision to behave as an *active instruction*, not as neutral history. It points
the next reader — or the next machine, or your own next session after a compact — at abandoned
work. The window between "we changed our mind" and "the docs say so" is precisely the window
someone else reads them in, and starting the new work first is what widens it.

This is not hypothetical. Both have already happened here:

- **XYZ-forge #467** carried *"Framework: JAX/Flax, not MLX … MLX is deferred to Phase 3/4"* in its
  checklist while a later comment on the **same issue** said CPU training does not finish and §4
  now runs on MLX. A reader who stopped at the checklist got the opposite instruction from one who
  scrolled to the bottom.
- **Needle-fork #1 §4** kept *"Framework decision: JAX"* long after the consolidation — on the
  issue that is SSOT for that phase, so the most authoritative artifact was the wrong one.

How to apply:

1. **Codify in at least two easily-found places**, always including the issue that is SSOT for the
   workstream (§4's rule, applied to reversals as well as adjudications).
2. **Sweep for the same claim restated elsewhere.** A reversal usually invalidates a sentence in
   more than one artifact — including ones *you wrote earlier in the same session*. A corrected
   estimate must be chased into every doc that quoted it, or the correction is cosmetic. One
   re-sizing on 2026-09-07 had already propagated into three documents before it was caught.
3. **Mark the supersession; do not delete the old text.** The reasoning for the reversal is the
   useful record — "this previously said X, and here is what measurement changed" is worth more
   than a clean page.
4. **Then** start the new work.

**Carve-out to §5.2's "do not rewrite the body".** §5.2's rule protects the audit trail, and it
holds for *decisions and findings*: comment, never quietly restate. It does **not** license leaving
a body-level **checklist or status table** that now contradicts a later comment on the same issue,
because that artifact is read as current instruction rather than as history. Edit it — and make the
edit non-silent:

- mark the supersession **in place** ("revised YYYY-MM-DD; this supersedes …"), and
- post a comment recording what changed and why, and
- never delete the superseded reasoning — GitHub keeps edit history, but the next reader does not
  read edit history.

Silent is the thing §5.2 forbids. An announced, marked, comment-backed correction of a live
checklist is the fix, not the violation.

## 6. Anti-patterns (apply `AGENTS.md` §6 here specifically)

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
- **Leaving a finding in a local doc or a commit message only.** The other machine reads the
  issue, not your branch. A result that never reaches the issue does not exist for anyone else,
  and the usual cost is the other lane spending hours on a premise you already disproved (§5.2).
- **Acting on the issue body without reading its comments.** The body is frequently the oldest
  text in the thread; a plan revised in comments while the body still shows the original sketch
  is the normal case here, not an anomaly (§5.1).
- **Silently resolving a doc-vs-issue conflict either way.** Obeying a plan you have evidence
  against, and overriding a plan without saying so, are the same failure with opposite signs.
  Post the contradiction, then proceed on the evidence and say that you did (§5.4-§5.5).
