---
gh_issue: 77
source: https://github.com/HiQS-Labs/Needle-fork/issues/77
title: "GH-77: Jev next-action follow-ups — 5× stability replay, wording ablation, q3 richer-state run"
status: Completed
created: 2026-09-21
updated: 2026-09-21
owner: Claude Code (operator go 2026-09-21)
doc_type: research
goal: measure the run-to-run noise of identical Jev requests, whether prescriptive wording explains the #66 result, and whether a richer state (issue text, last tool result) does — on the same 100 rows, against the same baselines
related: [66, 68, 69]
effort: 1
complexity: 2
risk: 1
phases: 1
---

# GH-77 — Jev next-action follow-ups

Capture of [#77](https://github.com/HiQS-Labs/Needle-fork/issues/77), the three measurements
proposed on [Jev-unofficial-toolkit #21](https://github.com/HiQS-Labs/Jev-unofficial-toolkit/issues/21)
after its verification round. Branch `experiment/needle3-pilot` (with #66).

## Status

| What was just completed | What's next |
|---|---|
| All three arms run 2026-09-21, 16 live runs. **A: identical requests score 18–20 (17/100 rows flip across replays). B: descriptive wording 18.8 vs 19.0 — no effect. C: real issue text lifts Jev to 28 (+9, outside the noise); adding the last tool result to 30 (+2, inside it); Markov-1 on the same rows 37.** [Receipt](../../TESTS-RESULTS/2026-09-21-jev-next-action-followups/SUMMARY.md). | Operator reads and closes #77. The one number that points somewhere — Jev-rich and Markov-1 are nearly disjoint in what they get right (union 65/100) — is recorded, not acted on; a combination would be a new bounded issue. The API non-determinism belongs to the toolkit (#11 there). |

## Ask

A: replay the #66 requests 5× and report the top-1 range and per-row stability. B: rerun with the
instruction reworded from "should take next" to "actually took next", 5×. C: build q3 rows for the
pilot's 13 instances, fit the #48 baselines on the q3 train rows, run Jev with history-only and rich
state 3× each, compare on identical rows.

## Files

- `spike/coding_core/jev_next_action.py` gains `--wording` and `--state` (defaults byte-identical
  to the #66 run, `questions_sha256 e97bc1c4…`); `q3_rows.py` (selection replay + q3 projection +
  baselines on those rows); `jev_runs_summary.py` (range, stability, majority vote);
  `tests/test_jev_next_action.py`.
- `TESTS-RESULTS/2026-09-21-jev-next-action-followups/` — SUMMARY, per-run results and hashes,
  per-arm summaries, q3 provenance and baselines. Aggregates only.

## Rating rationale (2026-09-21)

`rated 50/20/40/30` — pri 50: operator-requested; sev 20: no defect in this repo (the
non-determinism is the vendor's); appeal 40: two clean answers and one lead; effort 30: ~10 min,
1,600 requests, ≈ $0.05.
