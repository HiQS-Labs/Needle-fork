# RELAY · Needle 67 Jev zero-shot plan QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-18.
-->

NEXT: Producer
STATUS: Open
ROUND: 2 / 3

## ▶ TAKE YOUR TURN — read this first (works for ANY agent: Claude, Codex, agy)
1. **Read this whole file** (header, Setup, Ground rules, every block in the Log).
2. **Check it's your turn:** `NEXT` (top) names the role to act. Confirm you are bound to it and the
   last Log block isn't already yours. If not → STOP and reply "wrong window — nudge the <other> window."
3. **Do your role's work** on the artifact named in Setup:
   - **Reviewer:** review vs the Definition of Done → graded findings
     (`[Blocker]`/`[Should]`/`[Nit]`/`[Pass]`), each with a concrete fix → set a **Verdict**
     (Approved | Changes requested | Blocked). **Review the whole file, not just the diff** (GH-268):
     a beta test had this loop reach `Approved` in two rounds while an independent audit of the same
     branch found 20 issues (1 critical, 4 high) — every one of them in the pre-existing code the
     change sat on, which nobody had read. Pre-existing defects in a file you are touching are IN
     SCOPE; if you find none, say so explicitly rather than leaving it unstated.
     **Declare it: every review block must contain a literal `swept file: yes` or `swept file: no`
     line.** Without it a reviewer that skipped the sweep is indistinguishable in the transcript from
     one that did it and found nothing — which is how the original 20 issues stayed invisible.
     Any `[Pass]` or "verified"/"confirmed" finding MUST
     carry a quoted span or a `file:line` citation — an uncited one is mechanically downgraded to
     `[Unverified — no citation]` (GH-173 B3). Do **not** edit the artifact; only append findings here.
   - **Producer:** log a disposition for every open finding (Implemented / Modified / Declined + why),
     make the change, then add new work.
4. **Append ONE block** at the very bottom, directly **above** the marker line. Never edit earlier turns.
5. **Update the header:** flip `NEXT`; set `STATUS` (`Approved` closes — Reviewer only; else `Open`);
   the Producer bumps `ROUND` when opening a new cycle. If the max `ROUND` ends without `Approved`,
   set `STATUS: Escalated`.
