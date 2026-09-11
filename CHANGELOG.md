# CHANGELOG.md

Newest-first, dated end-of-iteration record. One entry per substantive iteration: what changed,
why, and the verification. See `PROJECT/PDDA.md` for the full contract.

## 2026-09-11

### Branch inventory and PR hygiene recorded

Triaged the five open PRs, the un-PR'd MLX research base, and merged branch families. Recorded
integration priorities and the #6 → #10 dependency in `doc/branch-triage-2026-09-11.md`.
AGENTS.md now requires explicit branch ownership through a PR or parked research disposition,
current review evidence, and post-merge reconciliation. No experimental merge or deletion occurred.

### README now leads with the fork's Oracle story

After the documentation reconciliation landed in PR #44, added a two-paragraph TLDR, a linked
experiment inventory and the pending in-domain milestone to README. Separated the experimental
fork claims from retained upstream package documentation. Documentation-only diff; existing
package setup and usage content preserved.

### Oracle findings and collaborator briefing reconciled

Added a two-paragraph executive summary with the experiment arc and evidence links; appended the
missing September 7–11 synthesis to FINDINGS.md. Recorded the Astra/Fable correction: repeat-last
is a baseline, the private-trained round is still pending, and reused evaluation scores do not
measure human acceptance. Documentation only; no runtime or experimental behavior changed.

### ZCode mapper correction targets three observed command shapes

The first ZCode blind audit found 69 errors in 200 reviewed rows. Three narrow, source-grounded
corrections now recognize shell test entrypoints, compound wait-and-poll commands, and edits to
already-completed project documents. The shared 44-label vocabulary is
unchanged. The old review set improves from 131/200 to 141/200 only as development evidence; it is
not a fresh post-change estimate and cannot qualify ZCode for training.

Three load-bearing assertions were witnessed failing before the mapper changed, then the complete taxonomy
suite and non-slow repository suite passed. A new frozen blind sample remains required before any
ZCode admission decision. Broad compound-command precedence and free-text-description rules were
deliberately excluded because they would guess across ambiguous multi-action calls and widen the
Claude mapper's blast radius.

## 2026-09-10

### Evaluation readiness now fails on capacity, not session count

An immutable refresh of the MacBook and Studio transcript sources isolates 2,913 evaluation
candidates across 32 sessions, clearing the frozen 30-session floor. The live-source attempt first
failed closed on transcript hash drift; rebuilding from a private snapshot made the source manifest
stable and preserved zero comparable overlap with correction, prior-audit, and legacy-training
boundaries.

The unchanged evaluation sampler still refuses before writing output. It excludes 100 events with
no auditable command or path text, leaving 2,813 reviewable rows across 38 labels. Its 40-row session
cap permits at most 604 rows, and the exact label-quota allocator can select only 541 of the required
1,000. The next action is therefore to collect independent, label-diverse sessions until the same
allocator succeeds. Ten additional full-capacity sessions is only a mathematical lower bound from
the raw capacity shortfall; the label mix can require more. No audit draw or training run started.
`sample_for_audit.py --check-only` now emits these post-filter metrics as aggregate JSON while
preserving exit 2 for an incomplete gate and writing no sample files. It computes label-constrained
capacity independently of the minimum-session rule, so that metric remains present when the session
floor is the reason a draw refuses. A pool too small to construct label quotas also emits structured
`INCOMPLETE` JSON with its inventory, raw capped capacity, and refusal reason.

### The label errors now have measured causes and a bounded feedback seed

All 61 adjudicated sorter disagreements from #20 were traced through the segmenter and rule matcher,
assigned a falsifiable primary cause, and weighted through the frozen sampling plan. Shell visibility
contributes an estimated 6.99 percentage points of corpus error, inline-program semantics 5.43,
multi-action one-label selection 4.46, taxonomy boundaries 2.66, direct rule defects 2.52, and
reference uncertainty 0.10. Treating all low-confidence cause judgments as unresolved leaves the
same top three causes.

`analyze_audit_causes.py` rejects missing, extra, stale-label, unknown-cause, empty-evidence, and
invalid multi-action classifications before writing an aggregate receipt. Its conservative feedback
seed contains 26 high-confidence reviewed corrections representing 12.31 percentage points of the
estimated error. They are development examples, not a holdout or a promise of equivalent model gain.
The next action is one unchanged-versus-corrected training comparison on fresh session-separated
evaluation rows; the frozen taxonomy and mapper stay unchanged for the comparison.

