# RELAY · Needle PR 27 audit evidence QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-10.
-->

NEXT: Producer
STATUS: Approved
ROUND: 1 / 4

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
6. **Commit only the relay file** (`relay(needle-27-agy-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Goal: QA PR #27 at code commit `6272d40` against `origin/main`. Review the complete changed files, not only patch fragments.
- Files: `utils/corpus/sample_for_audit.py`, `utils/corpus/score_audit.py`, `utils/corpus/analyze_audit_causes.py`, `tests/test_audit.py`, `tests/test_corpus_identity.py`, `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md`, `ROADMAP.md`, and `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/`.
- Reviewer: agy   ·   Producer: codex
- Started: 2026-09-10
- Definition of Done: no open Blocker or Should finding; targeted audit results make no population or inferential-interval claim; the exact allocator satisfies label quotas and declared session constraints or fails closed; scoring and cause analysis validate one complete source/session contract; aggregate receipts agree and expose no raw prompts, commands, paths, row IDs, or credentials; tests include meaningful red controls.

## Questions for the Reviewer

1. Does any code or public artifact still make an invalid population, confidence-interval, or causal-gain claim for the session-constrained targeted sample?
2. Is the min-cost-flow draw exact and deterministic, and can it falsely reject a feasible label-quota/session-cap allocation?
3. Can a malformed v3 identity, unsafe source path, missing session field, quota mismatch, or violated session limit reach a report instead of failing closed?
4. Do the public aggregate files and plan document agree on 400 rows, 254 sessions, 321 agreements, 72 adjudications, 79 errors, and 19 correction rows without leaking row-level material?
5. Do the tests actually turn red for the defects they claim to prevent, and is any changed file stale, contradictory, or overbuilt?

Cite `file:line` for every finding. End with `Approved` only if all five questions pass; otherwise request concrete changes.

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

- [Pass] Question 1 (inferential claims): No code or public artifact makes an invalid population, confidence-interval, or causal-gain claim for the session-constrained targeted sample. In `utils/corpus/score_audit.py:441-446`, `utils/corpus/score_audit.py:454-459`, `utils/corpus/score_audit.py:471-473`, `utils/corpus/score_audit.py:502`, and `utils/corpus/score_audit.py:513-524`, population-weighted estimates and Wilson confidence intervals are explicitly set to `None` for `TARGETED_DESIGN`, with `population_statistics` explicitly stating "not estimated: the session-constrained targeted draw has unequal inclusion probabilities". In `utils/corpus/analyze_audit_causes.py:131-133`, `utils/corpus/analyze_audit_causes.py:161-164`, `utils/corpus/analyze_audit_causes.py:186-191`, `utils/corpus/analyze_audit_causes.py:195-197`, and `utils/corpus/analyze_audit_causes.py:212-214`, population estimates are `None`, contribution keys report sample counts only (`sample_error_contribution`, `share_of_sample_errors`), and limitations note that the targeted draw is not a population estimate or expected training gain. Public artifacts adhere to this: `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:91-93`, `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:284-285`, `ROADMAP.md:17`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/SUMMARY.md:9`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/receipt.json:5-11`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-adjudicated.json:6`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-adjudicated.json:23`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-cause-metrics.json:8`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-cause-metrics.json:13`, and `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-raw-metrics.json:6`.
- [Pass] Question 2 (exact flow allocator): The min-cost-flow draw is exact, deterministic, and proven not to falsely reject any feasible label-quota/session-cap allocation (`utils/corpus/sample_for_audit.py:99-140`, `utils/corpus/sample_for_audit.py:143-208`). Node construction deterministically orders labels and sessions via seed-based SHA-256 (`utils/corpus/sample_for_audit.py:155-158`, `utils/corpus/sample_for_audit.py:177-179`), and candidates within each (label, session) cell are ranked by content-derived hash (`utils/corpus/sample_for_audit.py:84-88`, `utils/corpus/sample_for_audit.py:203-204`). The flow network structure guarantees exactness: capacity from label nodes enforces exact quotas (`utils/corpus/sample_for_audit.py:172`), per-session edges enforce the session cap `cap` (`utils/corpus/sample_for_audit.py:183-186`), and cost -1 on the first unit of session flow maximizes distinct session count. Because min-cost flow finds a flow of value `target` minimizing total cost, it achieves the mathematical maximum number of unique sessions possible; if `used_sessions = -flow_cost < min_sessions`, no feasible allocation of size `target` can achieve `min_sessions` sessions (`utils/corpus/sample_for_audit.py:188-196`). Terra's feasible counterexample where greedy allocation failed is verified passing (`tests/test_audit.py:441-453`).
- [Pass] Question 3 (fail-closed contract): Malformed v3 identity, unsafe source path, missing session field, quota mismatch, or violated session limit fail closed before any report is written. In `utils/corpus/score_audit.py:106-126`, duplicate `source_event_id`, unknown `source_namespace`, invalid `source_relpath` (empty, absolute, or traversing via `..`), non-64-hex SHA-256 strings for `session`, `transcript_sha256`, and `source_event_id`, or negative ordinal raise `AuditError`. Sorter count and strata mismatches raise `AuditError` (`utils/corpus/score_audit.py:127-131`). Violated session constraints raise `AuditError` (`utils/corpus/score_audit.py:136-146`). Path containment checks in sampler prevent escaping `data/` (`utils/corpus/sample_for_audit.py:335-340`, `utils/corpus/sample_for_audit.py:399-406`), and scorer input/output aliasing checks prevent overwriting inputs (`utils/corpus/score_audit.py:431-434`). All failure paths exit before writing outputs, covered by focused red controls (`tests/test_audit.py:151-218`, `tests/test_audit.py:304-321`, `tests/test_audit.py:367-379`).
- [Pass] Question 4 (aggregate receipt agreement and privacy): The public aggregate files and project documentation agree on 400 rows, 254 sessions, 321 agreements, 72 adjudications, 79 errors, and 19 correction rows:
  - 400 rows: `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:32`, `ROADMAP.md:17`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/SUMMARY.md:7`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/receipt.json:33`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-adjudicated.json:9`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-raw-metrics.json:10,214,419`.
  - 254 sessions: `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:277`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/SUMMARY.md:7`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/receipt.json:34`.
  - 321 agreements: `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:284`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/SUMMARY.md:9`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/receipt.json:38`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-adjudicated.json:10`.
  - 72 adjudications (328 unadjudicated agreements): `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:32,283`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/SUMMARY.md:8`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/receipt.json:41`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-adjudicated.json:453-454`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-raw-metrics.json:420`.
  - 79 errors: `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:286`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/SUMMARY.md:10`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-cause-metrics.json:11`.
  - 19 correction rows: `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:32,288`, `ROADMAP.md:17`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/SUMMARY.md:11`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/receipt.json:43`, `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/correction-cause-metrics.json:116`.
  Privacy verification confirmed zero raw row IDs, prompt texts, commands, operator paths, or credentials in public JSON files (`TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/receipt.json:107-124`).
- [Pass] Question 5 (red controls and lean scope): Focused tests provide meaningful red controls for defective inputs: testing infeasible session caps and floors (`tests/test_audit.py:435-438`), Terra's counterexample (`tests/test_audit.py:441-453`), suppression of population estimates/CIs under targeted design (`tests/test_audit.py:131-149`), invalid source relative paths (`tests/test_audit.py:151-161`), plan session contract tampering (`tests/test_audit.py:163-180`), malformed auditor submissions (`tests/test_audit.py:182-218`), duplicate source event IDs (`tests/test_audit.py:263-270`, `tests/test_audit.py:603-633`), unrenderable event accounting (`tests/test_corpus_identity.py:280-337`), and cause validation defects (`tests/test_audit.py:635-665`). All 61 focused audit and identity tests pass (`pytest tests/test_audit.py tests/test_corpus_identity.py`). Changed files are consistent, lean, and free of scope creep or dead code.
- [Pass] Whole-file sweep: swept `utils/corpus/sample_for_audit.py`, `utils/corpus/score_audit.py`, `utils/corpus/analyze_audit_causes.py`, `tests/test_audit.py`, `tests/test_corpus_identity.py`, `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md`, `ROADMAP.md`, and `TESTS-RESULTS/2026-09-10-issue-25-audit-freeze/` in full. Found no pre-existing defects or regressions.

VERDICT: PASS
Basis: All five questions verified with file:line citations; exact min-cost flow allocation verified; fail-closed contract verified; aggregate metrics verified; 61 focused tests pass.  [Unverified — no citation]
**Verdict:** Approved

relay closed (Approved), no further turn needed.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
