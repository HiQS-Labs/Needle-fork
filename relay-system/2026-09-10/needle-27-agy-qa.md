# RELAY · Needle PR 27 audit evidence QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-10.
-->

NEXT: Reviewer
STATUS: Open
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

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
