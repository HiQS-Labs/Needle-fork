# Lessons Learned

Durable lessons from work on this repo, written to be read *before* the next similar effort —
not a log of what happened. `FINDINGS.md` is the timestamped investigation log; this file is what
we would tell ourselves at the start.

**Admission rule:** an entry only goes here if it is **grounded** — traceable to a receipt, a
GitHub issue, a commit, or a file in this repo, and cited inline. A lesson we merely believe is
not a lesson; it is a habit looking for evidence. Entries without a citation should be deleted.

---

## 1. Spike the training data before you spike the training

**Do a technical spike that validates the corpus contains the bulk of what the model must learn,
*before* building the trainer.** Prove distribution and coverage, not just row count and schema
validity.

We built a taxonomy, an extractor, a corpus, a JAX baseline and a whole MLX training port before
anything measured whether the data could teach what we needed. Three defects were all latent from
the first build and all found late:

- **Zero abstention examples.** `abstain_rows: 0` in *both* corpora
  (`data/corpus/oracle-stats.json`, `data/corpus-studio/oracle-stats.json`), against
  `doc/finetuning.md:22`: *"Include off topic examples with `"answers": []`. The built in generator
  produces about 1 in 8. **Without them the tuned model calls a tool on everything.**"* Structural,
  not a converter bug — every pair in `pairs.jsonl` is a real tool call, so there was nothing to
  turn into an abstention. Recorded as F1 in `PROJECT/1-INBOX/GH-5-MLX-FINETUNE-SPIKE.md`.
