# Jev next-action follow-ups — stability, wording, richer state — 2026-09-21

Tracking issue: [#77](https://github.com/HiQS-Labs/Needle-fork/issues/77). Follow-up to the Jev arm
of [#66](https://github.com/HiQS-Labs/Needle-fork/issues/66) (receipt
`TESTS-RESULTS/2026-09-20-needle3-coding-core-pilot/`), prompted by the verification round on
[Jev-unofficial-toolkit #21](https://github.com/HiQS-Labs/Jev-unofficial-toolkit/issues/21).
Same 100 holdout rows, same pinned `jev-1.13.0`, same client (`spike/work_classification/jev_zero_shot.py`
unchanged). Measurement only; #66's Needle 3 conclusion (28% < 42%, arm stopped) is not touched.

## Headline

| Arm | Runs | Top-1 (each) | Mean | Notes |
|---|---:|---|---:|---|
| #66 original (2026-09-20) | 1 | 21 | 21 | prescriptive wording, q1 state |
| Toolkit #21 replay (Astra, 2026-09-21) | 1 | 18 | 18 | byte-identical requests |
| **A. Stability** — identical requests | 5 | 18, 19, 20, 19, 19 | **19.0** | range 2; 18–21 across all 7 samples |
| **B. Wording** — "actually took next" | 5 | 21, 17, 20, 16, 20 | **18.8** | no accuracy effect; ≥ 0.8 rows drop to 0 |
| **C1. q3 state, history only** — real issue text | 3 | 27, 28, 29 | **28.0** | +9 over A, outside the noise floor |
| **C2. q3 state, rich** — + last call and its result | 3 | 30, 32, 28 | **30.0** | +2 over C1, inside the noise floor |
| Baselines on the same rows | — | majority 26 · repeat-last 22 · **Markov-1 37** · phase-backoff 42 | | fitted on the q3 train rows; identical to the q1 numbers |

Three answers:

1. **Noise floor.** Byte-identical requests to the pinned model return different answers run to
   run: 17 of 100 rows changed at least once across five replays (never more than two distinct
   answers per row; 83 rows stable), top-1 18–20. Any single 100-row Jev number carries about
   ±2 points of pure API noise; a difference below ~4 points between single runs means nothing.
2. **Wording is not the problem.** Descriptive wording scores the same (18.8 vs 19.0). It does
   change calibration: with "should take" Jev put 5–6 rows at ≥ 0.8 confidence (1 correct each
   time); with "actually took" it put none there in any of five runs.
3. **State is the problem, and specifically the issue text.** Giving Jev the actual issue
   description (up to 2,000 chars) instead of the pilot's 600-char window — of which ~190 chars are
   the OpenHands environment preamble and ~390 the start of the issue — lifts top-1 from 19 to 28
   on the same 100 calls. Adding the last tool call and its result on top adds ~2 more, which the
   noise floor cannot distinguish from zero. With the richest state Jev beats majority and
   repeat-last and still does not reach Markov-1 (30 vs 37).

## Rows

All arms run on the same 100 holdout calls from the same 2 instances (`numpy__numpydoc-101`,
`tobymao__sqlglot-2529`). The q3 projection (`prepare_openhands.trajectory_rows(..., context="q3")`)
was built by replaying the pilot's selection — first 100 source trajectories at revision
`35455389…`, resolved only, `sha256(instance_id)` split, 500/100 caps counted in the q1 projection
— and produced 500 train / 100 holdout q3 rows for the same 11 + 2 instances; per-row gold label
and full action history match the q1 rows 100/100 (verified before any request was sent), and
support is identical (holdout `read` 29, `run_command` 26, `edit` 19, `search` 19, `run_tests` 7;
train `run_command` 138, `read` 123, `search` 88, `edit` 73, `run_tests` 67, `git` 11). q3 audit
over the 13 instances: 676 coding calls, 636 eligible rows, 51 control resets, 38 unmatched or
empty results.

State per arm (characters, holdout):

| State | What it holds | min / median / max chars | Input tokens per run |
|---|---|---|---:|
| q1 (A, B) | `[coding-core-q1]` · first user message truncated at 600 (preamble + issue start) · history (≤ 12) · LAST | 673 / — / 795 | 66,528 |
| q3 history (C1) | `[coding-core-q3]` · `<issue_description>` cleaned, ≤ 2,000 · history · LAST | 214 / 322 / 789 | 60,501 |
| q3 rich (C2) | C1 + `PREVIOUS CALL: <tool + selected args>` + `RESULT: <last 2,000 chars of the tool output>` | 427 / 1,287 / 3,121 | 90,375 |

The C1 states are shorter than q1 on median because the issue descriptions in this holdout are
short (max task 597 chars); the gain comes from *which* text, not how much.

## Per-label recall (mean correct / support; mean predicted count)

| Arm | `read` 29 | `run_command` 26 | `edit` 19 | `search` 19 | `run_tests` 7 |
|---|---|---|---|---|---|
| A (q1) | 11.4 (28) | 0.2 (5) | 0.0 (8) | 4.6 (23) | 2.8 (35) |
| B (descriptive) | 10.4 (25) | 0.6 (7) | 1.4 (12) | 3.0 (18) | 3.4 (37) |
| C1 (q3 history) | 14.0 (30) | 0.0 (0) | 1.0 (1) | 12.0 (52) | 1.0 (16) |
| C2 (q3 rich) | 11.3 (21) | 5.0 (8) | 2.0 (14) | 10.0 (39) | 1.7 (17) |

With the real issue text Jev stops over-predicting `run_tests` (35 → 16) and starts recovering
`search` (4.6 → 12 of 19); the tool result is what first lets it predict `run_command` at all
(0 → 5 of 26). `run_command` — the majority class — remains the one every arm here and in #66
(Needle 3: 0/26) fails on.

## Confidence

- A: ≥ 0.8 rows 5–6 per run, exactly 1 correct in every run. B: 0 rows at ≥ 0.8 in every run.
- C2 pooled over 3 runs: conf < 0.5 → 45/171 (26%); 0.5–0.8 → 32/80 (40%); ≥ 0.8 → 13/49 (27%).
  More rows reach high confidence with the rich state (15–18 per run) but the high-confidence
  subset is no more accurate than the rest. On this task Jev's confidence does not identify a
  trustworthy subset in any arm.

## Complementarity (observation, not a proposal)

Majority vote of the three C2 runs vs Markov-1 on the same rows: both right 2, only Jev 28, only
Markov-1 35, neither 35. The two are close to disjoint — Markov-1 carries the sequential
regularity, Jev reads content — and their union covers 65 rows. The q1 arm shows the same shape
(0 / 20 / 37 / 43). Nothing here is authorized to act on it; it is recorded because it is the one
number in this receipt that points somewhere.

## Envelope

16 live runs, 1,600 requests, 1,117,908 input tokens, ≈ $0.05 at the #69 rate; 26–40 s wall per
run (median request 0.27 s). Question hashes: prescriptive `e97bc1c4…` (the #66 question, unchanged),
descriptive `b84be7a1…`. All 500 A-run request hashes match the #66 run's 100 hashes (5 × 100/100).
Wall for the 16 runs 7.9 min; the whole campaign including q3 row building (4.4 s, HF rows API) and summaries ~10 min.
Host: MBP 14" M4 Pro; no local model inference in this receipt.

## What this does not establish

- Why identical requests to a pinned model vary. The variation is measured (17/100 rows over five
  replays), not explained; the toolkit (#11 there) owns that question.
- Anything about Score/Noul decomposition, few-shot prompting, or a Jev + Markov-1 combination.
- Generality beyond 100 rows from two trajectories; the +9 for issue text clears the measured noise
  floor on these rows and nothing more.

## Provenance

Per arm: `run-N/results.json` (metrics, per-row index/gold/choice/confidence/probabilities, hashes),
`run-N/requests.jsonl` (request/response sha256 per row), `summary.json` (range, stability,
majority vote, agreement with the #66 run). `q3-provenance.json` (selection replay counts, q3
audit, support, state sizes, row-file hashes), `q3-baselines.json` (baselines fitted on the q3
train rows, per-row predictions). Scripts: `spike/coding_core/jev_next_action.py` (`--wording`,
`--state`), `q3_rows.py`, `jev_runs_summary.py`; tests `tests/test_jev_next_action.py`. No state
text is stored under this directory.
