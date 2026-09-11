# RELAY · GH-41 final implementation proof
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-11.
-->

NEXT: Reviewer
STATUS: Open
ROUND: 1 / 2

## ▶ TAKE YOUR TURN — read this first (works for ANY agent: Claude, Codex, agy)
1. **Read this whole file** (header, Setup, Ground rules, every block in the Log).
2. **Check it's your turn:** `NEXT` (top) names the role to act. Confirm you are bound to it and the
   last Log block isn't already yours. If not → STOP and reply "wrong window — nudge the <other> window."
3. **Do your role's work** on the artifact named in Setup:
   - **Reviewer:** review vs the Definition of Done → graded findings
     (`[Blocker]`/`[Should]`/`[Nit]`/`[Pass]`), each with a concrete fix → end with the exact uppercase
     marker `VERDICT: Approved`, `VERDICT: Changes requested`, or `VERDICT: Blocked`. **Review the whole file, not just the diff** (GH-268):
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
6. **Commit only the relay file** (`relay(gh41-final-proof): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: **.relay-artifacts/build_grounded_augmentation.py** — the read-only path that
  `relay-drive.sh --artifact-file /Users/noelsaw/Documents/GH Repos/Needle-fork-gh41-augmentation/utils/corpus/build_grounded_augmentation.py` seeds into the isolated worktree (read it there; do NOT edit it).
- Reviewer: codex   ·   Producer: claude-a
- Started: 2026-09-11
- Definition of Done: final branch implementation through commit `dcf7e94` satisfies issue #41's
  initial implementation and the approved plan. Read the complete artifact, plus
  `tests/test_grounded_augmentation.py`, `tests/fixtures/gh41/`,
  `PROJECT/2-WORKING/GH-41-TARGETED-AUGMENTATION.md`, and the prior findings in
  `relay-system/2026-09-11/gh41-final-qa.md`. The local evidence is 16 focused tests and 400
  non-slow tests passing in a Python 3.12 environment installed with `.[test,train]`.

Answer each question with file-and-line evidence:

1. Do malformed seed, candidate, hash, pair, serializer, and forbidden-manifest inputs fail through
   the controlled contract/CLI path before any final run becomes visible?
2. Are seed provenance, label/action grounding, canonical serialization, deterministic ordering,
   duplicate rejection, and complete one-change counterfactual pairs enforced rather than asserted?
3. Are generated-only metadata and the privacy-safe manifest/report honest about their
   composition-time boundary, without claiming later trainer/evaluation enforcement?
4. Does the atomic publication path avoid a partially visible final run on validation or injected
   failure, and are its cleanup targets bounded?
5. Did the branch avoid every issue #25-owned path and unnecessary runtime/dependency changes?
6. Do the focused tests include meaningful red controls for the repaired review findings, and is any
   remaining gap a blocker to this initial offline-composer milestone?

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
