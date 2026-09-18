---
gh_issue: 67
source: https://github.com/HiQS-Labs/Needle-fork/issues/67
title: "GH-67: TypeSafe Jev zero-shot rerun of the #31 40-record purpose/area holdout"
status: in-progress
created: 2026-09-18
updated: 2026-09-18
owner: Claude Code (start-task)
doc_type: feedback
goal: score Jev jev-1.13.0 zero-shot on the frozen #31 holdout with the #547 metrics and report the comparison, without tuning on the holdout or sending non-public text
related: [31, 29, 57, 58]
effort: 1
complexity: 1
risk: 1
phases: 1
---

# GH-67 — Jev zero-shot rerun of the #31 purpose/area holdout

## Status

| What was just completed | What's next |
|---|---|
| Intake parked and promoted; recon of the #547 scoring code, holdout shape and data policy done; plan drafted. | Codex relay plan QA, then implement `spike/work_classification/jev_zero_shot.py` + test, run once on the holdout, write `TESTS-RESULTS/2026-09-18-jev-purpose-zero-shot/`, post to #67. |

## Observed problem

[#31](https://github.com/HiQS-Labs/Needle-fork/issues/31) ended with two weak classifiers on the operator-calibrated eight-purpose task (ModernBERT 23/40, TF-IDF 20/40) and no deployable area or rejection policy. The operator asked (2026-09-18, [XYZ-forge #709](https://github.com/HiQS-Labs/XYZ-forge/issues/709)) whether a zero-shot decision model, TypeSafe Jev, reaches the same bar with no training. Nothing in this repo can answer that today.

## Recon (base `f965a53`, clone `needle-fork-gh67-jev-purpose`)

- Scoring source of truth: XYZ-forge `TESTS-RESULTS/2026-09-10+GH-547-calibrated/run.py` at `430f432`. Text template `texts()`: `'Project: '+repo+'\nTitle: '+title+'\nDescription: '+description`. Metrics `metrics()`: `correct`, `raw_accuracy`, `macro_f1` (sklearn, `labels=` union of class list and truth, `average='macro'`, `zero_division=0`), confusion over that universe; area scored on records whose truth is non-null (38).
- Baselines from `results.json`: purpose tfidf 20/40 mF1 0.430, modernbert 23/40 mF1 0.370; area tfidf 12/38 mF1 0.206, modernbert 10/38 mF1 0.221. Majority purpose 17/40, area 4/38.
- Local data: `~/.cache/xyz-modernbert-calibrated/` — `holdout.json` (40 records: `id, repo, number, title, description, description_truncated, split, source_type, created_at`), `holdout-labels.json` (40: `purpose_primary`, `area_primary`, `confidence`, …), `taxonomy.md`, `validation.json` (32). `input-hashes.json` in the #547 dir carries sha256 for `holdout-labels.json` (`70aa61d4…`) and `taxonomy.md` (`2a373c3b…`); `holdout.json` itself is not in the manifest, so the runner also records its sha256 and the holdout `id` list hash.
- Repos in the holdout, all `PUBLIC` on 2026-09-18: XYZ-forge 22, rebalanceOS 5, Needle-fork 5, AEGIS-Sleuth-Slackbot 2, Orion-fork 2, XYZ-code-RAG 2, Model-catalog 2.
- Jev contract (docs, verified with one live call): `POST https://api.typesafe.ai/v1/systemone`, bearer key, body `{state, model, questions}`; Choice answer has `choice`, `probabilities`, `confidence`; response `model` is the versioned ID; `usage.input_tokens`. Limits: 32k state + longest question; max description here is 1,800 chars, so no truncation needed. Jaggedness relevant here: literal reading and indirection — the criteria must carry the taxonomy's boundary sentences, not just the label names.
- Existing conventions: research scripts live in `spike/<topic>/`, tests in `tests/test_*.py`, HTTP via `urllib.request` (`spike/coding_core/context_probe.py`), results in `TESTS-RESULTS/<date>-<slug>/`. No `requests` dependency in `requirements.txt`.

## Requirements

1. Score `jev-1.13.0` zero-shot on the 40 holdout records with one request per record carrying two Choice questions (`purpose`, `area`); criteria text = taxonomy v3 definitions verbatim (label → its definition sentence), state = the `texts()` string.
2. Same metrics as #547 for both axes, plus per-record `confidence` and a table of accuracy by confidence bucket (`<0.5`, `0.5–0.8`, `≥0.8`).
3. Freeze checks before the first request: sha256 of `holdout-labels.json` and `taxonomy.md` must equal `input-hashes.json`; every record's `repo` must be `PUBLIC` via `gh repo view --json visibility` (skipped records are reported, never sent).
4. Provenance: pinned model ID from each response, `usage.input_tokens` sum, sha256 of every request and response body, run UTC, script sha256. Published files contain aggregates, per-record predictions keyed by `id`, and hashes — no titles or descriptions.
5. No tuning on the holdout: the criteria strings are committed before the run; any wording change after a holdout request invalidates the run and requires a new results directory.

## Non-goals

- Training, fine-tuning, prompt iteration on the holdout, secondary labels, or a rejection policy.
- Any change to the `needle` runtime, the 44-label Oracle, or the #62/#59 gates.
- A TypeSafe SDK dependency; `urllib.request` is enough.
- Re-collecting or expanding the holdout.

## Smallest affected surface

- New: `spike/work_classification/jev_zero_shot.py` (~200 lines: freeze check, visibility check, request builder, scorer, writer; `--dry-run` builds requests and scores nothing; `--validation` targets `validation.json` for an optional wording check that must be recorded if used).
- New: `tests/test_jev_zero_shot.py` (scorer math on a fixture: 3-record case with one wrong purpose and one null area → expected counts and macro-F1; empty input rejected; criteria-string freeze hash asserted).
- New: `TESTS-RESULTS/2026-09-18-jev-purpose-zero-shot/{SUMMARY.md,results.json,requests.jsonl (hashes only)}`.
- Touched: `ROADMAP.md` pointer (promotion), `CHANGELOG.md` at iteration end.
- Nothing else. No existing writer is extended because no existing subsystem scores work-purpose in this repo; #547's `run.py` is in XYZ-forge and stays there.

## Dependencies and risks

- Key: the operator's local secrets file, read at run time from `TYPESAFE_API_KEY` or `--key-file`; never logged. Risk: 429 under dynamic limits → retry with backoff honoring `retry-after`, max 5 attempts, then abort the run (partial results are not published).
- `gh` must be authenticated for the visibility check; if unavailable the run refuses.
- macro-F1 needs sklearn; it is already in the test environment (`requirements-train.txt`). The scorer imports it lazily and the unit test skips if absent, matching `test_shortlist_eval.py`.
- Rollback: delete the results directory and the two new files; nothing else changes.

## Ordered implementation

1. Write `jev_zero_shot.py` with the criteria dict copied from `taxonomy.md`; commit it **before** any holdout call (freeze).
2. Write `tests/test_jev_zero_shot.py`; run `python -m pytest tests/test_jev_zero_shot.py -q` → green.
3. `--dry-run`: freeze hashes match, 40/40 repos PUBLIC, 40 request bodies built, token estimate printed.
4. Live run once: 40 requests, results written, `usage.input_tokens` summed.
5. Write `SUMMARY.md`: comparison table (majority / tfidf / modernbert / jev for both axes), confidence buckets, caveats (model-annotated labels, n=40, not unseen evidence, no promotion), cost.
6. Run `python -m pytest tests -q -m "not slow"` and `utils/pdda/pdda.sh run`; update `CHANGELOG.md`; commit; push to `origin/main` per the 2026-09-12 operator branch policy; post the summary to #67 and cross-link on XYZ-forge #709.

## Acceptance checks

- `pytest tests/test_jev_zero_shot.py` fails if the scorer miscounts the fixture or accepts an empty list (red control: mutate one expected count in the fixture and confirm the test fails, then restore).
- `--dry-run` exits non-zero on a hash mismatch (red control: run with `--hashes` pointing at a tampered manifest).
- `results.json` has 40 purpose predictions, 38 area truths counted, a `model` value of `jev-1.13.0` on every response, and request/response hash lists of length 40.
