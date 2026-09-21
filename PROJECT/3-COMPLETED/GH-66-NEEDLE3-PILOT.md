---
gh_issue: 66
source: https://github.com/HiQS-Labs/Needle-fork/issues/66
title: "GH-66: rerun the #42 six-action pilot on Needle 3 (Cactus 3) with enum extraction"
status: Completed
created: 2026-09-20
updated: 2026-09-20
owner: Claude Code (operator go 2026-09-20)
doc_type: research
goal: measure whether Needle 3, fine-tuned the cheap way upstream ships with the six labels as one enum tool, beats Markov-1 on the frozen #42 holdout by the +5pp rule; stop if not
related: [42, 48, 62, 67, 68, 69]
effort: 3
complexity: 3
risk: 1
phases: 1
---

# GH-66 — Needle 3 six-action pilot (and Jev on the same rows)

Capture of [#66](https://github.com/HiQS-Labs/Needle-fork/issues/66); the issue body (revised
2026-09-18 after Agy QA) is the canonical plan and comparison contract. Branch
`experiment/needle3-pilot` from a fresh full clone, upstream 3.0.1 (`94df999`) merged in;
nothing from this issue lands on `main`.

## Status

| What was just completed | What's next |
|---|---|
| All ten plan steps executed 2026-09-20. **Needle 3 (20 layers, LoRA) 28/100 top-1; 7-layer rung 27; untuned base 20; Jev zero-shot 21; Markov-1 37. Falsifier (< 42%) triggered → arm stopped.** Validation loss fell every epoch (2.72 → 2.37 → 2.31); training 1 h 53 min wall on the M4 Pro. [Receipt](../../TESTS-RESULTS/2026-09-20-needle3-coding-core-pilot/SUMMARY.md). | Operator reads the receipt and closes #66 (or names the next bounded step; the receipt's suggestion is the #42 one — an explicit state/transition classifier vs Markov-1, and `phase_backoff` already sits at 42% on these rows). Follow-up candidate: record `qat_bits` in 3.0.1's `write_adapter` so native adapters pass the #8 guard without `--allow-numerics-mismatch`. |

## Ask

Rerun the #42 six-action coding-core pilot on Needle 3 under the same data, split, holdout and
baselines, labels as one `next_action` tool with a six-value enum; JAX on CPU with stock
`needle finetune` / `needle build`; score all 100 holdout rows top-1; stop below 42%. Time
permitting, the rung nearest Needle 2's 45M. Additive (operator ask, 2026-09-20): Jev zero-shot on
the same 100 rows as one Choice question, scored identically.

## Deviations from the body (posted on the issue before the long run)

- Host is the MBP 14" M4 Pro (the 2026-09-07 execution decision), not the Mac Studio; Python 3.11.
- The re-ported #8 guard refuses every native 3.0.1 adapter (no `qat_bits` provenance); the build
  passed `--allow-numerics-mismatch` as the body anticipates, and upstream's three finetune→build
  tests carry the same override.

## Files

- `spike/coding_core/to_needle3.py` (+ `tests/test_to_needle3.py`), `eval_needle3.py`,
  `jev_next_action.py`.
- `TESTS-RESULTS/2026-09-20-needle3-coding-core-pilot/` — SUMMARY, preflight, baselines, rung
  table, three eval JSONs, Jev results, timestamped training log. Aggregates only.
- `needle/` = upstream `94df999` + the two #8 hunks (34 lines); `tests/test_build.py` carries
  the guard's tests on 3.0.1 fixtures.

## Rating rationale (2026-09-20)

`rated 60/30/40/80` — pri 60: operator-authorized experiment gating a serving decision; sev 30:
no defect (one follow-up candidate on the guard's provenance field); appeal 40: a clean negative;
effort 80: upstream merge + converter + 2 h CPU training + three evals + Jev arm, ~$0.003 API.