## 2026-09-09

### The label-correctness audit now measures the corpus it claims to measure

The frozen 399-row audit was internally complete, but its 84.71% headline pooled unequal
predicted-label strata and its Wilson interval described the sampled rows, not the corpus. The
unchanged adjudicated judgments produce a **77.84% population-weighted estimate** with a
stratified finite-population 95% sampling interval of **72.30–83.38%**. Governance predicted
strata estimate 94.32%; non-governance strata estimate 76.78%.

`score_audit.py` now rejects duplicate, missing, extra, unknown-label, invalid-confidence, and
allocation-mismatched inputs before writing output; performs the two-auditor adjudication path;
reports weighted estimates and full confusion pairs; and records the interval's limits.
`sample_for_audit.py` now reaches the requested target exactly or refuses, rejects reused non-empty
output directories, and assigns opaque IDs after the draw. Focused tests include red controls
against the previous permissive behavior, and the aggregate receipt was regenerated.
New plans require audit format v2; the frozen unversioned plan is accepted only through an explicit
`--allow-legacy-plan` compatibility switch recorded in the receipt.

The corrected weighting changes the next decision: `run_script` contributes about 10.86 percentage
points of estimated corpus error versus at most 3.46 points for `unmapped`. Issue #20's original
unmapped-first P1→P4 sequence and its ≤85%-proves-rule-order decision are superseded. The one next
action is to classify the existing adjudicated errors by observed cause and population-weighted
contribution before changing the mapper, vocabulary, or training path.

### Label vocabulary frozen as `v1.0.0`

`LABEL_SET_VERSION` cut from `v1.0.0-draft` to **`v1.0.0`**; `oracle/labels-v1.json`
regenerated through `build_schema`. 44 labels. Studio corpus at the freeze: 335
sessions, 71,763 calls, **coverage 96.41%**, governance 5.91%, top-3 bar 45.16%,
197 tests passing. Receipt: `TESTS-RESULTS/2026-09-09-taxonomy-v1.0.0-freeze/`.

The version guard was verified to fire rather than assumed: a contract still
stamped `v1.0.0-draft` is now refused by `serialize.load_schemas`.

