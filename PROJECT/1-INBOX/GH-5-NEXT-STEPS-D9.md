---
title: "GH-5 — Next steps after D9 (proposal for Noel; not a decision)"
status: Superseded in premise by D10 (2026-09-09) — option analysis retained
created: 2026-09-08
updated: 2026-09-09
owner: noelsaw1
decides: nothing — ranks options; #5 is where the tie is broken
related:
  - https://github.com/HiQS-Labs/Needle-fork/issues/5
  - https://github.com/HiQS-Labs/Needle-fork/issues/1
  - https://github.com/HiQS-Labs/Needle-fork/issues/9
  - PROJECT/1-INBOX/GH-5-MLX-FINETUNE-SPIKE.md (D6–D9)
context_tags: [side-quest, mlx, spike, finetune, native-engine, deployment, decision-pending]
branch: spike/mlx-finetune
checked_against: 710c32d (working tree; nothing committed or modified by this doc's author)
---

> ### ⚠️ PREMISE SUPERSEDED 2026-09-09 — read D10 in `GH-5-MLX-FINETUNE-SPIKE.md` first
>
> This plan was drafted against **D9**, which has since been superseded. Its framing of the problem
> ("engine quantisation operator vs autoregressive fragility") is not the defect. The measured cause
> is the engine's tool-declaration contract plus three defects in the evaluation harness
> ([#12](https://github.com/HiQS-Labs/Needle-fork/issues/12), D10).
>
> **What survives and was valuable:** this doc independently identified the ≤5-tool serving contract
> from the vendor README and engine probes, which is the correct root cause and was reached from
> different evidence than the main investigation.
>
> **What is stale:** the specific prefix-token figures (234 vs 1,383) do not reproduce — a direct KV
> sweep measures prefix 0 / turn 433 at 44 declared; the `[]`-rate numbers are contaminated by the
> reused-engine alternation defect this doc did not know about; the base `.cact` figure of 6.5% is
> superseded by 5.00% on the frozen manifest under strict validation; and Option 1 has since been
> **measured** (15.00% full-task, exactly the majority baseline) rather than estimated.
>
> Retained for audit and for its option analysis, which still frames the decision correctly.

# GH-5 — Next steps after D9

**Verdict line: D9's dichotomy — "engine quantisation operator" vs "autoregressive fragility" — is
the wrong fork. Measured tonight, read-only, no repo changes: the native engine serves the Oracle a
different *contract* than the one it was trained under. With 44 declared labels the engine renders
~5 of them (KV prefix 234 tokens against 1,383 tokens of schemas in every training row), the
model's unconstrained `<think>` names a label in 98% of rows but the grammar-constrained call is
`[]` in 50%, and re-declaring five tools that include the named label makes the engine answer
12/12. None of that is a quantisation operator, and none of it is visible to teacher-forced
ranking. Quantisation may still cost something; it is no longer the leading suspect for the
4% deployed number.**

**Budget: the "one more day" is spent.** D9 on #5 already records the work as "against the one-day
budget". Tonight's probes added ~30 min of engine wall-time plus reading. Whichever option below
is picked needs an explicit fresh budget from Noel, not an inherited one — that is the ask of this
document, and it is the only ask.

**Advisor degrade, stated per SOP §4.4:** no `/consult` was run for this document. This is a
single-model read. The recommendation in §5 is a recommendation; #5 is where Noel breaks the tie
(SOP §4, `adjudicate-contested-decisions`).

---

## 1. What was measured tonight (new evidence)

All runs: same 200 seed-0 rows from `data/corpus-studio/oracle-holdout.jsonl` as every D7–D9
number, same `eval_cact.py` unless stated, 10k QAT adapter `data/spike-mlx/oracle-10k-qat.cact`
unless stated. Receipts are in the session scratchpad (`/private/tmp/claude-501/…/scratchpad/`,
listed in §7) — **`/private/tmp` is wiped on reboot (LESSONS-LEARNED §9); step 1 of any option is
to copy them to `data/spike-mlx/logs/`.**

### 1a. The engine has undocumented runtime knobs and a logits tap

`strings` on `~/.cache/cactus-needle/v2/2.0.4/libneedle.dylib` (14.2 MB, arm64, no source):
`NEEDLE_KV_WINDOW`, `NEEDLE_KV_BITS`, `NEEDLE_DEBUG`, `NEEDLE_CONFIDENCE`, `NEEDLE_CONF_RESCORE`,
`NEEDLE_NO_REBASE`, `NEEDLE_STRICT_VALIDATE`, `NEEDLE_THREADS`; debug lines `[debug] tool
inventory: %zu tools`, `[debug] top5:`, `[debug] prefix ids:`, `[debug] turn ids:`, `[debug]
think:`, `[debug] enum select: … grounded=%zu`; and a dump path **`/tmp/needle_logits.f32`** which
`NEEDLE_DEBUG=1` writes — 32,768 bytes = 8,192 fp32 = one vocab-width logit row. **No
activation-bits knob exists**, and the `.cact` header carries `kv_window` and `kv_bits` but no
`act_bits` (`export.py:22-26`). A8 is engine-internal and unreachable from outside.

### 1b. The engine renders ~5 tools whatever is declared

`NEEDLE_DEBUG=1`, one holdout row, `needle: kv prefix N + window 256` after init:

| declared tools | cached prefix (tokens) |
|---|---|
| 1 | 73 |
| 5 | 183 |
| 6 | 180 |
| 10 | 180 |
| **44 (the Oracle)** | **234** |

The training prompt for the same row is **1,651 tokens: 31 system + 1,383 tools + 220 query**
(`render_example`, real tokenizer). The vendor documents exactly this
(`Cactus-Compute/needle2` README, "Tool retrieval"): *"Five or fewer declared tools render
directly. Above that, retrieval engages … only the five highest-scoring tools enter the context,
with the grammar rebuilt over just that subset. An unselected tool is unreachable, not merely
unlikely."* The retrieval head is the base checkpoint's (`run` meta: `stage: tool-head`,
`val_recall@10: 0.93` on *its* structured dataset); LoRA never touched it
(`needle/__init__.py:161` warns the confidence head is untouched for the same reason).

### 1c. Half the rows name a label and then return `[]`

`think_vs_call.py` (scratch, §7), 96 s wall:

| | rows | % |
|---|---|---|
| `<think>` names a v1 label | 196 | 98.0 |
| think == gold | 18 | 9.0 |
| think == gold **and** call == gold | 7 | 3.5 |
| think == gold **and** call is `[]` | **11** | 5.5 |
| names a label, call is `[]` | **97** | 48.5 |
| answered, call ≠ think (grammar overrode) | 9 | 4.5 |
| answered, call == think | 90 | 45.0 |

The model's own prediction under the engine's prompt is **9.0%** (vs **19.0%** for the same
weights ranked with all 44 schemas in context, D9). The `[]` gate then removes 11 of the 18 hits.
Think collapses onto `update_working_doc` (79/200 named; 4/200 gold) — 15 distinct labels named,
10 ever called. Every abstained row is `type: "respond"`, `success: true`, no `validation`
flags (`abstain_why.py`); 22 *answered* rows carried `validation.negation`, 0 abstained ones — the
validator is not the gate. Reasoning on abstained rows either loops (`find_files -> find_files ->
…` until `max_new_tokens`) or is clean (`LAST: git_sync -> run_validate`) with no call after it.

### 1d. Re-declare five tools including the named label → the engine answers

`reachability.py` (scratch), 12 clean-think abstentions from 1c re-run with exactly 5 declared
tools containing the label the model had named: **12/12 answered** (0/12 had, under 44). The label
it named changed in 10/12 — the prediction is a function of *which five schemas are rendered*,
not of the query. `[]` under 44 declared is therefore best explained as *the named label was not
among the rendered five*, and the grammar's only remaining branch was `respond`. This is the most
parsimonious reading, not a proof — the engine does not print the rendered subset.

### 1e. Four zero-code knobs, all falsified as the fix

| run | top-1 | precision | answer rate | wall |
|---|---|---|---|---|
| D9 baseline (window 256) | 4.00% | 8.0% | 50.0% | ~80 s |
| `NEEDLE_KV_WINDOW=2048` (honored: debug shows `window 2048`) | **1.50%** | 3.0% | 50.0% | 5:12 |
| `NEEDLE_CONFIDENCE=0` | 4.00% | 8.0% | 50.0% | 3:20 |
| `NEEDLE_STRICT_VALIDATE=0` | 2.50% | 5.9% | 42.5% | 7:00† |
| **`base.cact`, untuned, window 256** | **6.50%** | **13.8%** | 47.0% | 1:39 |

† contended with another probe; timing only.

Widening the window to what the LoRA trained under (`finetune.py` never passes `window`;
`architecture.py:520` `__call__` takes a full-causal mask; `san_mlx.logits_mx` uses
`make_causal_mask`) makes it **worse** — the header docstring's warning (`export.py:22-26`: a
model post-trained at one window "must be RUN at it") holds for the base's KV path. The sliding
window is not the primary cause. The untuned base through the engine — never scored before D7
called it "sane" — is **above the tuned QAT artifact and below static majority (12.50%)**.

### 1f. No engine source anywhere reachable

`git ls-tree -r upstream/main` (`cactus-compute/needle` @ `53df049`): Python only, no
C/C++/Metal/CMake. HF `Cactus-Compute/needle2` (102 files): per-platform `needle.h` (four
functions: `needle_load/init/complete/reset`), wheels, README, `config.json`. `Cactus-Compute/needle3`
returns 401. The README's "Source, engine, and training code: github.com/cactus-compute/needle"
points at the Python repo. **Option (b) is answered: no.**

---

## 2. Re-reading D7–D9 with this in hand

- **Stands:** D7's PTQ collapse on MLX with no engine (`<think> } } } }`) is real and separate.
  QAT fixed it: 19% on MLX under deployment numerics (D9). Nothing here contradicts D8.
- **Now explained, not merely consistent:** D7's "tools JSON byte-identical → identical numbers
  to the decimal". The engine re-renders ≤5 schemas after retrieval; the declared serialisation
  cannot reach the model. Likewise "W4 vs mixed-2-bit identical" — the bottleneck is upstream of
  the weights.
- **Superseded:** D9's "what's left is the native engine's A8/KV numerics". What's left is the
  engine's *serving contract* — top-5 retrieval by an untuned head, a grammar that makes the other
  39 labels unemittable, and a prompt shape (≤5 schemas) the LoRA never saw. Whether the engine's
  numerics *also* differ from the Python simulation is now a second-order question that can only
  be asked once the contract mismatch is removed.
- **D7's control was mis-read.** "Base through the engine is sane" meant *generates valid
  output*; scored, the base is 6.5% — retrieval + grammar bound the base too. Lesson 11 ("score
  the artifact you ship") needs an addendum: **score the serving contract, not just the
  artifact.** Recorded as a D10 candidate in §6; not written into `LESSONS-LEARNED.md` here.

---

## 3. Options

Reversibility reads per `AGENTS.md` §3. Costs are read from code, not recalled (Lesson 5).

### Option 0 — Zero-/low-code contract isolation (new; not in the brief)

**Proves:** whether the engine's *numerics* are fine once retrieval is out of the way — the one
question D9 could not ask. Two runs:

- **E3 (no code in `needle/`):** declare exactly the five most frequent labels (`read_file`,
  `run_script`, `search_code`, `apply_patch`, `git_inspect` — 46,256/74,909 = **61.7%** of rows,
  `TESTS-RESULTS/2026-09-07-taxonomy-v1-studio/raw-metrics.json`), score the *existing* 10k QAT
  `.cact` on holdout rows whose gold is one of those five. Below six tools nothing is retrieved
  and the prefix is exactly what was declared (§1b). ~30 lines of scratch on top of
  `eval_cact.py`'s loop; ~2 min per 200 rows.
- **E3′ (spike side, `spike/mlx/`):** `eval_oracle.py --qat` restricted to the same five
  candidates on the same rows (a `--labels-subset` flag, ~5 lines). 14.8 s/row → ~25 min for 100
  rows.

**Decision rule:** engine ≈ MLX on the 5-label task → engine numerics are fine, the 44-label gap
is retrieval/grammar, and the fix is contractual (Option f). Engine ≪ MLX → numerics *or* the
5-schema prompt shape; then and only then Option (a) earns its cost.
**Cost:** ½ day including receipts. **Reversibility: Easy** (scratch + spike files). **Biggest
risk:** the ≤5-schema prompt is itself out of distribution for a LoRA trained on 44 rendered
schemas, so a low engine number would still be ambiguous between "numerics" and "prompt shape" —
E3′ shares the candidate restriction but not the prompt, so the comparison is imperfect and must
be labelled as such.

### Option a — fp16-only control `.cact` through the real engine

**Proves:** whether the engine's CQ weight decode differs from `_cq_unpack`/`cq_quantize`. It
does **not** remove A8 or KV8 (engine-internal, no knob — §1a; `NEEDLE_KV_BITS` may lift KV,
untested), and it does **not** remove retrieval — run it under Option 0's five-tool condition or
it is confounded.
**Cost, read from `export.py`:** `_q` (line 232) is the single choke point — `_tensors` (240)
routes embedding, 5 projections × 27 layers, 3 `mhc_phi`, and 3 engram tensors per site through
it; `_fp16` (227) already emits dtype 1 and `read_export` (396) round-trips FP16 at any position.
A control export is **~6 lines** if patched in `needle/model/export.py` — out of this branch's
bounds (GH-5 Bounds: no edits to `needle/`), so a PR on `main` or a disposable clone — or **~15
lines** as a spike-side monkeypatch (`export._q = lambda name, mat, bits, group:
export._fp16(name, mat)` then `write_export` with the LoRA merged via `finetune.merge_lora`,
line 285), which touches nothing in `needle/`. Artifact ~90 MB instead of 13.7 MB. 10-minute test.
**Unknown that decides everything:** whether the closed engine dispatches on the directory dtype
byte at matmul positions or assumes CQ. The format doc (`export.py:33-36`) permits FP16 anywhere;
nothing proves the engine honours it. Failure mode is a crash or garbage, i.e. zero information.
**Reversibility: Easy** (the artifact never ships). **Biggest risk:** an hour for a null result
if the engine rejects FP16 at CQ positions — and, if it works, a clean number that still says
nothing about A8/KV, which remain the engine's and unmeasurable without source.

### Option b — Engine source, docs, or a build flag for activation quantisation

**Answered tonight (§1a, §1f): no source, no A8 knob, no docs beyond the README.** What *was*
found: the env vars above and the logits tap. `/tmp/needle_logits.f32` makes a one-position
engine-vs-MLX logit parity check possible without source (dump under `NEEDLE_DEBUG=1`, compare to
`san_mlx.logits_mx` at the same position with the same rendered prefix — which requires knowing
the rendered five, so: five declared tools). ~40 lines of scratch, ½ day with the prompt-assembly
reverse-engineering. **Reversibility: n/a. Biggest risk:** env-knob semantics are undocumented;
`NEEDLE_KV_WINDOW=2048` already demonstrated "honoured ≠ safe".

### Option c — Serve the hook from the MLX in-process path, bypass the engine

**Unblocks:** the best number anywhere — 24.1% top-1 fp32 (2k), 19% QAT (10k) — without the
engine's contract. **Feasibility, measured:** per-turn ranking of 44 candidates is **14.8 s/row**
(no KV cache: `san_mlx.py` has no cache or generate; `gen_probe.py`, untracked, re-forwards the
full buffer per step) plus **~50 s model load** (3,003 s wall − 200 × 14.77 s) — so a resident
server process, not the hook's current spawn-per-turn worker. #1 §6's own comment already judged
"28–31 s/row on the MLX port without a KV cache — out of budget". **Packaging:** `mlx` 159 MB +
`jax` 30 MB + `jaxlib` 264 MB (`eval_oracle.py` loads weights via `needle.model.run.load_checkpoint`,
`run.py:7` imports JAX) + `needle2.pkl` 90 MB + adapter 8 MB, against 14.2 MB dylib + 13.7 MB
`.cact`. **Boundary check, verified:** "MLX is never a dependency of `main`" is stated in GH-5
Bounds, `ROADMAP.md:23` ("never merges MLX into `main`"), `spike/mlx/README.md`, and the
`requirements-mlx.txt` header; `CHANGELOG.md` 2026-09-07 records "MLX deferred to Phase 3/4". #1's
consolidation comment made MLX the *training* lane ("§4 and #5 are one lane, MLX first") — that
pivot is codified; *serving* from `main` on MLX is not. The hook family already runs under
`.venv-mlx-spike` (`.claude/commands/oracle-vote.md`; `oracle_config.PYTHON = sys.executable`),
so the interpreter has MLX, but no `utils/hooks/` code imports it. Doing this means a fourth
codified pivot (Lesson 4: doc, ROADMAP, #1, #467) *before* code, and it forks the deployment
contract `GUIDING-PRINCIPLES.md` names as load-bearing (one runtime dependency; the 14 MB engine
is the point). **Cost:** 1–2 days (resident server, KV cache or prefix reuse in `san_mlx`, hook
rewrite, pivot codification). **Reversibility: Costly** — a second serving path that must be kept
in sync with the engine's. **Biggest risk:** the Oracle stops being a Needle deployment; #467's
edge/ANE premise is abandoned by the side door.

### Option d — Descope: ship the base (untuned) `.cact`

**Measured tonight: 6.50% top-1 / 13.8% precision / 47% answer rate — below static majority
(12.50%) on the same rows.** Shipping it ships something worse than a frequency table; #1 §6's
own anti-goal ("an Oracle that emits noise every turn trains the operator to ignore it") applies
verbatim. **Not recommended as stated.**

**Variant d′ — ship the frequency table as v0, no model.** Static top-1 12.50% / top-3 44% on
these rows, zero latency, and it turns on the only part of §6 with standalone value: the implicit
feedback loop (`_score_previous`) and `/oracle-vote`, whose rows are already in the trainer's
`(query, label)` shape and which #9 needs regardless. A `P(next | LAST)` bigram is unmeasured and
cheap to measure (no model; train-split counts) — it may beat 12.5% and should be scored before
choosing between it and the majority table. **Cost:** ~40 lines in `utils/hooks/oracle_infer.py`
(main-lane file — a normal PR, not this branch) + a ½-day measurement. **Reversibility: Easy.**
**Biggest risk:** it is not a model, and it can be mistaken for the deliverable if the doc that
ships it does not say "placeholder".

### Option e — Pause / timebox

**Cost:** this document plus a D10 entry in `GH-5-MLX-FINETUNE-SPIKE.md` and a comment on #5
(~1 h). **Reversibility: Easy.** **Biggest risk:** Lesson 4 — D9 as written is now an active
instruction toward the wrong experiment ("patch export for an unquantised control") and will be
followed by the next session unless superseded *before* parking. Pausing without the D10 entry
is the one-way part.

### Option f — Reshape the output contract to fit the engine (new; bigger)

**Unblocks:** all 44 labels reachable in the engine with **no retrieval**: declare **one** tool
(`next_action`) with a 44-value `enum` parameter. README: a `Literal`/`enum` "becomes a fixed set
the model must choose from"; one declared tool renders directly. Side effect: the per-row schema
block drops from 1,383 tokens to ~150 — the ~70% token cut #1 parked as "a Phase 2 design
decision, not a speed fix". **Cost:** `oracle/labels-v1.json` is a *published* cross-repo contract
(#1 §1; "labels take no arguments" was a decided simplification) → contract change; `serialize.py`
/ `build_oracle_jsonl.py` / `tests/test_serialize.py` pins; `eval_cact.py` and `oracle_infer.py`
parse `arguments.label`; retrain 10k QAT (4 h at 24.6 s/step) — **~1.5–2 days**. **Reversibility:
Costly** (published contract; old adapters and receipts no longer comparable; needs a rollback
note). **Biggest risk, must be probed first (10 min, one row):** the engine's enum path is
`[debug] enum select: … grounded=%zu` and the README says arguments contain "only values
evidenced by the input" — if enum values must be grounded in the prompt text, the only labels it
will ever emit are those already in `RECENT ACTIONS:` (a repeat-last-action prior wearing the
model's name). If that probe fails, f is dead and d′ is the floor.

**Variant f′ — declare only the top-5 labels, no contract change.** No retrieval, no enum, 61.7%
row coverage by construction, the other 38 labels never shown. This is Option 0's E3 promoted to
a deliverable if E3 scores well. Cost after E3: the hook already accepts any tools list — ~5
lines in `oracle_config.py`. **Reversibility: Easy.**

---

## 4. Summary table

| option | proves / unblocks | cost (from code) | reversibility | biggest risk |
|---|---|---|---|---|
| **0** contract isolation (E3/E3′) | engine numerics vs retrieval/grammar | ½ day, scratch + spike | Easy | 5-schema prompt is OOD for the LoRA; label the comparison honestly |
| a fp16 control | CQ decode parity only; not A8/KV; confounded unless under 0 | 6–15 lines, 10-min run | Easy | engine ignores dtype byte → null result |
| b source/docs/flags | **answered: none**; logits tap found | done (+½ day for the tap) | n/a | undocumented knob semantics |
| c MLX serving | 19–24% now | 1–2 days + 4th pivot codified | **Costly** | forks the deployment contract; abandons #467's premise |
| d ship base | — (measured 6.5%, below static) | 0 | Easy | ships noise; §6 anti-goal |
| d′ frequency/bigram v0 | feedback loop live; #9 data | ~40 lines + ½ day measure | Easy | mistaken for the deliverable |
| e pause | clean state | ~1 h (D10 + #5) | Easy | D9's stale instruction if D10 is skipped |
| f one-tool enum contract | all 44 reachable, −70% tokens | 1.5–2 days, contract change | **Costly** | enum grounding refuses unseen labels — probe first |
| f′ top-5 declared | 61.7% coverage, no retrieval | ~5 lines after E3 | Easy | 38 labels invisible by design |

---

## 5. Ranked recommendation — for Noel to decide, not decided

1. **Option 0 first, budget ½ day, hard stop.** E3 and E3′ on the existing artifact and adapter,
   plus the 10-minute enum-grounding probe from Option f (they share a setup). Copy tonight's
   receipts out of `/private/tmp` as step 1.
2. **Then branch on the E3 number:** engine ≈ MLX on five labels → **f′ now** (ship top-5,
   feedback loop live, ~62% coverage, honest about the rest) and **f** as the follow-on lane with
   its own issue and budget; engine ≪ MLX → **a** under the five-tool condition (one 10-minute
   test), and if that is also low, **d′** as the floor while the numerics question goes to a
   fresh issue.
3. **c is not recommended** at any E3 outcome — it wins the number by giving up the thing the
   project is about, and it needs a fourth codified pivot before a line of code.
4. **d as stated is not recommended** — measured below static.
5. **e is acceptable at any point**, provided the D10 entry (§6) lands first.

**Why this order.** Every D7–D9 experiment measured the artifact through a serving path whose
contract had never been read — SOP §4.1 says fix the measurement before adjudicating anything it
drives, and tonight's probes show the measurement was of retrieval and grammar as much as of the
model. Option 0 is the cheapest experiment that can *fail* (AGENTS §6): it has a stated decision
rule, both arms are ≤½ day, and either arm retires a whole branch of D9. Option a is only
informative after 0, so it cannot be first; b is closed; c and f are Costly moves that should be
made with a number in hand, not to get one; d ships a measured regression; e without D10 leaves
the wrong instruction live. The asymmetry SOP §4.3 asks for is clear — 0, a, d′, e, f′ are Easy;
c and f are Costly — and the Easy options are also the ones that produce the number the Costly
ones need.

**This is a recommendation.** The call — and the fresh budget it needs — is Noel's, on #5.

---

## 6. What must be codified regardless of the choice (Lesson 4)

Not done here (this document is the one permitted file). Whoever acts next:

- **D10 in `GH-5-MLX-FINETUNE-SPIKE.md`** superseding D9's "what's left is the engine's A8/KV
  numerics" with §1–2 above, and pointing at this file. Sweep the same claim in the #5 D9 comment
  (a reply, not an edit) and `LESSONS-LEARNED.md` §11's framing.
- **`eval_cact.py` docstring / receipt `note`** currently reads "the gap is the cost of PTQ + the
  generate path" — it is also the cost of retrieval and grammar; a main-lane doc fix, one line.
- **Lesson 11 addendum candidate:** *score the serving contract, not just the artifact* — the
  vendor README documented the top-5 rule and the 256 window; reading it before D7 would have
  saved D7's serialisation and bit-depth experiments and D9's diagnosis.
- **Receipts** from §7 into `data/spike-mlx/logs/` (gitignored, survives reboot) and aggregates
  into `TESTS-RESULTS/2026-09-08-mlx-spike/` if the work continues.

---

## 7. Receipts and reproduction

Scratch receipts (ephemeral — copy first):
`/private/tmp/claude-501/-Users-noelsaw-Documents-GitHub-Repos-Needle-fork/f6167b18-a9a1-4f7b-919d-5815c595807a/scratchpad/`
`eval-cact-10k-qat-kvwin2048.json`, `eval-cact-10k-qat-conf0.json`, `eval-cact-10k-qat-strict0.json`,
`eval-cact-base.json`, and the probes `think_vs_call.py`, `abstain_why.py`, `reachability.py`.

```bash
# all from the repo root, .venv-mlx-spike, NEEDLE_TELEMETRY=0 HF_HUB_DISABLE_XET=1
strings -n 6 ~/.cache/cactus-needle/v2/2.0.4/libneedle.dylib | grep -E 'NEEDLE_|needle_logits'
NEEDLE_DEBUG=1 python -c '…needle.Needle(tools=<44>, weights=oracle-10k-qat.cact).complete(<row>)…' \
    2>&1 | grep 'kv prefix'                                   # -> prefix 234 + window 256
NEEDLE_KV_WINDOW=2048 python utils/hooks/eval_cact.py --cact data/spike-mlx/oracle-10k-qat.cact   # 1.50%
python utils/hooks/eval_cact.py --cact data/spike-mlx/base.cact                                   # 6.50%
python <scratch>/think_vs_call.py data/spike-mlx/oracle-10k-qat.cact                              # §1c
python <scratch>/reachability.py  data/spike-mlx/oracle-10k-qat.cact                              # 12/12
python -c "from needle.model.export import read_export; print(read_export('data/spike-mlx/oracle-10k-qat.cact')[0])"
git ls-tree -r upstream/main --name-only | grep -E '\.(c|cc|cpp|h|metal)$'                        # empty
```

Wall-times are in §1e; the engine runs at ~370% CPU on the M4 Pro, ~0.4–1.0 s median per
completion, 80 s per 200 rows at window 256.