6. **Commit only the relay file** (`relay(needle-67-codex-plan-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: **GH-67-JEV-PURPOSE-ZERO-SHOT.md** (embedded below — read it here).
- Reviewer: agy   ·   Producer: claude-a
- Started: 2026-09-18

### Artifact — GH-67-JEV-PURPOSE-ZERO-SHOT.md
```
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
```
- Definition of Done: _<fill in the acceptance criteria the Reviewer grades against>_

## Definition of Done and review questions (Reviewer: answer every numbered item)

**Goal.** Pre-implementation QA of the GH-67 plan (embedded above). No code exists yet; grade the plan, its recon claims, its protocol fairness, and its acceptance checks.

**Operational envelope.** One offline research script (`spike/work_classification/jev_zero_shot.py`, ~200 lines, stdlib `urllib` + lazy sklearn for macro-F1), one pytest file, one results directory. It runs once, by the operator, on 40 records. No SDK, no training, no service, no retry framework beyond a five-attempt loop. This repo works on `main` with scoped commits per `AGENTS.md` "Branch and PR hygiene" (operator revision 2026-09-12). Grade against this envelope and commensurate complexity.

**Read in the worktree (read-only):** the embedded plan; `AGENTS.md` lines 108–128; `spike/coding_core/context_probe.py` (`fetch_json`, the `urllib` convention); `spike/coding_core/README.md`; `tests/test_shortlist_eval.py` (test convention, sklearn skip pattern); `ROUTER.md` canonical rules. The #547 scoring code lives in XYZ-forge (`TESTS-RESULTS/2026-09-10+GH-547-calibrated/run.py` at `430f432`), not here; the plan quotes its `texts()` and `metrics()` definitions — grade those quotes as claims.

**Questions.**

1. Fairness: the holdout was already observed by the #31 round. The plan scores Jev zero-shot on it with criteria frozen (committed) before the first request and forbids wording changes afterwards. Is that a fair comparison against the ModernBERT/TF-IDF numbers? What else must the protocol forbid or record (e.g. no reading `holdout-labels.json` until scoring, no `--validation` runs after the holdout call)?
2. Area question design: the taxonomy says "null if no supported area or inadequate context", and 2 of 40 truth areas are null; #547's heads forced a class and scored the 38 non-null rows. A Jev Choice must pick one option. Should the area question add a `none` option (changes comparability) or keep the 12-class set and score on 38 (matches #547)? Pick one with a reason.
3. Criteria fidelity: "definitions verbatim from taxonomy v3" — is a label→definition-sentence map the right criteria shape for Jev's documented literal-reading failure mode, or must the boundary sentences (e.g. "a comparison plan is research_evaluation, not planning") be included? Concrete fix if so.
4. Metric parity: are `correct`, `raw_accuracy`, `macro_f1` (sklearn, `labels=` union of classes and truth, `average='macro'`, `zero_division=0`) reproducible as described? Is the lazy sklearn import + test skip pattern consistent with `tests/test_shortlist_eval.py`?
5. Data policy: the visibility gate is `gh repo view --json visibility == PUBLIC` per record repo, re-run at run time. Is that sufficient for "only public HiQS-Labs content leaves the machine"? Any leak path via descriptions (up to 1,800 chars) that the gate does not cover? Keep the answer to what a 40-record one-shot run needs.
6. Provenance: pinned response `model`, `usage.input_tokens`, request/response sha256 per record, script sha256, run UTC, `holdout.json` sha256 and id-list hash. Anything missing for a later reader to trust the number?
7. Acceptance checks: does `tests/test_jev_zero_shot.py` as described detect a miscounting scorer and reject empty input? Is the hash-mismatch red control for `--dry-run` sufficient? Anything that lets a broken scorer pass?
8. Surface: name anything in the plan that is machinery beyond the envelope (`--validation` mode? five-attempt retry?) and anything missing (e.g. a fixture file, a `pyproject` marker)?
9. Rating: is `rated 60/30/50/85` grounded (appeal 50 neutral, effort = cheapness)?

Output: graded findings (`[Blocker]`/`[Should]`/`[Nit]`/`[Pass]`), each with a concrete fix and a `file:line` or quoted-span citation; every behaviour-change request carries `Observed input:` / `Affected scope:` / `Falsifier:`. Then a Verdict. `swept file: yes|no` line required.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

### Reviewer (agy) — Round 1

swept file: yes

- **[Blocker] 4. Metric parity (sklearn vs manual)**
  - **Observed input:** Plan claims "macro-F1 needs sklearn... The scorer imports it lazily and the unit test skips if absent, matching `tests/test_shortlist_eval.py`."
  - **Affected scope:** Dependencies and tests (`jev_zero_shot.py`).
  - **Falsifier:** `tests/test_shortlist_eval.py` does not import or use `sklearn`; it relies on `spike/coding_core/shortlist_eval.py` which computes macro metrics manually using standard Python.
  - **Concrete fix:** Remove `sklearn` from the plan. Compute `macro_f1` manually without adding a new dependency, exactly as `shortlist_eval.py` does.
- **[Blocker] 5. Data policy (Leak path)**
  - **Observed input:** Visibility gate checks `gh repo view --json visibility == PUBLIC`, but `holdout.json` is not in the frozen manifest.
  - **Affected scope:** Data policy and security.
  - **Falsifier:** A tampered `holdout.json` could contain injected/redacted sensitive text in its `description` field. The visibility gate only checks the `repo` string, allowing the tampered description to be exfiltrated to the API.
  - **Concrete fix:** The protocol must explicitly assert the sha256 hash of `holdout.json` against a known-good hardcoded hash before making any requests, ensuring the text sent is exactly the agreed-upon public snapshot.
- **[Should] 1. Fairness (Validation mode & labels)**
  - **Observed input:** Plan allows `--validation` mode for wording checks and reads `holdout-labels.json` for hashing.
  - **Affected scope:** Fairness protocol.
  - **Concrete fix:** Explicitly forbid running `--validation` *after* any holdout call to prevent post-hoc tuning. Specify that `holdout-labels.json` must NOT be parsed into memory for logic until all API requests are complete (only hash it as bytes).
- **[Should] 3. Criteria fidelity (Boundary sentences)**
  - **Observed input:** "criteria text = taxonomy v3 definitions verbatim (label → its definition sentence)"
  - **Affected scope:** Request builder.
  - **Concrete fix:** Jev's literal-reading behavior requires the full bullet point from `taxonomy.md`, including boundary sentences (e.g., "A comparison plan is this, not planning just because it says plan"), not just the first definition sentence. Update the plan to include the full text for each label.
- **[Should] 8. Surface (Validation mode & Missing Hashes)**
  - **Observed input:** Plan includes `--validation` mode; mentions `input-hashes.json` in the #547 dir.
  - **Affected scope:** Smallest affected surface.
  - **Concrete fix:** `--validation` mode is machinery beyond the envelope for a one-shot holdout run; remove it. `input-hashes.json` is in XYZ-forge, so hardcode the expected hashes in the script instead.
- **[Pass] 2. Area question design**
  - Keep the 12-class set (no `none` option) and score on the 38 non-null rows. This ensures Jev faces the exact same forced-choice denominator as the #547 baselines for an apples-to-apples comparison.
- **[Pass] 6. Provenance**
  - Add the sha256 of `taxonomy.md` and `holdout-labels.json` to the provenance in `results.json` to prove which criteria and truths were used.
- **[Pass] 7. Acceptance checks**
  - The fixture correctly covers the null area row. With `sklearn` removed, ensure the unit test asserts behavior when a label has 0 support/predictions (zero division). The hash-mismatch red control is sufficient.
- **[Pass] 9. Rating**
  - 60/30/50/85 is grounded. Effort 85 (cheap) aligns with `effort: 1` and no new dependencies; Appeal 50 is neutral; Severity 30 is appropriate for research; Priority 60 matches operator request #709.

**Verdict:** Changes requested.

handing off to Producer — go to the claude-a window and say 'take your turn'

### Producer — r1 dispositions (claude-a, 2026-09-18)

Plan revised in `PROJECT/2-WORKING/GH-67-JEV-PURPOSE-ZERO-SHOT.md` (same commit).

- [Blocker] 4 sklearn — **Implemented.** Metrics are plain Python (`correct`, `raw_accuracy`, `macro_f1` over the class∪truth universe, zero-division → 0, confusion), as `shortlist_eval.py` does; sklearn removed from Requirements, Dependencies and the test (§Requirements 2, §Dependencies).
- [Blocker] 5 `holdout.json` hash — **Implemented.** Pinned sha256 `24995fe2…edf26` (the operator's verified 2026-09-18 snapshot) beside the two #547 manifest hashes; all three are constants in the script and the freeze check aborts before any request on mismatch (§Recon, §Requirements 3).
- [Should] 1 fairness — **Implemented.** Validation mode removed entirely; `holdout-labels.json` is hashed as bytes before the run and parsed only after the last response (§Requirements 5).
- [Should] 3 criteria fidelity — **Implemented.** Criteria carry the full taxonomy bullet per label including boundary sentences; the three labels the taxonomy leaves undefined (`ci_cd`, `skills`, `ui`) get one-line glosses recorded in provenance (§Requirements 1).
- [Should] 8 surface — **Implemented.** `--validation` removed; hashes hardcoded (§Smallest affected surface).
- [Pass] 2 area design — **Acknowledged**, kept the 12-class forced choice on 38 rows (§Requirements 1). [Pass] 6 provenance — hashes already in `results.json`. [Pass] 7 — test now includes a zero-support/zero-prediction class case (§Smallest affected surface). [Pass] 9 rating — unchanged.

Round 2 asks: confirm each disposition against the revised plan; anything still blocking?

handing off to Reviewer (agy) — take your turn on this file.

### Reviewer (agy) — Round 2

swept file: yes

- **[Pass] 4. Metric parity (sklearn vs manual)**
  - Verified: "computed in plain Python as `spike/coding_core/shortlist_eval.py` does; **no sklearn**" (Requirements 2).
- **[Pass] 5. Data policy (Leak path)**
  - Verified: "sha256 `24995fe28edf56d3c77be41d9e0baec958006f987889efc51369fa77e5eedf26`" (Recon).
- **[Pass] 1. Fairness (Validation mode & labels)**
  - Verified: "`holdout-labels.json` is hashed as bytes before the run and parsed only after the last response is in" (Requirements 5) and "There is no validation mode" (Requirements 5).
- **[Pass] 3. Criteria fidelity (Boundary sentences)**
  - Verified: "criteria text = the **full** taxonomy v3 bullet for each label including its boundary sentences" (Requirements 1).
- **[Pass] 8. Surface (Validation mode & Missing Hashes)**
  - Verified: "freeze check against three hardcoded hashes" (Smallest affected surface).
- **[Should] Acceptance check inconsistency (Hardcoded hashes)**
  - **Observed input:** Plan states hashes are hardcoded (Smallest affected surface) but the red control says "run with `--hashes` pointing at a tampered manifest" (Acceptance checks).
  - **Affected scope:** Acceptance checks.
  - **Falsifier:** There is no `--hashes` flag in the script's surface since the hashes are now hardcoded constants.
  - **Concrete fix:** Update the red control in Acceptance checks to "mutate a hardcoded hash in the script" instead of using a `--hashes` flag.

**Verdict:** Changes requested.

handing off to Producer — go to the claude-a window and say 'take your turn'

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
