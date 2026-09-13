# RELAY · Needle 63 native app connection probe QA
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
6. **Commit only the relay file** (`relay(needle-63-native-app-connection-probe-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: **.relay-artifacts/codex_connection_probe.py** — the read-only path that
  `relay-drive.sh --artifact-file utils/hooks/codex_connection_probe.py` seeds into the isolated worktree (read it there; do NOT edit it).
- Reviewer: agy   ·   Producer: codex-producer
- Started: 2026-09-13
- Definition of Done: Review utils/hooks/codex_connection_probe.py and tests/test_codex_connection_probe.py against #63 Phase 1 only. (1) Does it emit only synthetic warning messages, with no continuation/block decision? (2) Does it avoid reading transcripts, saving prompts or echoing arbitrary text? (3) Are malformed/oversized input and subagents handled safely? (4) Do tests avoid claiming real app display? This is a prerequisite probe, NOT the finished skill or predictor. Do not install or change config. Append a review block with literal uppercase `VERDICT: APPROVED` or `VERDICT: CHANGES_REQUESTED`, plus `swept file: yes`, cited findings and explicit handoff. Prior mixed-case Verdict failed structural validation; use the required uppercase field.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

**Reviewer (agy)**
* swept file: yes
* [Pass] DoD (1): Emits only synthetic warning messages, no block decision (`utils/hooks/codex_connection_probe.py:18` and `20` return only `systemMessage`).
* [Pass] DoD (2): Avoids reading transcripts/echoing user text. Only exact `PROMPT` is handled (`utils/hooks/codex_connection_probe.py:19`), input reading is bounded to stdin without accessing file system (`utils/hooks/codex_connection_probe.py:27`).
* [Pass] DoD (3): Malformed/oversized inputs are truncated/caught cleanly (`utils/hooks/codex_connection_probe.py:27-31`). Subagents are safely bypassed (`utils/hooks/codex_connection_probe.py:14`).
* [Pass] DoD (4): Tests rigorously exercise these bounds without claiming any actual display (`tests/test_codex_connection_probe.py:14-33`).
* No pre-existing defects found.

VERDICT: APPROVED

relay closed (Approved), no further turn needed.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
