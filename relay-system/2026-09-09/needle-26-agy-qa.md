# RELAY · Needle PR 26 Agy QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-09.
-->

NEXT: Reviewer
STATUS: Open
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
- Artifact under review: the complete `origin/main...HEAD` diff for
  `HiQS-Labs/Needle-fork` PR #26 and every full file changed by that diff. Read the issue #25 plan,
  recon, aggregate receipt, implementation, tests, and prior relay records. This is a read-only QA
  turn; do not edit source files.
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

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
