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
  measured wrong. **Addendum, same day, same author:** `pkill -f <pattern>` also matches the
  *shell running the chain that launched the pattern* — it killed a smoke → commit → launch
  chain mid-way, and the commit never landed. Launch long jobs from a **script file** so no
  shell's argv contains the pattern, write the PID to a file, and kill by that PID. Writing a
  lesson down is not the same as having learned it; the test is whether the next run is
  structured so the mistake cannot recur.
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

---

## 11. The eval number is not the deployed number — score the artifact you ship

> **CORRECTED 2026-09-09 (D10, [#12](https://github.com/HiQS-Labs/Needle-fork/issues/12)).** The
> headline of this lesson survives — it is *more* true than when written — but **the evidence below
> is wrong and the causal claim is withdrawn.** The 8–10% was precision-when-answering from a
> harness that discarded every second row, scored on a sample with zero abstention rows. Post-training
> quantisation does **not** destroy the fine-tune: measured properly, the 2k PTQ artifact works
> (8.00% top-1 at 44 declared, 8.50% at 5). The deployed collapse was the engine's ≥6-tool
> declaration contract, which degrades the *base* model too.
>
> The bullet below asserting "QAT is not an optimisation; it is the deployment contract" is
> withdrawn as stated: QAT training turned out to be neither the problem nor the fix. It is the best
> artifact once the contract is sound, and the worst when measured under the broken one.
>
> The one claim here still standing: tuned + PTQ generating `<think> } } } }` **on MLX with no
> engine** remains unexplained and unreproduced. See D7's annotation in the spike doc.
>
> The durable version of this lesson is **#13**, which is what the evidence actually supports.

The 2k adapter scored **24.1%** top-1 when ranked at fp32 on MLX and **8–10%** through
`needle build` → `.cact` → native engine, with degenerate reasoning (`LAST: read_file -> }] }] }]`).
Four isolating experiments falsified the plausible suspects one by one — byte-identical tools
serialisation changed nothing (to the decimal); W4 vs mixed-2-bit changed nothing; the *base*
model through the engine was sane; the fp32 tuned model generated cleanly. Then the decisive one:
**tuned weights + PTQ generated on MLX with no engine at all → `<think> } } } }`**, while base + PTQ
stayed sane. Post-training quantisation of the LoRA-merged weights destroys the fine-tune. D7 on
[#5](https://github.com/HiQS-Labs/Needle-fork/issues/5); `TESTS-RESULTS/2026-09-07-mlx-spike/`.

**Lessons:**

- **#1 §5 said "evaluate the exported `.cact`, not just the checkpoint" — and it was right before
  the data existed to prove it.** A fine-tune whose quality is only ever measured in the training
  numerics has not been measured. `utils/hooks/eval_cact.py` now scores the deployed path.
- **QAT is not an optimisation; it is the deployment contract.** `needle finetune` defaults to
  `--qat-bits auto` for a reason, and PR #8's guard exists because silence here is catastrophic.
  The MLX port deferred QAT as "later" (D6) on the assumption an fp32 adapter would survive PTQ.
  It did not survive at all.
- **Isolate by falsification, one variable at a time, and keep a control.** Each of the four
  negative results was cheap, and the base-model control is what let "the engine is fine" be a
  conclusion rather than a hope.

---

## 12. A smell is not a verdict — test the primitive before restating a gate

QAT parity landed at 4.9e-04 (tiny) / 1.1e-03 (real) relative against a 1e-4 fp32 gate, with
argmax 100% / 99.2%. The pattern *smelled* like codebook-boundary flips from backend fp noise —
inherent, not a bug. It would have been easy to loosen the gate on that smell. Instead the
quantisers were compared directly on real leaves, and the mechanism was **proved**: differing
elements came in **exact multiples of 128** (384, 384, 512 — whole groups), because one codeword
flip is spread across its group by the Hadamard un-rotation; MLX's *CPU* device disagreed with JAX
identically, ruling out a GPU artifact; A8 differed by one ulp; and the residual was flat across
sequence length, ruling out an accumulating activation-path defect. D8 restated the gate on that
evidence. `TESTS-RESULTS/2026-09-07-mlx-spike/p3-qat-parity.json`.

**Lesson:** when a parity gate fails by a little, the two honest moves are "find the bug" or "prove
the residual is inherent, with a mechanism and a number". "It's probably fine" is neither. D4 and D8
both restated a criterion; both did it with the evidence unchanged and the mechanism named.

---

## 13. Validate the measurement before you optimise against it — and make the control fail on purpose

Added 2026-09-09. This is the durable replacement for the withdrawn causal claim in **#11**; the
full trail is D10 in the spike doc and [#12](https://github.com/HiQS-Labs/Needle-fork/issues/12).

An entire chain of work — D7's diagnosis, D8's parity gate, the MLX QAT port, a 4-hour 10k retrain,
and two GitHub issues — was built on a deployed number produced by a harness with **three** defects,
none in the model:

1. **A reused engine handle.** The engine is conversational; `complete()` continues the prior turn
   and never calls the `needle_reset()` that exists in the library. A reused instance answered every
   *other* row — a perfect `Y n Y n` alternation.
2. **Unpaired samples.** `load_rows(n=60)` and `load_rows(n=200)` share a seed but reservoir-sample
   *different sets*. The headline "21.67% MLX vs 3.00% engine" compared **zero overlapping rows**.
3. **A scorer that credited failure.** A regex searching output for `"name"` accepted truncated JSON
   (`<tool_call>[{"name":"run_script"` scored as a correct answer), and "precision when answering"
   was reported on a sample containing **zero abstention rows**, so it conditioned away half the
   failures by construction.

The control that would have caught all of it — score the **base, un-fine-tuned** model through the
same path — is a two-minute run. It was not done until after the retrain. It immediately showed the
untuned base *outscoring* the tuned artifact, which is impossible if the fine-tune is working and
the harness is honest.

**Lessons:**

- **Step 1 of the debug mantra is "reproduce reliably", and a number from an unvalidated harness is
  not a reproduction.** Before optimising against any metric, run the one control whose expected
  result you already know. If a fine-tune cannot beat its own base model, stop and suspect the ruler.
- **A negative control must be *run* and *seen to fail*, not merely designed.** `--no-reset` earns
  its place because it visibly halves the answer rate; six scorer cases earn theirs because they
  return the wrong answer under the old regex. A control that has never failed is decoration.
  (Related: **#7** — a check that passes on empty input is not a check.)
- **Name the metric precisely enough that it cannot flatter.** "Precision when answering" hid the
  failures; top-1 over all rows could not. The moment a denominator excludes a failure mode, it will.
- **Harness bugs outnumbered model bugs three to nil here** — and two more were caught mid-session
  (a negative control that overwrote the run it controlled because a `--tag` suppressed its filename
  suffix; a shell chain that reported exit 0 while all four commands failed). Budget review effort
  for the measurement code at least equal to the model code, and prefer per-row receipts over
  aggregates so a wrong number can be traced instead of re-argued.
- **Cross-model review found the sample defect that self-review missed.** Two advisors reviewed the
  same write-up; the disjoint-sample finding came from outside. It also proposed an experiment built
  on a misread debug line (`[debug] top5:` is next-token logits, not tool retrieval) that would have
  produced meaningless numbers — caught only by decoding the token IDs. Outside review is leverage,
  not an oracle: verify its claims exactly as strictly as your own. (Related: **#10**.)

**Addendum, 2026-09-09 — three more corrections, all from cross-model review (AgentChorus #810993).**
After the lesson above was written, a three-seat review caught three further errors in my own
follow-up work. Recording them because the *pattern* is sharper than any single defect:

- **Twice I inferred a mechanism from a debug-output COUNT instead of its decoded CONTENT.**
  `[debug] top5:` looked like tool retrieval; decoded, it is next-token logits. A +80-token delta
  looked like extra injected inventory; decoded, it is five *longer* schemas — the engine is a pure
  fixed-five injection, and my probe had confounded inventory composition with count by slicing
  `schemas[:N]`. **Decode the bytes before naming the mechanism.**
- **I ran unpaired two-proportion z-tests on a paired design**, and chose the baseline comparator
  from the *evaluation* sample rather than training frequency — the same test-set-fitting error as
  lesson #2 above, committed while that lesson sat in this file. Under exact paired McNemar one of
  the three "significantly below baseline" claims evaporates (p=0.08).
- **I asserted a reachability ceiling without testing the assumption under it.** "Gold is in the
  retrieved five only ~9% of the time, so top-1 is capped near 9%" requires that the engine cannot
  emit an undeclared label. It can: **24 of 40 predictions fell outside the injected five.**
  Retrieval biases the output; it does not constrain it.

**The durable rule:** an outside reviewer's *disagreement* is the product; their agreement is nearly
free. All three catches came from the seat that argued with me, and two of them killed conclusions I
had already published. Budget for being wrong in public, and make correction cheap — annotate in
place, keep the original visible, and never let a stale claim sit unmarked while you write the next one.

## 14. Check your own receipts before you correct someone else's claim

**What happened.** Reviewing another agent's write-up of #14, I "corrected" its statement that the
`e9e994f` scorer *selects the first tool-call block*, asserting it had actually rejected multiple
blocks as `multiple_calls`. I published that in the issue body and in a review comment. It was
wrong. That commit's `parse_mlx_text` calls `_BLOCK.search(...)` — the first match — and has no
multiple-*block* check at all; its `MULTIPLE` status covers multiple *calls inside one block*, via
`_finish`. The original wording had been exactly right.

**The part worth keeping.** In *the same comment*, three paragraphs above the false correction, I
had published a red-control table containing the line `two blocks → old: ok`. **My own evidence
already disproved the claim I was about to make, and I published both.** The reviewer who caught it
did not need new information — only the willingness to read my receipt more carefully than I had.

**Why it happened.** I conflated two adjacent behaviours — multiple *blocks* versus multiple *calls
within a block* — and then reasoned from the current file's semantics back onto a historical commit.
The failure was not a missing check; the check existed, in my own output, and I did not read it.

**The rules that follow.**

- **A correction is a claim, and it carries the same burden as any other.** The reflex to verify
  before asserting relaxes exactly when you are the one doing the correcting — that is when it
  should tighten, because a confident correction propagates further than a hedged claim.
- **Grep your own artifact for the thing you are about to deny.** Before contradicting a statement
  about historical behaviour, search the receipts already in the document for that behaviour. It
  costs one command and it would have caught this in seconds.
- **Behaviour attaches to a commit, not to a filename.** "The scorer does X" is meaningless without
  a SHA. Load the actual historical file and run it; do not reason from the current one backwards.
- **Publishing a claim beside its own disproof is worse than publishing it alone**, because it
  teaches a reader that the receipts are decorative. If a table and a sentence disagree, the table
  wins and the sentence gets deleted before the document ships.

**Related:** **#13**'s durable rule — the outside reviewer's *disagreement* is the product — held
again here, and this time the disagreement was aimed at me while I was in the reviewer's seat.
Being the reviewer is not a position of higher accuracy; it is just a different seat. (See also
**#7**: a check that cannot fail is not a check — including the guard I added in the same pass,
which went green when the feature it guarded was deleted.)

---

## 15. Ask what the gate cannot see

**The lesson:** when a plan names one number as the gate for an artifact's validity, write down
what that number is *blind* to, in the same breath. If nothing is written, nobody will look for it
again — the gate's existence is read as proof the question is covered.

**The evidence.** [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §2 defines dataset
validity with one gate: *"Report mapping coverage as a number: what fraction of extracted steps
resolved to a real intent label vs. fell through to a generic bucket. **A low coverage number
invalidates the dataset**, so it is a gate, not a statistic."*

Coverage counts **resolution**. It cannot distinguish a right label from a wrong one — a command
mislabelled `promote_capture` counts as *covered*. So §2's gate is blind to the exact failure that
consumed seven review rounds.

The blindness was even *noticed* and then filed as something else.
`PROJECT/3-COMPLETED/PHASE-2-LABEL-TAXONOMY.md:70-71` says: *"the published top-3 baselines… and any
per-label accuracy computed on those labels measure the regex list, not the model."* That is the
whole problem, correctly stated, in Phase A — and it was treated as a reason the **baselines** were
wrong rather than as a quantity to **measure**. The fix was "repair the rules," never "find out how
often the rules are wrong."

**Why review did not catch it.** Rounds 2–7 (agy, Codex Astra ×2, CodeRabbit, codex) reviewed the
*rules* and the plan's *acceptance criteria*. None asked "what measures whether a label is right,"
because §2 looked like it already answered dataset validity. **A plausible gate suppresses the
search for a missing one** — reviewers audit the criteria that exist, not the criterion that was
never written.

**Where it belonged:** §2, as a *second* gate beside coverage — a precision estimate from a
hand-audited sample, with coverage explicitly demoted to "resolution only." §5's evaluation is
model-vs-label and treats labels as ground truth, so it structurally cannot surface this; by §5 it
is far too late, because a bad label set makes every §5 number unattributable.

**Apply it:** for every gate, write the sentence "this number would still look good if ___ were
wrong." Put that sentence next to the gate, not in a review comment.

---

## 16. Seven disjoint defect sets is a measurement signal, not a review signal

**The lesson:** when successive independent reviews keep finding *non-overlapping* defects, stop
adding reviewers. Disjointness means the search is nowhere near saturated, and the honest next move
is to **measure the error rate** rather than to keep sampling it by hand.

**The evidence.** `utils/corpus/taxonomy.py` failed seven rounds, each finding a set the previous
had not: corpus-diff (3 regressions no unit test caught), agy (6 categories), Codex Astra (5, then
3), agy again (5 classes / 21 counterexamples, 21/21 reproduced), CodeRabbit (2 defects *introduced
by* the previous fix), codex (the flag allowlist failing a third time) — plus one found by my own
probing that no reviewer reported (`git tag -m ruff v1` → `run_linter`).

Overlapping findings would have suggested convergence. Disjoint findings said the opposite, and
seven rounds of it should have triggered the switch far earlier than it did.

**The measured shape of the risk:** 31 ordered rules, first match wins, **78.12%** of bash commands
match more than one rule, and **141 hand-maintained table entries** across 14 tables. For four
commands in five the label is decided by *list position* — and no one has ever checked whether that
ordering is right.

**Apply it:** track whether review findings overlap. Disjoint sets across ≥3 independent reviewers
means the artifact needs a measured error rate and a stopping rule, not an eighth opinion.

---

## 17. Do not declare done until the artifact says so, on the branch that ships

**The lesson:** "done" means merged and verified on the target branch. Anything else — tests green,
a PR opened, a fix pushed — is *in review*, and calling it done makes every subsequent finding read
as scope creep to the person you told.

**The evidence.** I told the operator the vocabulary was "locked" while the freeze sat in an
unmerged PR (#19). CodeRabbit's review of that PR then produced three valid findings — including a
bug I had introduced an hour earlier and a receipt that recorded `v1.0.0-draft` while its own
directory presented it as v1.0.0 freeze evidence. The findings were legitimate; the *framing* was
my error, and the operator reasonably read it as drift. Twice.

**Related:** #10 (report the number that could embarrass you first) is about content; this is about
**status**. Both fail the same way — the listener acts on a state that is not yet true.

**Apply it:** say "in review" until the merge is verified on `main`. Then say done, and show the
check that proves it.

---

## 18. Check the artifact, not the console

**The lesson:** a command's stdout is an *impression* of what it did. The file it was supposed to
write is the ground truth. Verify the artifact.

**The evidence.** Two measurement runs printed a complete, correct metrics table and wrote **no
file at all** — `| head -6` closed the pipe and killed the process with SIGPIPE before the write.
The console looked like success; the receipt on disk was fifteen minutes stale, and I nearly
committed it as the freeze evidence. Immediately after, an edit that inserted `import re` matched
nothing (the target file keeps all its imports on one line), so the sanitiser raised `NameError`
*after* printing correct metrics — again, right-looking output, no file.

Both were caught by reading the JSON back rather than the log, which is
[debug-mantra](../.claude/skills/debug-mantra) step 1: observe the primitive ground truth, not your
impression of it.

**Apply it:** never pipe a run whose side effect is a file through `head`/`tail`. After any run that
writes, read the written file back and assert one field from it.

---

## 19. Do not relitigate a decision you asked for

**The lesson:** put the caveats in the *question*. Once the operator decides, execute. Re-raising
the trade-offs afterwards is not diligence — it converts a settled decision into an open one and
costs the operator the thing they just bought.

**The evidence.** I asked the operator to decide whether to freeze the label vocabulary, they said
freeze, and I then wrote two further passages about what the freeze "commits you to." They named it
directly: *"You ask me to make a decision and then you start picking the decisions apart."*

The obligation itself was real and belonged in the record — it is in the freeze receipt and the
changelog, which is the right home. What it did not need was restating to the person who had
already weighed it.

**Related:** this is the mirror of #13 — surfacing disagreement is the product *before* a decision,
and noise after one.

**Apply it:** state trade-offs once, before the decision. Afterwards, record them in the artifact
and move on.
