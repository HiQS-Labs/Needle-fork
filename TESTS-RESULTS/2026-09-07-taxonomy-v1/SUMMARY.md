# Taxonomy v1 — labeling-mechanism measurement

**Date:** 2026-09-07 · **Machine:** MacBook Pro 14" (Apple M4 Pro, 12 cores / 16 ANE, 25.8 GB, macOS 15.6)
· **Commit:** `16bce0b` · **Label set:** `v1.0.0-draft` (44 labels)
· **Issue:** [Needle-fork#1](https://github.com/HiQS-Labs/Needle-fork/issues/1) §1, §2

## Scope — read this before citing any number

This measures the **labeling mechanism** on this machine's 17 Claude Code
transcripts (1,446 tool calls). It is **not** a corpus measurement. The training
corpus at `data/corpus/` came from the Mac Studio's ~420 transcripts (74,897
pairs) and is untouched here.

So the old-vs-new table below is computed by running **both** labelers over the
**same** 1,446 local calls. It is not comparable to the 55.4% / 61.8% baselines
published from the Studio corpus, and those two numbers are not restated here as
if they were.

## Result

| | old (`16bce0b`) | v1 | |
|---|---|---|---|
| Labels in use | 27 | 41 | 44 defined |
| Static top-1 baseline | 26.82% | **17.98%** | lower is a more honest bar |
| Static top-3 baseline | 68.66% | **46.27%** | the number the Oracle is judged against |
| Governance labels present | 0 | **54 calls (3.7%)** | the point of the Oracle |
| Fall-through bucket | 2.99% `bash_other` | **0.97%** `unmapped` | |
| Mapping coverage (§2 gate) | 97.01% | **99.03%** | |

Baselines going *down* is the intended effect: probability mass that sat in
order-artifact buckets is now spread across real intents, so a majority-class
predictor scores lower.

## Why the old labels could not be frozen

| | |
|---|---|
| Bash commands that are compound | 97.87% |
| Commands matching ≥2 rules (original 14-rule list) | **74.0%** |
| Commands matching ≥2 rules (v1 30-rule list) | 82.21% |

Both lists are ambiguous under whole-string first-match-wins, which is the
labeling function the first pass used — so for most calls the label was chosen by
a rule's position in the list. v1 does not use that function: it segments the
command and resolves by an explicit specificity tier.

Separately, the first pass read only `command` and never `file_path`, so no
governance label was detectable at all. `file_path` is present on 100% of
Edit/Write/Read calls locally, 26.6% of them on governance docs.

## Timing — this machine

| Step | Wall |
|---|---|
| Read + label 1,446 calls across 17 transcripts | **0.22 s** |
| Full `measure_taxonomy.py` run incl. machine probe + receipt | **1.11 s** |
| `pytest tests/test_taxonomy.py` (31 tests) | **0.10 s** |
| Schema export | < 0.1 s |

Throughput ≈ **6,580 calls/s** single-threaded. Extrapolated to the Studio's
~75,000 calls that is ~11 s, so re-measuring there is cheap; the cost of Phase C
is the re-extraction, not the labeling.

## Status

`ok`. Machine-parseable record in `raw-metrics.json`.

## Caveats

- 17 sessions is a rule-design sample, not a statistical one. It validates that the
  mechanism resolves commands correctly; it cannot size the label set.
- Governance labels are thin here — four have a single observation. Whether that is
  a property of this machine or of the operator's SDLC is a Studio question.
- `raw-metrics.json` carries aggregates only; no prompt text, commands or paths.