- **Governance is 6.8% of the holdout** — 68 of 1,000 rows — while governance is the entire
  justification for the Oracle (#1: *"an Oracle that only knows `run_tests` does not know our
  SDLC"*). Measured: the tuned model scores **19.1% top-3 on governance vs 49.0% on coding**
  (`TESTS-RESULTS/2026-09-07-oracle-eval/`). It is worst at the thing it exists for. Five of the
  13 governance labels have **zero** holdout rows, and it earns a top-1 on only three. Tracked as
  [#9](https://github.com/HiQS-Labs/Needle-fork/issues/9).
- **The prompt is ~80% boilerplate.** All 44 tool schemas are embedded in every row — 1,383 tokens
  of schema against rows rendering at 1,524–1,950 tokens. This is also why `--max-len` could not
  rescue CPU training: coverage at both 512 and 1024 is **0.0%**, so no short-row bucket exists
  (#1 §4).

**What the spike should have asserted**, in a form that can fail:

- every label's share of rows, against the support floor, split governance vs coding
- the abstention slice actually exists at the documented rate
- token-length distribution vs `--max-len`, and what fraction of each row is constant boilerplate
- what a trivial baseline scores — because if a frequency table is already strong, the metric may
  not be able to see your model (lesson 2)

**Cost of skipping it:** roughly a full day of training and porting work whose headline result is
now known to be unable to distinguish itself from a three-label frequency table.

---

## 2. A single aggregate number hides the subgroup you actually care about

At n=1,000 on the Studio holdout (`TESTS-RESULTS/2026-09-07-oracle-eval/`):

| | top-1 | top-3 |
|---|---|---|
| static majority class | 16.30% | 46.70% |
| base checkpoint, untuned | 2.80% | 12.70% |
| **tuned** | **24.10%** | **47.00%** |

top-1 is a real win (+7.80pp, z ≈ 4.34). **top-3 is +0.30pp — three rows in a thousand**, z ≈ 0.13.
The aggregate cannot separate a trained model from guessing `read_file`, `run_script`,
`search_code`.

Two traps in one table:

- **The documented bar was a different sample.** Tuned top-3 47.00% against a quoted bar of 45.99%
  reads like a pass. The same-sample static baseline is **46.70%**. Comparing a measurement to a
  bar computed on other rows manufactures a result.
- **The aggregate buried the point.** Coding is 93.2% of rows, so the headline is a coding number.
  Governance — the reason the project exists — is 19.1% and invisible.

#1 §5 already required the governance-vs-coding split and said *"a single aggregate number hides
that."* **It was right, and it was written before the data existed to prove it.** Design the
subgroup report in with the metric, and report both from the first run.

**Related:** always run an untuned control. The base model scoring 12.70% — far *below* the static
baseline — is what proved the scorer had real dynamic range rather than flattering whatever it was
handed.

---

## 3. Two machines with two corpora is not parallelism

Phase 2 §4 ran on the Mac Studio while the MLX spike ran on the MBP. Each machine built its own
corpus from its own `~/.claude` transcripts, and they are **not the same data**:

| | train | holdout |
|---|---|---|
| MBP (`data/corpus/`) | 61,629 | 13,280 |
| Studio (`data/corpus-studio/`) | 48,744 | 25,684 |

Same extractor, same taxonomy version, same `labels_present: 43` — different rows, so different
baselines, different scores, and receipts that cannot be compared. From commit `0700238`:

> *"Running Phase 2 §4 on the Studio while GH-5 ran on the MBP produced two lanes with different
> corpora, different baselines and different receipts, and the reconciliation cost more than the
> parallelism bought."*

**Lessons:**

- Split work across machines only when the **inputs are identical and pinned** — checksum-verified,
  not "regenerated the same way". Regeneration from per-machine state is a different dataset
  wearing the same name.
- If two datasets must coexist, write down which is authoritative for what, and make every receipt
  name the corpus that produced each number. The rule adopted was: **one corpus for anything
  scored** (`data/corpus-studio/`), either for anything timed.
- Prefer one machine executing and the other planning, over two machines executing.

---

## 4. Codify a changed decision before you build on it

A superseded decision left in a doc is not neutral history — it is an **active instruction**
pointing the next reader, the other machine, or your own post-compact session at abandoned work.

Both instances are real:

- **XYZ-forge #467** carried *"Framework: JAX/Flax, not MLX … deferred to Phase 3/4"* in its
  checklist while a later comment **on the same issue** said CPU training does not finish and §4
  now runs on MLX.
- **Needle-fork #1 §4** kept *"Framework decision: JAX"* long after the consolidation — on the
  issue that is SSOT for that phase.

Codified as **`SOP.md` §5.7**. The clause that does the most work: **sweep for the same claim
restated elsewhere.** One corrected estimate had already propagated into three documents before it
was caught (lesson 5); a correction that does not chase every copy is cosmetic.

---

## 5. Size the work by reading the code, not by recalling its shape

The MLX quantisation-aware port was described — by me, in three places — as requiring the
Lloyd-Max codebook, the Hadamard rotation and the nearest-codeword search to be reimplemented.
Measured:

- `cq_ste` (`needle/model/quantize.py:354`) is **one line**
- `_cq_codebook_np` / `_cq_hadamard_np` are `@lru_cache` **numpy constants** keyed only on
  `(bits, group_size)` — weight-independent, so **imported, not ported**
- `cq_quantize` is ~12 lines, and MLX has every op it uses

**~25 lines, not multi-day — off by an order of magnitude, and it was about to drive a scheduling
decision.** Recorded as D6 in the GH-5 doc and corrected in #7.

The check is cheap: before a size-based decision, open the function. Estimates deserve the same
"verified beats plausible" standard as results (`AGENTS.md` §6).

---

## 6. Compute the resource requirement before you allocate it

A batch-16 / seq-2048 training run **took the machine down** — a reboot, not an OOM.

The arithmetic takes ten seconds: one `[B, H, S, S]` float32 attention score matrix per layer,
retained for backward, on 27 layers, is **~54 GB**. The host has 24 GB, with ~8.7 GB already held
by another job. It was never "tight"; it was 2.5× total RAM. I named the risk out loud and
proceeded anyway — **naming a risk is not mitigating it.**

Three things this taught, all now in `spike/mlx/train_lora.py` (`813f5a7`):

- **A pre-flight refusal computed from config is the only guard that works.**
  `mx.set_memory_limit` is **advisory** — measured, a step peaked at 13.4 GB against a 12 GB cap
  and allocated straight through without raising.
- **Unified-memory GPU frameworks fail differently.** They starve the kernel instead of getting
  OOM-killed, so the blast radius is the host, not the process.
- **The gap was a missing feature, not a law of nature.** `TransformerConfig.flash` defaults `True`
  and the JAX path is memory-bounded; the port materialised full scores (`san_mlx.py:214`).
  Corrected in #7 §2 — reporting the 54 GB as intrinsic to Needle would have been wrong.

---

## 7. A check that passes on empty input is not a check

Two instances, one day:

- **Training on nothing, reporting success.** At `--max-len 512` every corpus row truncates inside
  the prompt, so the loss mask is all zeros and the run printed a clean `loss 0.0000` while
  optimising nothing. Now refused outright (`b60b074`).
- **A holdout split that was never scored.** The port carved out `val_seqs`/`val_masks` exactly as
  `finetune.py:359-365` does, then never evaluated them — so the first "completed" P3 run reported
  train loss only, which cannot distinguish convergence from memorising a 33-token span. Re-ran
  rather than reporting it (`b4ebe56`).

Corollary, from PR #8: **make tests fail first.** The guard there was verified red before green,
and the failing output — the adapter building happily and writing `W4A8` — is the evidence the
defect was real, not merely plausible.

---

## 8. Silence is a defect, not a default

`needle build` deployed a full-precision-trained adapter into 2-bit quantised numerics and exited
0. Two causes, both about silence: `.get()` made a **missing** metadata key indistinguishable from
an explicit `None`, and the fallthrough branch resolved bits from `config.weight_bits` without
comment.

It was incoherent with the code around it, which *already raised* for the strictly milder case of a
QAT bit-width mismatch. Fixed in **PR #8**, with the escape hatch preserved
(`--allow-numerics-mismatch`) so deliberate post-training quantisation still works.

**When a guard exists for a mild failure, check the severe version of the same failure is not
falling through unguarded.**

---

## 9. Operational hygiene that cost us real time

Small, specific, each one grounded in a thing that actually went wrong:

- **`gh` with no default repo resolves to `upstream`.** In this fork, a bare `gh issue view 5`
  returned *cactus-compute/needle*'s issue #5, not ours. One `gh repo set-default` prevents
  posting work to the wrong project. Verify before assuming a comment landed where you meant.
- **`/private/tmp` is wiped on reboot.** The crash took ~1.5 h of JAX baseline logs with it. Long
  runs write to a path that survives a restart.
- **Commit before starting anything long or risky.** ~2 h of uncommitted port work was sitting in
  the tree when the machine went down. It survived; it did not have to.
- **Process watchers match the wrong process.** A `pgrep -f` watcher matched its own command line,
  and later reported `cpu=0.0%` for a job running at 341% because it read the `zsh` wrapper rather
  than the Python child. Watch a **PID**, and sanity-check that a "dead" job is not simply being
  measured wrong.
- **A GPU job looks idle.** MLX training ran at 30% CPU and 960 MB RSS — nothing like the JAX
  baseline's 600% CPU and 8.7 GB. "Nothing is spinning" is not evidence a GPU job has stopped.

---

## 10. Report the number that could embarrass you first

Recurring across this work: the honest framing was always cheaper than the flattering one, and
usually more useful.

- P2 passed only after **restating a tolerance** the checkpoint made unreachable (1e-4 absolute is
  below fp32 epsilon at logits of 2,322–9,643). Stating plainly that the criterion was loosened
  *and the evidence was not* is what kept the result meaningful.
- Reporting **sum and mean ranking** both, rather than picking one, is what exposed a severe length
  bias (tuned top-3 47.0% sum vs 37.3% mean).
- Reporting **top-3 as indistinguishable** rather than "47.00% clears 45.99%" is the difference
  between a finding and a fabrication.

If a number needs a specific framing to look good, that framing is the finding.
