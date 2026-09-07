# CHANGELOG.md

Newest-first, dated end-of-iteration record. One entry per substantive iteration: what changed,
why, and the verification. See `PROJECT/PDDA.md` for the full contract.

## 2026-09-07

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

Not yet done: the corpus itself is unchanged. Re-extraction on the Mac Studio is
required before `v1.0.0-draft` can be cut to `v1.0.0` — tracked in
`PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md`.

Verification: `python3.11 -m pytest tests/test_taxonomy.py -q` → 31 passed;
`python3 utils/corpus/measure_taxonomy.py` → coverage 99.03%, receipt in
`TESTS-RESULTS/2026-09-07-taxonomy-v1/`; `./utils/pdda/pdda.sh run`

## 2026-09-06

### PDDA installed

- Installed the PDDA document-automation surface (`utils/pdda/pdda.sh` + helpers, `PROJECT/PDDA.md`)
  and the `PROJECT/**` lifecycle tree in `observe` mode.
- Next: replace this entry as real iterations land.

Verification: `./utils/pdda/pdda.sh run`
