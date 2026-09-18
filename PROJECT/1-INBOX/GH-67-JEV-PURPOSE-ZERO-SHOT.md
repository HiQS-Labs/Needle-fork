---
gh_issue: 67
source: https://github.com/HiQS-Labs/Needle-fork/issues/67
title: "GH-67: TypeSafe Jev zero-shot rerun of the #31 40-record purpose/area holdout"
status: Proposed (1-INBOX — not yet active)
created: 2026-09-18
updated: 2026-09-18
doc_type: feedback
effort: 1
complexity: 1
risk: 1
phases: 1
---

# GH-67 — Jev zero-shot rerun of the #31 purpose/area holdout

Capture of [#67](https://github.com/HiQS-Labs/Needle-fork/issues/67), Lane A of
[XYZ-forge #709](https://github.com/HiQS-Labs/XYZ-forge/issues/709). The issue body is the
canonical ask; this doc is the in-repo pointer.

## Ask

Re-score the frozen 40-record holdout from [#31](https://github.com/HiQS-Labs/Needle-fork/issues/31)
(XYZ-forge #547 calibrated round, input freeze `47baf02`) with TypeSafe Jev `jev-1.13.0` zero-shot:
one Choice question per axis (purpose, area), criteria verbatim from `TAXONOMY.md` v3, state = the
same `Project / Title / Description` text the #547 `texts()` function used.

Baselines on the same records: purpose ModernBERT 23/40 (57.5%), TF-IDF 20/40 (50.0%), majority 17/40;
area (38 labeled) TF-IDF 12/38, ModernBERT 10/38.

## Constraints

- No tuning on the holdout; criteria frozen before the first holdout request (iterate on
  `validation.json` only if wording needs it, and record the final wording).
- Verify `~/.cache/xyz-modernbert-calibrated/` against `input-hashes.json` before sending; abort on
  mismatch.
- Data policy: all 40 records are from `HiQS-Labs/*` repos verified `PUBLIC` on 2026-09-18; re-check
  at run time and skip any that changed.
- Same metrics as #547 plus per-record confidence and a confidence-vs-accuracy table.
- Log pinned `model`, `usage.input_tokens`, request/response sha256 per record; publish aggregates and
  predictions by record `id` only.

## Deliverable

`TESTS-RESULTS/2026-09-18-jev-purpose-zero-shot/` (runner, `results.json`, `SUMMARY.md`), summary
posted to #67.

## Rating rationale (2026-09-18)

This repo has no RELEASES ledger; per start-task policy the rating lives here and on the issue.
`rated 60/30/50/85` — pri 60: operator-requested, cheap, informs #57/#58; sev 30: no consequence if
skipped; appeal 50 neutral; effort 85: single script on frozen data. Recurrence: n/a.
