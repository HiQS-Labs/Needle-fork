# Taxonomy v1 — full Mac Studio corpus

**Date:** 2026-09-07 · **Corpus source:** `~/.claude/projects` on noel's Mac Studio,
mounted read-only over SMB · **Label set:** `v1.0.0-draft` (44 labels)
· **Issue:** [Needle-fork#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §1, §2

> **Status 2026-09-09: STALE — measured under superseded rules.** #16 corrected
> positional label assignment (322 labels move on the local corpus). The numbers
> below stand as the record of what this run measured and are **not edited**; they
> are no longer evidence about the current mapper. The §2 gate is re-opened in
> `PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md` until the Studio corpus is
> re-extracted. See `../2026-09-09-taxonomy-positional-fix/`.

Supersedes the local-sample measurement in `../2026-09-07-taxonomy-v1/`, which was
17 transcripts on the MacBook and could validate the mechanism but not size the
label set. This is the real corpus.

## Result

| | |
|---|---|
| Transcripts seen | 383 |
| Sessions used / skipped | **359** / 24 |
| Pairs | **74,909** |
| Split (by session) | 299 train / 60 holdout |
| **Mapping coverage (§2 gate)** | **98.52%** |
| **Governance share** | **7.26%** (5,441 calls) |
| Labels in use | 43 of 44 |
| Labels at or above the 0.1% floor | **40** |
| Static top-1 baseline | 16.80% (`read_file`) |
| **Static top-3 baseline** | **45.82%** (`read_file`, `run_script`, `search_code`) |

The extractor reproduced the handoff's session counts exactly (359 used, 24
skipped), so this is the same corpus, relabelled — not a different sample.

## The bar the Oracle must beat is 45.82%, not 61.83%

The previously published top-3 baseline of 61.83% was computed on labels that were
substantially an artifact of regex ordering: 97.9% of Bash commands are compound and
74% matched two or more rules under whole-string first-match-wins, so probability
mass piled into whichever buckets sorted highest. Spreading it across real intents
lowers what a static majority-class predictor scores.

**Report model accuracy against 45.82%.** A model scoring 60% against the old
number would look like a win while having learned less than one scoring 50% here.

## Both open decisions are now answered by data

**Label-set size — keep the set; the floor prunes nothing.** 40 of 44 labels clear the
0.1% floor (74 calls). Only four fall below, and all four are kept:

| label | calls | disposition |
|---|---|---|
| `no_action` | 0 | **Expected.** It is the abstention target produced by the `"answers": []` off-topic slice (#1 §3), not by labelling a call. Not a gap. |
| `park_roadmap_row` | 68 | Just under the floor. Detectable only via the `releases_app.py roadmap add` CLI form. |
| `promote_capture` | 14 | Genuinely rare in traces. |
| `publish_release` | 1 | Genuinely rare in traces. |

`pkg_manage` was on this list at 60 calls and is not any more. Two bugs in our own
labeler were suppressing it — `uv add ruff` scored as `run_linter` (a package *name*
read as an invocation) and dependency inspection (`pip list`, `brew list`, `npm ls`)
had been tightened out into `unmapped`. Fixed, it measures **111**. See the decision
record in `PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md` and `SOP.md` §4 for the
procedure that caught it.

So #1 §1's "roughly 20-30" understates what the corpus actually contains: 39 labels
are independently supported. The overage is real actions §1 omits (`find_files`,
`run_script`, `git_inspect`, `git_sync`, `read_issue`, `session_control`).

**Governance support — traces do carry it, at 7.26%.** This was the open risk, and
it resolves favourably: 10 of 13 governance labels clear the floor, led by
`update_working_doc` (1,356), `run_pdda_check` (961) and `run_validate` (927). The
local sample's 3.7% understated it by half.

The consequence for #1 §3: governance-doc synthesis (§3b) and git/PR history mining
(§3c) stay **supplements**, not load-bearing replacements. They are needed for
exactly three thin labels — `park_roadmap_row`, `promote_capture`, `publish_release`
— which happen to be the ones that land as commits without a corresponding prompt,
precisely the case §3c exists to cover.

## Coverage came from closing four gaps

First pass over this corpus scored 97.26%. Diagnosing the unmapped remainder on a
60-file sample found four fixable classes, now covered and regression-tested:

| gap | effect |
|---|---|
| MCP tools (`mcp__github__issue_read`, …) unmapped entirely | intent is in the tool name; mapped by longest prefix |
| `git -C <path> <verb>` | the `-C` flag broke every git rule — 25 leading-`git` commands unmapped |
| `[ -f x ] && …` test conditionals | largest single unmapped leading token (30) |
| `python3 -m`, `npx`, `swift`, `$VAR/script.sh`, `sleep` | interpreters and plumbing |

Result: 97.26% → **98.52%**.

## Timing

| | |
|---|---|
| Extract 383 transcripts (935 MB) over SMB | **347.9 s** wall |
| CPU time within that | **12.5 s** (3.6% CPU — bound on SMB reads, not labelling) |
| Throughput | ~5,990 pairs/s CPU |
| `pytest tests/test_taxonomy.py` (46 tests) | 0.11 s |

Run on the Studio directly and the extraction is ~13 s; essentially all of the 348 s
is network I/O.

## Status

`ok`. Machine-parseable record in `raw-metrics.json`.

## Caveats

- The corpus is **live** — sessions are written and rotated, so totals drift slightly
  between runs. 383 transcripts today vs 420 at the first extraction.
- `data/corpus-v1/` is gitignored and stays on the MacBook. It contains real prompt
  text and must never be committed.
- The 1.48% still unmapped is mostly bare `echo`/`printf` segments, which are display
  rather than action. Left unmapped deliberately so the gate keeps its meaning.