**What is frozen is the label NAMES.** The sorter that decides which label a
command gets is not frozen and is still under repair (#17) — the two artifacts
version independently. Freezing also **commits the project to supplementation**
(#9): the contract says the support floor's action is `"supplement"`, never
delete or merge, and `promote_capture` (8) and `publish_release` (2) are kept on
that basis.

The final pre-freeze review (`codex`) returned FAIL, and its own reasoning is why
the freeze proceeded anyway: *"the freeze blocker here is sorter correctness, not
rarity alone… the contract can freeze label names while still requiring sorter QA
and supplementation."* Its blocker was fixed first (`7cd7150`).

**96.41% counts resolution, not correctness.** 78.12% of bash commands match more
than one rule and rule order picks the winner; nothing has been hand-audited.
Seven review rounds have found seven disjoint defect sets, which is not evidence
that the eighth does not exist.


### Positional label rules — role before operands, and the §2 gate re-opened

A command's **operands** were being read as if they were its **invocation**, so text a
command merely *displayed* or *carried* could score a governance label: `echo mv
PROJECT/1-INBOX/x.md ...` scored `promote_capture`, `chmod +x validate.sh` scored
`run_validate`. The fix establishes the command's role first (`ANY_POSITION_GATE`,
with per-clause `_is_move` / `_is_roadmap_tool` predicates) and only then reads its
operands with values intact — an earlier attempt that blanked quoted text was wrong in
*both* directions, missing unquoted display data and destroying the operands of a real
`mv "PROJECT/1-INBOX/a.md" "..."`.

**Mutation controls, not membership assertions.** The previous class control asserted
that a program was absent from a table, which shows the table's contents, not that the
guard is why a test passes — it was decorative. The controls now disable
`command_region` and require the class tests to go red. That caught a
mis-attribution on its first run: `touch requirements.txt` does **not** revert when
the positional guard is disabled; it was fixed by removing a rule alternative. Two
mechanisms had landed in one change and the wrong one had been credited. Both halves
are now pinned separately.

**Found by four independent reviews, each in code the previous had not seen** — a
corpus re-extraction diff (3 regressions no unit test caught), a headless `agy`
adversarial pass (6 categories), and two AgentChorus rounds with Codex Astra (5, then
3). Four disjoint defect sets is not evidence the search is exhausted; the review loop
was stopped by a bounded-pass rule, not by a clean round.

**The §2 coverage gate is re-opened.** The 2026-09-07 Studio measurement (98.52%) was
produced by the rules this change replaces, which move 322 labels. The acceptance
boxes in `PROJECT/3-COMPLETED/PHASE-2-LABEL-TAXONOMY.md` are unchecked and the
2026-09-07 receipt gains a STALE pointer with its numbers left unedited. The general
rule, now written down: *a measurement is scoped to the code that produced it* — an
acceptance box is a claim about current code, not a record that a run once happened.
Records belong in `TESTS-RESULTS/`; boxes revert.

Merging this does **not** freeze the taxonomy. `LABEL_SET_VERSION` stays
`v1.0.0-draft` and `utils/corpus/serialize.py` raises if a corpus artifact disagrees
with `taxonomy.py`, so the freeze remains a separate, enforced step.

Verification: `python3.11 -m pytest tests/ -q` → 253 passed, 6 skipped, 6 deselected;
local corpus 2,111 commands, coverage 98.77% → 97.92%, 322 labels change, 3 governance
losses (each verified a false positive), 0 gained; receipt in
`TESTS-RESULTS/2026-09-09-taxonomy-positional-fix/`.

### The §2 gate, re-measured — 96.33%, and a control that attributes the fall

The Studio corpus was re-scored under the corrected mapper once the share was mounted:
**335 sessions, 71,547 calls, mapping coverage 96.33%** (corpus: 71,186 pairs, 274/47
split). Receipt: `TESTS-RESULTS/2026-09-09-taxonomy-studio-postfix/`.

Coverage fell 2.19 points from 98.52%. The Studio's transcript set had *also* drifted
(383 files on 09-07, 337 now), so the raw delta confounded two changes. The **pre-fix
mapper was re-run over today's corpus as a control** — identical 335 sessions and 71,547
calls, mapper the only variable. It scores **98.52%**, exactly the 09-07 figure. Corpus
drift moved the gate **0.00 pp**; the entire fall is the rule change.

**The lower number is mostly the fix working — ~97% of it.** (Corrected 2026-09-09 by
GH-17: round 4 also dropped 45 real commands, +0.06 pp recovered once fixed. The
original claim here said "entirely", which the control did not support — it showed the
fall was *caused by* the rule change, not that every dropped call deserved dropping.)
Coverage counts resolution, not correctness.
Commands mislabelled from displayed text (`echo mv PROJECT/...` → `promote_capture`)
used to count as covered — covered by a wrong label — and now fall to `unmapped`. On the
identical corpus the fix removes **513 false governance calls** (6.61% → 5.90%), the
exact error class #2 reported, in the group this Oracle exists to get right.

Support floor: `park_roadmap_row` crossed it (68 → 96) because it had been losing real
calls to mislabelling; `promote_capture` fell 14 → 8 because six were display text. Two
stragglers now rather than three, both still #9's supplementation targets.

Unchanged and still the structural risk: `multi_rule_pct` 78.09% over 55,269 bash
commands, statistically identical to the control's 77.87%. The fix corrected *which*
rule wins positionally; it did not reduce how often several match.

## 2026-09-07

### Phase 2 §3 — `query` serialization is one shared function; token budget forces `--max-len 2048`

- Added `utils/corpus/serialize.py`: `serialize_query` (format `q1`, versioned, every line a
  citable anchor), `templated_reasoning`, `to_finetune_row`, `load_schemas`. It is the only
  place the model input is rendered; the corpus builder and the Stop hook both call it, so
  training-time and hook-time queries cannot drift (issue #1 §3, §6).
- Added `utils/corpus/build_oracle_jsonl.py`: `pairs.jsonl` → `oracle-{train,holdout}.jsonl`
  in the exact shape `needle/model/finetune.py` consumes. Refuses an empty split (§3's
  silent-drop hazard), writes via `.tmp` + rename so a crash cannot leave 0-byte files a
  trainer would accept as zero rows, and refuses a pre-v1 corpus by name.
- Added `utils/hooks/oracle_stop_hook.py`: the Claude Code Stop hook's serve side, built on
  the same `iter_steps` → `label_call` → `serialize_query` path as training. Logs query and
  latency to `data/hook-log.jsonl`; always exits 0; calls no model yet because no adapter
  exists.
- **Measured** with the real tokenizer: the 44 inline label schemas are **1,383 tokens**,
  over `finetune`'s default `--max-len 1024` on their own, and `_encode` truncates from the
  target end. Decision recorded in the project doc: keep full schemas, train at
  `--max-len 2048` (the architecture's `max_seq_len`; `run.py:182` enforces the same ceiling
  at inference). `--check-max-len` renders every row as the trainer will and refuses the
  build on overflow.
- Verification: `tests/test_serialize.py` (9 tests, incl. hook == trainer byte-for-byte) +
  `tests/test_taxonomy.py` → 68 passed, 1 skipped. Corpus re-extracted on the Studio under
  v1 end-to-end: 359 sessions, 74,428 pairs, coverage 98.52%, top-3 bar 45.99%.
  `build_oracle_jsonl.py --check-max-len` over all 74,428 rows with the real tokenizer:
  **longest rendered row = 1,950 tokens** — fits 2048 with 98 tokens of headroom, and
  would have been truncated at 1024. Split by session hash landed 48,744 train /
  25,684 holdout rows (63 of 359 sessions; a few long sessions fell on the holdout side).
  `abstain_rows: 0` — the `no_action` slice must come from §3b synthesis, not traces.
- Framework codified: **JAX/Flax** (the repo's declared stack; `doc/finetuning.md` confirms
  `jax-metal` is not viable on current JAX, so Apple Silicon trains on CPU — fine for a 45M
  LoRA). MLX deferred to Phase 3/4, recorded in #1 and umbrella #467.

### Phase 2 §1 — v1 Oracle label taxonomy authored, published and tested

- Added `utils/corpus/taxonomy.py` as the single source of truth for the label set
  (`LABELS_V1`, 44 labels) and the labeling function (`label_call`), so the extractor,
  trainer, evaluator and end-of-turn hook cannot drift apart (issue #1 §1).
- Published the cross-repo contract as `oracle/labels-v1.json`, **generated** by
  `utils/corpus/export_label_schemas.py` through this repo's own
  `needle/agent/tools.py` `build_schema` rather than hand-written. Labels take no
  arguments, per Message 3's Ponytail Output Simplification.
- Added `utils/corpus/measure_taxonomy.py`, which reports the §2 mapping-coverage
  **gate** plus per-label support, static baselines and the rule-ambiguity rate, and
  writes a `TESTS-RESULTS/` receipt. Receipts carry aggregates only — no prompt text,
  commands or paths — since `data/` is gitignored and this repo is public.
- Added `TESTS-RESULTS/README.md` adopting the Message 4 receipt protocol.

Why: the first-pass labels from `16bce0b` cannot be frozen. Measured on 1,220 local
Bash calls, 97.9% of commands are compound and 74.0% match two or more rules, so
whole-string first-match-wins let a rule's **position in the list** decide most
labels — `git_mutate` was collecting `grep -n …` and `sed -n 1,120p ROUTER.md`.
Separately the extractor read only `command` and never `file_path`, so no governance
label was detectable at all; `file_path` is present on 100% of Edit/Write/Read calls
and 26.6% of those target a governance doc. v1 segments the command, drops preamble
and display tails, and resolves by an explicit specificity tier; a segment led by an
argument-consuming program (`grep`, `cat`, `find`) is that program's label so that a
search *mentioning* governance is not scored as a governance move.

Effect, both labelers over the same 1,446 local calls: static top-3 baseline
68.66% → 46.27%, governance labels 0 → 54 calls, fall-through 2.99% → 0.97%,
mapping coverage 97.01% → 99.03%.

### Re-extracted the full Mac Studio corpus under v1

The Studio's home folder turned out to be reachable as an SMB share, so the
re-extraction ran from this machine instead of needing a handoff. It reproduced the
handoff's session counts exactly (359 used, 24 skipped), confirming this is the same
corpus relabelled rather than a different sample: **74,909 pairs, mapping coverage
98.52%, governance share 7.26%, static top-3 baseline 45.82%**.

Closing four coverage gaps found by diagnosing the unmapped remainder took the gate
from 97.26% to 98.52%: MCP tools were unmapped entirely (their intent is in the tool
name), `git -C <path> <verb>` broke every git rule, `[ -f x ] && …` conditionals were
the largest single unmapped leading token, and `python3 -m` / `npx` / `swift` /
`$VAR/script.sh` were uncovered. All regression-tested.

Both open decisions are now answered by data rather than preference:

- **Label-set size:** 40 of 44 labels clear the 0.1% support floor. Only
  `park_roadmap_row` (68), `promote_capture` (14) and `publish_release` (1) fall
  below, plus `no_action` at 0 — expected, since it comes from §3's `"answers": []`
  slice and not from labelling a call.
- **Governance support:** traces do carry it, at 7.26%, with 10 of 13 governance
  labels above the floor. §3b doc-synthesis and §3c git/PR-mining therefore stay
  supplements rather than load-bearing, needed for the three thin labels — which are
  exactly the ones that land as commits with no prompt, the case §3c exists for.

**The bar the Oracle is judged against is 45.82% top-3, not the previously published
61.83%**, which was computed on order-artifact labels.

### Adjudicated the `pkg_manage` decision — and it dissolved

`pkg_manage` measured 60 calls, under the 74-call floor, and the open question was
whether to merge it into `run_script`. **Both numbers were artifacts of bugs in our
own labeler:** `uv add ruff` scored as `run_linter` (the linter regex matched the
package *name* as though it were an invocation — the same class of error as a `grep`
whose pattern mentions a governance word), and dependency *inspection* (`pip list`,
`pip show`, `brew list`, `npm ls`) had been tightened out of `pkg_manage` into
`unmapped`. Fixed, `pkg_manage` measures **111** — above the floor. There was no
decision to make; there was a bug to fix.

Adjudicated against `GUIDING-PRINCIPLES.md`, `AGENTS.md` and `SOP.md`, the durable
outcome is a rule rather than a one-off call: **the support floor is a
supplementation gate, not a deletion gate.** A label below it is flagged for §3b/§3c
synthesis and is never deleted or merged on the floor alone; consolidating labels for
training belongs at the dataloader as a projection, not at the canonical taxonomy
root. DRY is about duplication, not rarity — "mutate/inspect the dependency
environment" and "run something ad hoc" are two concepts. Reversibility is asymmetric
(`AGENTS.md` §3): keeping a label is Easy to undo, merging is Costly.

Codified in four places so it is found later — `utils/corpus/taxonomy.py` (at the
constant itself), `oracle/labels-v1.json` (`support_floor`, so consumers inherit it),
`PROJECT/3-COMPLETED/PHASE-2-LABEL-TAXONOMY.md`, and here — and guarded by a test that
was verified to fail when the rule is reversed.

`SOP.md` gains **§4, "Adjudicating a contested decision"**, generalising the procedure:
fix the measurement first, cite the rail, read the reversibility asymmetry, consult
independently and state the degrade, codify in at least two places, and guard it with
a test you have watched fail. `AGENTS.md` points at it.

Cross-model `/consult` **could not run** — `codex` is authenticated but its ChatGPT
account supports none of its models (HTTP 400), and `agy` needs an interactive login.
A single independent read (Gemini via `aider`, in a throwaway worktree) agreed on all
five points, but one model that agrees with the framing it was handed is corroboration,
not verification, and is recorded as such.

Not yet done: `v1.0.0-draft` has not been cut to `v1.0.0`. Tracked in
`PROJECT/3-COMPLETED/PHASE-2-LABEL-TAXONOMY.md`.

Verification: `python3.11 -m pytest tests/test_taxonomy.py -q` → 46 passed;
`utils/corpus/extract_claude_transcripts.py` over the Studio corpus → 74,909 pairs,
coverage 98.52%; receipts in `TESTS-RESULTS/2026-09-07-taxonomy-v1/` (local
mechanism) and `TESTS-RESULTS/2026-09-07-taxonomy-v1-studio/` (full corpus);
`./utils/pdda/pdda.sh run`

## 2026-09-06

### PDDA installed

- Installed the PDDA document-automation surface (`utils/pdda/pdda.sh` + helpers, `PROJECT/PDDA.md`)
  and the `PROJECT/**` lifecycle tree in `observe` mode.
- Next: replace this entry as real iterations land.

Verification: `./utils/pdda/pdda.sh run`
