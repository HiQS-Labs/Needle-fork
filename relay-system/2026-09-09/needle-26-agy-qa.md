# RELAY · Needle PR 26 Agy QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-09.
-->

NEXT: Producer
STATUS: Approved
ROUND: 1 / 1

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
6. **Commit only the relay file** (`relay(needle-26-agy-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md
- Review scope: the complete `origin/main...HEAD` diff for `HiQS-Labs/Needle-fork` PR #26 and every
  full file changed by that diff. Read the issue #25 plan, recon, aggregate receipt, implementation,
  tests, and prior relay records. This is a read-only QA turn; do not edit source files.
- Reviewer: agy   ·   Producer: codex-producer
- Started: 2026-09-09
- Definition of Done: Answer each question with concrete `file:line` evidence and flag any defect,
  unsupported claim, privacy leak, weak test, or unnecessary scope.

  1. Do stable session/event identities remain invariant across mount paths while distinguishing
     copied transcripts, native duplicate records, and ID-less subagent events?
  2. Does manifest construction fail closed unless it can reconstruct and match the exact source
     request, prior actions, tool, label, transcript hash, and canonical correction membership?
  3. Are fitting, prior-audit, and model-selection boundaries mandatory and are session, event, q1,
     and content overlaps checked without inventing unavailable legacy identifiers?
  4. Do opt-in namespaced paths preserve the legacy extract/sample/score behavior when omitted?
  5. Are the public receipt and plan claims supported by code and aggregate evidence, free of raw
     prompts, credentials, and operator-specific paths, and honest about the 17-session shortfall?
  6. Do tests exercise failure paths rather than mirror implementation, and does the relevant test
     suite pass from a clean checkout? Run focused tests if feasible and report the exact command.
  7. Sweep every changed implementation, test, plan, receipt, and relay file in full, plus the PR
     diff as a whole. State whether PR #26 is safe to merge.

  End with exactly `**Verdict:** Approved`, `**Verdict:** Changes requested`, or
  `**Verdict:** Blocked`.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

### Reviewer · agy · round 1

swept file: yes

- [Pass] Stable session/event identities remain invariant across mount paths while distinguishing copied transcripts, native duplicates, and ID-less subagents (`utils/corpus/transcript_events.py:54-64`, `utils/corpus/transcript_events.py:94-98`, `utils/corpus/transcript_events.py:130-145`, `utils/corpus/extract_claude_transcripts.py:172-175`). Relative path normalization strips foreign mount points so identical sessions share identity across prefixes (`tests/test_corpus_identity.py:116-136`). Copied transcripts within a namespace collide on native event IDs and fail closed (`tests/test_corpus_identity.py:138-160`), while ID-less subagent events scope to the distinct subagent path session (`tests/test_corpus_identity.py:161-179`).
- [Pass] Manifest construction fails closed on source mismatch, drift, or missing canonical correction membership (`utils/corpus/build_experiment_manifest.py:142-172`, `utils/corpus/build_experiment_manifest.py:182-239`, `utils/corpus/build_experiment_manifest.py:368-432`). It requires both `--correction-membership-pairs` and `--correction-legacy-source-prefix`, verifies legacy path hashing against training split membership, rebuilds the exact request and prior actions from raw source, and rejects drifted q1 context or post-extraction transcript edits (`tests/test_corpus_identity.py:270-279`, `tests/test_corpus_identity.py:316-322`, `tests/test_corpus_identity.py:342-362`, `tests/test_corpus_identity.py:364-378`).
- [Pass] Fitting, prior-audit, and model-selection boundaries are mandatory and evaluated without inventing unavailable legacy identifiers (`utils/corpus/build_experiment_manifest.py:28`, `utils/corpus/build_experiment_manifest.py:452-470`, `utils/corpus/build_experiment_manifest.py:309-325`, `utils/corpus/build_experiment_manifest.py:322-365`). Omitted boundary categories fail closed (`tests/test_corpus_identity.py:323-340`). Legacy exclusions explicitly record `source_identity: "unavailable in frozen legacy pairs"`, reporting `session: null` and `source_event_id: null` in separation rather than inventing synthetic identifiers (`TESTS-RESULTS/2026-09-09-issue-25-source-gate/receipt.json:62,148-154`, `tests/test_corpus_identity.py:219-223`).
- [Pass] Opt-in namespaced paths preserve legacy extract, sample, and score behavior when `--source-namespace` is omitted (`utils/corpus/extract_claude_transcripts.py:151-155,183-191`, `utils/corpus/sample_for_audit.py:88-105,157-162`, `utils/corpus/score_audit.py:99-106,301-306`, `utils/corpus/measure_taxonomy.py:26-44,147`). Legacy pair generation, audit format 2, `--allow-legacy-plan`, and `iter_calls` run unchanged when namespacing is not requested, and legacy test suites continue to pass (`tests/test_audit.py:139-150`).
- [Pass] Public receipt and plan claims are backed by code and aggregate data, free of secrets and local paths, and honest about the 17-session shortfall (`TESTS-RESULTS/2026-09-09-issue-25-source-gate/receipt.json:287-300`, `TESTS-RESULTS/2026-09-09-issue-25-source-gate/SUMMARY.md:5-7,67-70`, `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:256-259`). Programmatic gate `_assert_public_safe` bans credential patterns and operator home paths (`utils/corpus/build_experiment_manifest.py:29-33,485-491`). The shortfall below the 30-session floor is clearly marked `INCOMPLETE`, and training was correctly not started.
- [Pass] Focused test suite exercises failure paths rather than mirroring implementation and passes cleanly from checkout (`PYTHONDONTWRITEBYTECODE=1 pytest -o cache_dir=/tmp/pytest_cache -p no:cacheprovider tests/test_corpus_identity.py tests/test_audit.py` -> 42 passed in 1.69s). Red controls cover duplicate session rejection (`tests/test_corpus_identity.py:146-149`), context drift (`line 278`), exclusion overlap (`lines 284, 291`), empty input (`line 301`), overwrite refusal (`line 312`), hash drift (`line 319`), missing boundaries (`line 338`), missing membership flags (`line 360`), tampered context (`line 376`), and contract version drift (`line 391`).
- [Pass] Complete sweep of all 20 changed files across `origin/main...HEAD` (`PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md`, `ROADMAP.md`, `TESTS-RESULTS/2026-09-09-issue-25-source-gate/SUMMARY.md`, `TESTS-RESULTS/2026-09-09-issue-25-source-gate/receipt.json`, `doc/recon-25-feedback-experiment.md`, relay files, `tests/test_audit.py`, `tests/test_corpus_identity.py`, and `utils/corpus/*.py`) identified no pre-existing defects, privacy leaks, or scope creep. PR #26 is safe to merge.

**VERDICT:** PASS
**Basis:** All 7 Definition of Done requirements verified with concrete file:line citations; failure paths and red controls confirmed; privacy and honest 17-session shortfall verified; full sweep of PR #26 clean.  [Unverified — no citation]
**Verdict:** Approved

relay closed (Approved), no further turn needed.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
