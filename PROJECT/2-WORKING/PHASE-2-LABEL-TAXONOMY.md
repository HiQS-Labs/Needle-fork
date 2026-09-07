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
| Adjudicated the `pkg_manage` decision — it dissolved: the 60-call count was an artifact of two bugs in our own labeler, and fixing them took it to **111**, above the floor. **40 of 44** labels now clear it. | Cut `v1.0.0-draft` → `v1.0.0`, then start §3's `query` serialization, the last design decision before training. |

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

**Done.** The Studio's `~/.claude/projects` was reachable as an SMB share
(`//noels-mac-studio.local/noelsaw`, mounted read-only), so the re-extraction ran
from this machine rather than needing a handoff. Receipt:
`TESTS-RESULTS/2026-09-07-taxonomy-v1-studio/`.

The extractor reproduced the handoff's session counts exactly — 359 used, 24 skipped
— so this is the same corpus relabelled, not a different sample.

| | local (17 transcripts) | **Studio (383)** |
|---|---|---|
| Pairs | 1,439 | **74,909** |
| Mapping coverage | 99.03% | **98.52%** |
| Governance share | 3.75% | **7.26%** |
| Static top-3 baseline | 46.91% | **45.82%** |
| Labels at/above 0.1% floor | — | **40 of 44** |

The local sample understated governance support by half but got the mechanism and
the baseline right to within ~1 point, which is the outcome that justifies having
designed the rules there.

### Both open decisions, resolved by data

1. **Label-set size — keep the set.** 40 of 44 labels clear the 0.1% floor (74
   calls). Only `park_roadmap_row` (68), `promote_capture` (14) and `publish_release`
   (1) fall below, plus `no_action` at 0 — which is expected, since it is produced by
   §3's `"answers": []` off-topic slice and not by labelling a call. #1 §1's "roughly
   20-30" understates what the corpus contains. (`pkg_manage` was on this list at 60
   until two of our own labeler bugs were fixed; it measures 111 — see the decision
   record at the end of this doc.)
2. **Governance support — traces carry it, at 7.26%.** 10 of 13 governance labels
   clear the floor, led by `update_working_doc` (1,356), `run_pdda_check` (961) and
   `run_validate` (927). §3b (doc synthesis) and §3c (git/PR mining) therefore stay
   **supplements**, needed for exactly the three thin labels — which are precisely
   the ones that land as commits with no corresponding prompt, the case §3c exists
   for.

### Coverage: 97.26% → 98.52%

The first Studio pass scored 97.26%. Diagnosing the unmapped remainder on a 60-file
sample found four fixable classes, now covered and regression-tested: MCP tools were
unmapped entirely (intent is in the tool name); `git -C <path> <verb>` broke every
git rule; `[ -f x ] && …` test conditionals were the largest single unmapped leading
token; and `python3 -m` / `npx` / `swift` / `$VAR/script.sh` / `sleep` were
uncovered. The residual 1.48% is mostly bare `echo`/`printf`, which is display rather
than action — left unmapped deliberately so the gate keeps its meaning.

- [x] Decide the two open items below — operator chose: size the set from Studio data
      via the support floor, and measure real governance support before planning §3b/§3c
- [x] Teach `extract_claude_transcripts.py` to record `file_path` and to import
      `taxonomy.label_call` instead of its own `BASH_RULES` — done and verified locally
      (16 sessions, 1,439 pairs, coverage 99.03%, governance share 3.75%)
- [x] Re-extract on the Mac Studio — done from this machine over SMB; coverage 98.52%
- [x] Apply the support floor (0.1% of calls) — 40 of 44 clear it; 3 real stragglers + `no_action`
- [x] Decide `pkg_manage` — **kept**; the decision dissolved once the measurement was fixed (below)
- [ ] Cut `label_set_version` from `v1.0.0-draft` to `v1.0.0` and re-publish the contract
- [x] Report the Studio coverage number to issue #1 as the §2 gate result

### Reproducing the Studio extraction

The Studio's home folder is an SMB share; its `Documents` share does **not** contain
`~/.claude`, and Remote Login is off, so SSH is not a route.

```sh
MNT="$(mktemp -d)"
mount_smbfs -o ro,nobrowse //noels-mac-studio.local/noelsaw "$MNT"
python3 utils/corpus/extract_claude_transcripts.py \
  --source "$MNT/.claude/projects" --out-dir data/corpus-v1
umount "$MNT"
```

