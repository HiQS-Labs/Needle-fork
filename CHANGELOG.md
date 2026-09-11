# CHANGELOG.md

Newest-first, dated end-of-iteration record. One entry per substantive iteration: what changed,
why, and the verification. See `PROJECT/PDDA.md` for the full contract.

## 2026-09-11

### Coding-core OpenHands pilot stopped at the cheap promotion gate

- Added a reversible six-label projection (`read`, `search`, `edit`, `run_tests`, `run_command`,
  `git`) without changing the canonical 44-label Oracle contract.
- Added a bounded, revision-pinned OpenHands preparation path and static baselines. Raw trajectories,
  generated JSONL, weights, and detailed receipts remain ignored under `data/`.
- Trained one 29-step MLX LoRA pilot on 500 projected rows. On the instance-separated 100-row public
  holdout it scored 27% top-1, versus 26% majority and 37% Markov-1. The predeclared gate therefore
  failed; no synthetic balancing, larger run, private evaluation, or serving integration followed.
- Verification: 13 focused tests passed; the full non-slow suite passed with 195 tests, 6 skipped,
  and 6 deselected.

### Coding-core pivot promoted a phase-aware transition classifier

- Extended the existing baseline evaluator with one standard-library phase-aware backoff candidate;
  no model, dependency, taxonomy, or serving surface changed.
- Frozen development gate: at least 42% top-1, five points above the existing 37% Markov-1 result.
  The candidate scored exactly 42/100 and therefore advances only to one disjoint private check.
- Higher-order transition history alone scored 37%, 37%, 37%, 32%, 31%, and 30% for maximum orders
  1–6, so sequence depth was rejected. Raw issue-text learning was also rejected because the 500
  rows contain only 11 repeated training-instance requests.
- The CLI receipt now carries train/holdout hashes and exits nonzero when the frozen gate fails. A
  43% red control exited 1 before the restored 42% gate passed.
- Added a fail-closed projection of the private canonical Oracle pairs into the six-label view. On
  23,442 eligible actions from 63 held-out sessions, the frozen classifier scored 25.23%, missing
  its 33.78% gate and trailing Markov-1 at 28.78%; repeat-last scored 43.52%. The classifier arm is
  stopped. This identifies action persistence—not transferred OpenHands transitions—as the next
  smallest product hypothesis.
- Verification: 16 focused tests and the full non-slow suite passed (198 passed, 6 skipped,
  6 deselected); Python compilation and `git diff --check` passed. The private projection test was
  also witnessed red by deliberately misprojecting `run_tests`, then restored green.

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
`PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md`, and here — and guarded by a test that
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
`PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md`.

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
