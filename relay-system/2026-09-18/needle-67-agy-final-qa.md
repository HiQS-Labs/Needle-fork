# RELAY · Needle 67 Jev zero-shot final QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-18.
-->

NEXT: Reviewer
STATUS: Open
ROUND: 1 / 3

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
6. **Commit only the relay file** (`relay(needle-67-agy-final-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: **SUMMARY.md** (embedded below — read it here).
- Reviewer: agy   ·   Producer: claude-a
- Started: 2026-09-18

### Artifact — SUMMARY.md
```
# GH-67 — Jev zero-shot on the #31 purpose/area holdout

Run: 2026-09-18T23:34:47Z · Model: `jev-1.13.0` on all 40 responses · Input tokens: 55,579 (~$0.0023) · Script: `spike/work_classification/jev_zero_shot.py`, frozen at commit `453cae1` before the first request (`questions_sha256 21094cd4…`, `script_sha256 07405826…`) · Wall time 14 s · Records sent: 40/40 (all repos `PUBLIC` at run time, none skipped).

## Result

| Axis | Majority | TF-IDF + logistic (#547) | Frozen ModernBERT + logistic (#547) | **Jev zero-shot** |
|---|---:|---:|---:|---:|
| Purpose correct /40 | 17 | 20 (50.0%) | 23 (57.5%) | **37 (92.5%)** |
| Purpose macro-F1 | — | 0.430 | 0.370 | **0.675** |
| Area correct /38 labeled | 4 | 12 (31.6%) | 10 (26.3%) | **32 (84.2%)** |
| Area macro-F1 | — | 0.206 | 0.221 | **0.696** |

Same 40 records, same `Project / Title / Description` text, same metric definitions (`correct`, `raw_accuracy`, `macro_f1` over the union of taxonomy classes and truth labels with zero-division → 0; area scored on the 38 non-null truth rows). Baselines are copied from `TESTS-RESULTS/2026-09-10+GH-547-calibrated/results.json` in XYZ-forge at `430f432`.

## Confidence

| Axis | conf < 0.5 | 0.5 ≤ conf < 0.8 | conf ≥ 0.8 |
|---|---|---|---|
| Purpose | 2/3 correct | 5/7 | **30/30** |
| Area | 4/7 | 8/11 | **20/20** |

Every prediction at confidence ≥ 0.8 was correct on both axes; every miss sits below 0.8 (purpose misses at 0.46 / 0.53 / 0.59; area misses at 0.41–0.71). A confidence gate at 0.8 would answer 30/40 purpose and 20/38 area rows with zero errors and route the rest to the #29 contract's `uncertain` output. This is an observation on 40 rows, not a tuned threshold.

## Misses

Purpose (3): `holdout-002` truth `merge_closeout` → `feature_enhancement` (0.46); `holdout-008` `bug_fix` → `research_evaluation` (0.53); `holdout-013` `testing_validation` → `research_evaluation` (0.59). The one `merge_closeout` example in the holdout was missed, so that class scores 0 in macro-F1; `maintenance` has no holdout support and scores 0 by the zero-division rule, which is what holds macro-F1 at 0.675 despite 92.5% accuracy (same rule as #547).

Area (6): four of the ten `model_inference` rows went to `core_harness` ×2, `telemetry`, `ingestion_sync`; `holdout-011` `search_retrieval` → `ledger`; `holdout-037` `skills` → `core_harness`. `core_harness` is over-predicted (7 predicted, 4 true). The two null-truth area rows received `core_harness` and `telemetry` (forced choice, not scored — same denominator as #547).

## Caveats (carried from #31 and the plan)

- The holdout labels are **model-annotated** under the operator's calibration (a third model reviewer, blinded to training labels), not human gold. A zero-shot model agreeing with model annotators at 92.5% may partly reflect shared priors; the #547 classifiers were trained on labels from the same annotation protocol and still scored 50–57.5%, so the gap is not explained by that alone.
- n = 40. Purpose classes `maintenance` (0) and `merge_closeout` (1) are effectively untested; area classes `dependencies` and `integrations` have no support.
- This holdout was already observed by the #31 round. Nothing was tuned against it here (criteria committed before the first request, one run, labels parsed after the last response), but it is not "unseen evidence" for any follow-up model and must not be reused as such.
- Three area labels (`ci_cd`, `skills`, `ui`) have no definition in taxonomy v3; their one-line glosses are the script's (`area_glosses_by_script` in `results.json`). All three were classified correctly, but a taxonomy revision should own that wording.
- Zero-shot means no in-domain data was used; this does not establish that Jev generalises to other HiQS repos, private titles, or a fresh sample.

## What this does and does not change

- It answers the question in #67: on the frozen #31 holdout, Jev zero-shot clears the ModernBERT/TF-IDF bar by a wide margin on both axes, with confidence that separates its own errors.
- It does not promote anything. Per the plan, a better score is a signal to run a **fresh unseen sample** with human adjudication before any deployment decision; that is a new issue with its own gate. #62 and #59 are untouched.

Files: `results.json` (aggregates, confusion matrices, per-record predictions by `id`, provenance hashes), `requests.jsonl` (request/response sha256 per record). No titles or descriptions are stored.
```
- Definition of Done: _<fill in the acceptance criteria the Reviewer grades against>_

## Definition of Done and review questions (Reviewer: answer every numbered item)

**Goal.** Final QA of the GH-67 implementation against its approved plan (`PROJECT/2-WORKING/GH-67-JEV-PURPOSE-ZERO-SHOT.md`, approved r3 in `relay-system/2026-09-18/needle-67-codex-plan-qa.md`). The receipt is embedded above.

**Operational envelope.** One offline research script + one pytest file + one results directory; nothing touches the `needle` runtime. Grade against the plan's requirements and commensurate complexity.

**Read in the worktree (read-only):** the plan; `spike/work_classification/jev_zero_shot.py`; `spike/work_classification/README.md`; `tests/test_jev_zero_shot.py`; `TESTS-RESULTS/2026-09-18-jev-purpose-zero-shot/results.json` and `requests.jsonl`; `CHANGELOG.md` top entry; `ROADMAP.md` in-progress pointer. Git history: `453cae1` (freeze commit) precedes `1aa4132` (results commit).

**Questions.**

1. Protocol adherence: were the criteria frozen by commit before the first request (the freeze commit precedes the results commit; `results.json.questions_sha256` and `script_sha256` correspond to the frozen file)? Is there any code path that reads `holdout-labels.json` before all responses are in (cite line numbers)?
2. Requirements 1–5 of the plan: for each, cite the line(s) in `jev_zero_shot.py` that satisfy it or name what is missing (text template, full taxonomy bullets, 12-class forced-choice area, three pinned hashes, visibility gate, plain-Python metrics, confidence buckets, provenance fields).
3. Metric parity: does `metrics()` reproduce #547's definitions (known-truth rows only; universe = classes ∪ truth; macro-F1 with zero-division → 0)? Check the arithmetic in the receipt: purpose 37/40 with `merge_closeout` (support 1, missed) and `maintenance` (support 0) both scoring 0 → is macro-F1 0.675 consistent?
4. Publication safety: do `results.json` / `requests.jsonl` contain any title, description, or key material? Cite what fields they do contain.
5. Test adequacy: does `tests/test_jev_zero_shot.py` detect a miscounting scorer, empty input, the zero-support class, and the freeze-mismatch path? Anything that lets a broken scorer pass?
6. Receipt honesty: does `SUMMARY.md` state the caveats the plan required (model-annotated labels, n = 40, observed holdout, script-authored glosses for three area labels, no promotion)? Any claim in it that the files do not support?
7. Surface: any file changed outside the plan's "smallest affected surface"? Any machinery beyond the envelope?
8. Rating and status: does the plan's rating (`60/30/50/85`) still match the evidence, and is the plan's status table truthful?

Output: graded findings (`[Blocker]`/`[Should]`/`[Nit]`/`[Pass]`) with `file:line` or quoted-span citations; behaviour-change requests carry `Observed input:` / `Affected scope:` / `Falsifier:`. Then a Verdict. `swept file: yes|no` line required.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