The corpus lands in `data/corpus-v1/` (gitignored) and must never be committed.
Extraction is ~348 s over SMB but only ~12.5 s of CPU — it is network-bound, and
would be ~13 s run on the Studio itself.

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


---

## Decision record — the support floor is a supplementation gate

**Adjudicated 2026-09-07** against `GUIDING-PRINCIPLES.md`, `AGENTS.md` and `SOP.md`.
The process that produced it is `SOP.md` §4. Codified in four places so it is found
later: `utils/corpus/taxonomy.py` (the decision record, at the constant itself),
`oracle/labels-v1.json` (`support_floor`, so downstream consumers inherit it),
`CHANGELOG.md`, and here. Guarded by
`tests/test_taxonomy.py::test_support_floor_is_a_supplementation_gate_not_a_delete_gate`,
verified to fail when the rule is reversed.

### The rule

> A label below `SUPPORT_FLOOR_RATE` (0.1% of calls) is **flagged for supplementation**
> — issue #1 §3b governance-doc synthesis, §3c git/PR-history mining. It is **never
> deleted or merged on the strength of the floor alone.** Consolidating labels for
> training is legitimate, but belongs at the dataloader as a projection, never at the
> canonical taxonomy root.

### The case that set it

`pkg_manage` measured 60 calls, under the 74-call floor, and the open question was
whether to merge it into `run_script`. **Both numbers were wrong**, and wrong because
of bugs in our own labeler:

1. `uv add ruff` was labelled `run_linter` — the linter regex matched the package
   *name* as though it were an invocation. The same class of error as a `grep` whose
   pattern mentions a governance word, which we had already fixed once.
2. Dependency *inspection* (`pip list`, `pip show`, `brew list`, `pip freeze`,
   `npm ls`) had been tightened out of `pkg_manage` into `unmapped` when the regex
   moved from bare tokens to install-only subcommands.

Fixing both took `pkg_manage` from 60 to **111** — above the floor. There was no
decision to make; there was a bug to fix. **40 of 44** labels now clear the floor.

### Why the rule reads the way it does

| Rail | Bearing |
|---|---|
| `AGENTS.md` §6 — *"an empty input passes every check"*, *"a check that cannot fail is not a check"* | The floor is a number we invented, not a measured property. Letting it silently delete semantically distinct labels is a check reporting confidence it never earned. **Fix the measurement before adjudicating anything the measurement drives.** |
| `GUIDING-PRINCIPLES.md` — DRY, *"one source of truth per concept"* | DRY is about duplication, not rarity. "Mutate/inspect the dependency environment" and "run something ad hoc" are two concepts; collapsing them destroys meaning without removing any duplication. |
| `AGENTS.md` §3 — reversibility | Asymmetric. Keeping a label is **Easy** to undo (collapse with a dict at dataset-build time, downstream of both this file and the published contract). Merging is **Costly** to undo — it needs a re-extraction over a network share that is not always mounted. |
| `GUIDING-PRINCIPLES.md` — durable | Fixing the floor's *role* removes the root cause; re-litigating each sparse label one at a time is the band-aid that gets torn out at the next one. |

### Cross-model feedback

`/consult` **could not run**: `codex` is authenticated but its ChatGPT account
supports none of its models (HTTP 400 on `gpt-5.4`, `gpt-5.1-codex`, `gpt-5-codex`,
`gpt-5.1`, `gpt-5`), and `agy` needs an interactive `agy login`. Recorded because a
silent degrade would be worse than none.

A single independent read was obtained instead — Gemini (`gemini-flash-latest`) via
`aider`, run in a throwaway worktree. **This is one model, not a cross-model consult**,
and it broadly agreed with a framing supplied to it, so treat it as corroboration
rather than verification. It graded "adjudicating on uncorrected telemetry" a
**[Blocker]** against `AGENTS.md` §6, called the merge "semantic conflation, not DRY",
and independently proposed the same supplementation-gate reframing. Transcript is
not committed (it is scratch); the reasoning that matters is reproduced above.

### Still open

Nothing on this decision. `pkg_manage` stays, `run_script` stays, and the floor's
role is written down in four places.
