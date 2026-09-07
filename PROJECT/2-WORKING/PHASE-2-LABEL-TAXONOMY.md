---
title: "Phase 2 §1 — Freeze the v1 Oracle label taxonomy"
status: In progress
created: 2026-09-07
updated: 2026-09-07
owner: noelsaw1
goal: >
  Freeze the v1 label taxonomy for the Needle SDLC Oracle and publish it from this
  repo as the machine-readable cross-repo contract, with the §2 semantic-mapping
  coverage reported as a gate rather than a statistic.
related:
  - https://github.com/HiQS-Labs/Needle-fork/issues/1
  - https://github.com/HiQS-Labs/XYZ-forge/issues/467
context_tags: [phase-2, taxonomy, semantic-mapping, corpus, oracle]
effort: 3
complexity: 4
risk: 2
phases: 3
branch: main
---

# Phase 2 §1 — Freeze the v1 Oracle label taxonomy

## Status

| What was just completed | What's next |
|---|---|
| Built and tested the v1 taxonomy (44 labels), rewired the extractor onto it, and showed the first-pass labels were 74% decided by regex list order and carried **zero** governance labels. | Re-extract on the Mac Studio — one command, everything else is in the repo. |

## Table of contents

- [Phase A — Establish whether the existing labels can be frozen](#phase-a--establish-whether-the-existing-labels-can-be-frozen)
- [Phase B — Author and publish the v1 taxonomy](#phase-b--author-and-publish-the-v1-taxonomy)
- [Phase C — Re-extract on the Studio and freeze](#phase-c--re-extract-on-the-studio-and-freeze)

---

## Phase A — Establish whether the existing labels can be frozen

**Finding: they cannot.** Two independent defects, both measured, both in
`utils/corpus/extract_claude_transcripts.py` as shipped in `16bce0b`.

### A1. Three of every four Bash labels were decided by rule order, not by the command

The first pass matched an ordered 14-regex list against the **whole** command
string, first match wins. Measured over 1,220 local Bash calls:

| | |
|---|---|
| Commands that are compound (`cd X && A && B \| C`) | **97.9%** |
| Commands matching ≥2 rules | **74.0%** (against the original 14-rule list) |
| Commands matching exactly one rule | 22.9% |

When a command matches several rules, the label is whichever rule sits higher in
the list. Concretely, `git_mutate` was collecting `grep -n "some_symbol" app/x.py`
and `sed -n 1,120p ROUTER.md`, and `git merge-tree` (an inspection) was landing in
`git_mutate` because `merge` appears in the mutation alternation.

The handoff comment anticipated the sibling error — the leading-program table that
read 77.6% `cd` — but concluded *"the bucket rules search the whole command string
and are unaffected."* That conclusion is the defect: searching the whole string is
exactly what lets rule order decide the label.

Consequence: the published top-3 baselines (55.4% raw / 61.8% merged) and any
per-label accuracy computed on those labels measure the regex list, not the model.
§5's governance-vs-coding split would have been unreadable.

### A2. Governance labels were undetectable by construction

The extractor reads only `(block.get("input") or {}).get("command")`. It never
reads `file_path`. Measured locally, `file_path` is present on **100%** of
Edit/Write/Read calls and **26.6%** of them target a governance doc
(`PROJECT/**`, `ROADMAP.md`, `CHANGELOG.md`, `AGENTS.md`, `SOP.md`, `ROUTER.md`).

So `Edit` — 11.33% of the corpus and its 4th-largest label — collapsed
`update_changelog`, `file_capture_doc`, `park_roadmap_row` and ordinary code edits
into one indistinguishable token. Zero of issue #1 §1's governance labels appear
anywhere in the extracted corpus, which is why the label distribution reads as a
generic coding-assistant trace.

This is not fixable with better regexes over `command`. It needs a change to what
the extractor records, and therefore a **re-extraction**.

### A3. Tiering governance labels introduces its own false positives

Found while building Phase B, and worth recording because it nearly shipped.
Ranking governance above search means `grep -E "recon|merge|release|pdda" notes.md`
scores as `run_pdda_check`, and `rg -n "vendor" .xyz/relay-automation/CONSUMING.md`
as `start_relay` — a search that *mentions* governance outranking the search itself.
It inflated `run_pdda_check` 18→28 and `start_relay` 4→19.

Fix: a segment whose leading program consumes its arguments as data
(`grep`/`rg`/`cat`/`sed`/`find`/`ls`/…) **is** that program's label, and its
arguments are never inspected. The leading-program signal is only trustworthy here
because preamble segments are dropped first — which is precisely why the first
pass's leading-program table failed.

**Only the evidence strings exposed this; the counts looked better with the bug in.**
Hence `tests/test_taxonomy.py` asserts on what a command resolves to, never on totals.

### Phase A gate — met

- [x] Quantify the ambiguity rate → 74.0% (original list), 82.2% (v1 list)
- [x] Quantify governance detectability → 0 labels present; signal exists in `file_path`
- [x] Decide whether the shipped labels can be frozen → **no**, re-extraction required

---

## Phase B — Author and publish the v1 taxonomy

### What was built

| Artifact | What it is |
|---|---|
| `utils/corpus/taxonomy.py` | Single source of truth: `LABELS_V1` + `label_call()`. The extractor, trainer, evaluator and hook all import it, per §1's no-drift requirement. |
| `oracle/labels-v1.json` | The published cross-repo contract. **Generated**, not hand-written. |
| `utils/corpus/export_label_schemas.py` | Renders each label through this repo's own `needle/agent/tools.py` `build_schema`, per §1 bullet 3. |
| `utils/corpus/measure_taxonomy.py` | Reports the §2 coverage gate, per-label support, baselines and ambiguity. Emits a `TESTS-RESULTS/` receipt. |
| `tests/test_taxonomy.py` | 31 regression tests, all passing. |

### Design decisions, stated rather than assumed

1. **Segment, then resolve by tier.** Split on `&&`/`||`/`;`/`|`/newline; drop
   `cd`/env/loop-keyword preamble and display-only tails (`echo`, `head`, `wc`); label
   each remaining segment; the **highest specificity tier** wins, ties to the earliest
   segment. Tiers are `governance(3) > domain(2) > generic(1)` — generic transport verbs
   lose to anything more specific. This replaces "position in a list" with a documented,
   testable ranking.
2. **Heredoc bodies are not shell.** `python3 - <<'PY' … PY` is one action; splitting it
   produced the first pass's `bash_other` pile-up. It is now `run_script`, which is the
   single largest label locally at 17.7%.
3. **`file_path` carries the governance signal.** Path rules run before the native-tool
   map — but a `Read` of `CHANGELOG.md` stays `read_file`, because reading a governance
   doc is not a governance move.
4. **Each label records what signal it needs** (`native` / `command` / `path` /
   `path+content`). Two labels from #1 §1 — `update_status_table` and
   `repoint_roadmap_row` — need the **edit body**, which the corpus deliberately does not
   carry. They are dropped from v1 rather than frozen as labels that can never be
   learned; `update_roadmap` covers the ROADMAP case without claiming to know park vs repoint.
5. **Labels take no arguments.** Enforced by a test. Per Message 3's Ponytail Output
   Simplification the model predicts only a name; a label with parameters would
   re-introduce the JSON generation that was explicitly abandoned.

### Measured effect, same 1,438 calls, old labeler vs v1

Apples-to-apples on one sample — *not* a comparison against the Studio corpus's
published numbers, which were computed on a different and much larger corpus.

| | old (`16bce0b`) | v1 |
|---|---|---|
| Labels | 27 | 41 in use (44 defined) |
| Static top-1 baseline | 26.82% | **17.98%** |
| Static top-3 baseline | 68.66% | **46.27%** |
| Governance labels present | 0 | 54 calls (3.7%) |
| Fall-through bucket | 2.99% (`bash_other`) | **0.97%** (`unmapped`) |
| Mapping coverage (§2 gate) | 97.01% | **99.03%** |

The baselines going **down** is the point. Probability mass was concentrated in
buckets that were partly an artifact of rule ordering; spreading it across real
intents lowers the score a majority-class predictor gets, which is the honest bar.

### Phase B gate — met

- [x] Taxonomy authored as a shared module, not duplicated per consumer
- [x] Contract generated through `needle.agent.tools.build_schema`
- [x] Coverage reported as a gate — 99.03% local
- [x] Tests green — 31 passed
- [x] Receipt written to `TESTS-RESULTS/2026-09-07-taxonomy-v1/`

---

## Phase C — Re-extract on the Studio and freeze

Blocked on the operator: this machine holds 17 transcripts, the Studio holds ~420.
Every number in Phase B is a **rule-design** measurement on a small local sample. It
validates the mechanism; it does not size the label set.

- [x] Decide the two open items below — operator chose: size the set from Studio data
      via the support floor, and measure real governance support before planning §3b/§3c
- [x] Teach `extract_claude_transcripts.py` to record `file_path` and to import
      `taxonomy.label_call` instead of its own `BASH_RULES` — done and verified locally
      (16 sessions, 1,439 pairs, coverage 99.03%, governance share 3.75%)
- [ ] Re-extract on the Mac Studio; re-run `measure_taxonomy.py` there
- [ ] Apply the support floor (default 0.1% of calls) — merge or defer thin labels
- [ ] Cut `label_set_version` from `v1.0.0-draft` to `v1.0.0` and re-publish the contract
- [ ] Report the Studio coverage number to issue #1 as the §2 gate result

### Run this on the Mac Studio

Everything below is in the repo; nothing else needs building first.

```sh
python3 utils/corpus/extract_claude_transcripts.py --out-dir data/corpus
python3 utils/corpus/measure_taxonomy.py \
  --out TESTS-RESULTS/$(date +%F)-taxonomy-v1-studio/raw-metrics.json
```

The corpus overwrites `data/corpus/` (gitignored). The receipt is aggregates only and
is safe to commit. Labeling ~75,000 calls should take ~11s at the 6,580 calls/s
measured here.

### Open decisions — resolved 2026-09-07

1. **Label-set size.** *Resolved: let the Studio data decide.* Keep 44 as
   `v1.0.0-draft`; apply the 0.1%-of-calls support floor against the Studio corpus,
   merge or defer thin labels, then cut `v1.0.0`. Original framing below. v1 defines 44 against #1 §1's "roughly 20-30". The overage is
   real actions the corpus contains and §1 omits — `find_files`, `run_script`,
   `git_inspect`, `git_sync`, `read_issue`, `cloud_cli`, `session_control`. Dropping
   them re-creates the transport problem; keeping them exceeds the stated range. The
   support floor should settle it against Studio data, not preference.
2. **Governance-label support.** *Resolved: re-extract first, then decide.* Original framing below.

   Locally the governance groups are 3.7% of calls, and
   `promote_capture`, `complete_doc`, `file_capture_doc` and `cut_release` have **one
   observation each**. If the Studio corpus is similarly thin, the Oracle cannot learn
   the labels it exists for from traces alone — which is what #1 §3b (synthesize from
   the governance docs) and §3c (mine git/PR history) are for. That would make them
   load-bearing rather than supplementary, and worth sizing before training.

## Quad Concepts

- **Pain:** the shipped labels were 74% decided by regex order and contained zero
  governance labels → **Fix:** segment-aware labeling resolved by an explicit
  specificity tier, plus `file_path` as the governance signal.
- **Pain:** counts look identical whether a label is right or wrong → **Fix:** tests
  and review assert on matched evidence, never on totals.
