# Studio raw-transcript scan — is the extractor losing governance? **No.**

**Date:** 2026-09-08 · **Issue:** [#9](https://github.com/HiQS-Labs/Needle-fork/issues/9)
**Source:** the Mac Studio's own `~/.claude/projects`, read over SMB — 947 MB, **385 transcripts**,
**418,946 lines**. This is the machine that ran the governance-heavy XYZ-forge and PDDA work, and
it is the source the scored corpus was built from.

## The question

Governance is scarce in the corpus. Two explanations point at completely different work:

- **(a) extractor loss** — the acts are in the transcripts and the labeller drops them. Plausible:
  [#2](https://github.com/HiQS-Labs/Needle-fork/issues/2) is an open, known labelling defect of
  exactly that class. A better filter would then recover real training data.
- **(b) genuine scarcity** — the acts are not in the transcripts at all, and no filter helps.

## The answer: (b), decisively

Every tool call in the raw transcripts, labelled through `utils/corpus/taxonomy.py` — the same
labeller the corpus build uses — against the full built corpus:

| | calls / rows | governance | share |
|---|---|---|---|
| **raw Studio transcripts** | 76,420 | 5,440 | **7.12%** |
| **built corpus** (train + holdout) | 74,428 | 5,318 | **7.15%** |

**Identical.** Per label, retention is 87–100%:

| label | raw | corpus | kept |
|---|---|---|---|
| `update_working_doc` | 1,331 | 1,306 | 98% |
| `run_validate` | 966 | 928 | 96% |
| `run_pdda_check` | 966 | 939 | 97% |
| `file_capture_doc` | 553 | 542 | 98% |
| `start_relay` | 473 | 473 | 100% |
| `update_roadmap` | 361 | 359 | 99% |
| `update_changelog` | 280 | 276 | 99% |
| `update_governance_doc` | 189 | 186 | 98% |
| `cut_release` | 123 | 123 | **100%** |
| `complete_doc` | 106 | 104 | 98% |
| `park_roadmap_row` | 78 | 68 | 87% |
| `promote_capture` | 13 | 13 | **100%** |
| `publish_release` | 1 | 1 | **100%** |

**The pipeline is working correctly. 7.15% is the ceiling from this source**, and a better regex
recovers nothing — there is nothing left to recover.

## Correction to an earlier figure

An earlier note in this campaign quoted the corpus at **4.70%** governance and treated the raw
scan's higher share as evidence of extractor loss. That 4.70% came from the **first 8,000 holdout
rows**, which are not label-representative. Corpus-wide the figure is **7.15%**, which matches raw
almost exactly and reverses the reading. The lesson is the one already in `LESSONS-LEARNED.md`
lesson 2: a convenience sample is not the population, and the comparison must be like-for-like.

## What it means for #9

The three labels with real volume in git history are the ones transcripts cannot supply:

| label | transcripts | git history |
|---|---|---|
| `park_roadmap_row` | 78 | **791** |
| `cut_release` | 123 | **349** |
| `complete_doc` | 106 | **156** |
| `promote_capture` | 13 | **67** |
| `publish_release` | 1 | **263** (11 in our repos) |

Governance acts are **outcomes**, and outcomes live in git. Transcript mining is closed as an
avenue; **#1 §3c's git-history mining is the route**, confirmed twice now from opposite directions.

`promote_capture` (13 transcripts / 67 git) and `publish_release` (1 / 11 ours) remain under the
75-row support floor from *both* sources combined, and need synthesis or an explicit below-floor
decision.

## Method

`spike/corpus/raw_gov_scan.py --root <studio>/.claude/projects --pass2 --all`. The `--all` flag is
load-bearing: without it the scan labels only regex-selected candidate lines, which inflates the
governance share by construction and is **not** comparable to the corpus.
