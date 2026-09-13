# RELAY · Needle 63 Codex app feedback plan QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-13.
-->

NEXT: Producer
STATUS: Approved
ROUND: 1 / 2

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
6. **Commit only the relay file** (`relay(needle-63-codex-app-feedback-plan-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: **.relay-artifacts/CODEX-NEEDLE-FEEDBACK.md** — the read-only path that
  `relay-drive.sh --artifact-file PROJECT/2-WORKING/CODEX-NEEDLE-FEEDBACK.md` seeds into the isolated worktree (read it there; do NOT edit it).
- Reviewer: agy   ·   Producer: codex-producer
- Started: 2026-09-13
- Definition of Done: Review the entire proposed plan, not implementation. Are the confirmed requirements (this Codex app, automatic display every completed turn, separate want/did feedback) preserved? Check app hook feasibility without continuation loops, hidden private storage versus the inspected XYZ collector, session/choice identity, context leakage and lean scope. The first phase explicitly blocks implementation until app rendering is proved: do not mistake that planned proof for a claimed result. Read PROJECT/2-WORKING/RECON-CODEX-FEEDBACK.md as supporting evidence. Cite concrete issues, distinguish blockers from optional future work. Do not install hooks, run experiments, publish private data or edit other files.  [Unverified — no citation]

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

### agy (Reviewer) - Approved

swept file: yes

- `[Pass]` Confirmed requirements (Codex app, automatic display, separate want/did): Preserved per lines 33-34 ("this Codex app/chat, automatically after every completed turn", "separate intended and completed feedback").
- `[Pass]` App hook feasibility without continuation loops: Addressed in lines 76-77 ("Prefer JSON systemMessage ... without decision:block") and lines 89-90 ("no extra model continuation, repeated hook loop").
- `[Pass]` Hidden private storage vs XYZ collector: Addressed in lines 110-111 ("Store append-only events in `relay-system/.needle-feedback.jsonl`, with a hidden lock beside it") and lines 129-130 ("Test actual XYZ collector with synthetic private markers → none copied").
- `[Pass]` Session/choice identity: Covered by line 83 ("stable session/turn identity") and lines 115-117 ("Each suggestion records session/turn/suggestion ID ... Each feedback event records its own ID, referenced suggestion").
- `[Pass]` Context leakage and lean scope: Bounded correctly in lines 105-106 ("Bound hook runtime to two seconds and context to the latest 32 KiB").
- `[Pass]` Blocking implementation until app rendering is proved: Respected in line 95 ("Only after Phase 1 passes, add one small stdlib dispatcher").
- `[Pass]` No planned proof mistaken for claimed result: Status explicitly says "Review plan, then separately authorize the app connection proof. No hooks installed." (line 16).

Verdict: Approved

relay closed (Approved), no further turn needed.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
