# RELAY · Needle 25 deterministic feedback plan QA round 2
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-09.
-->

NEXT: Producer
STATUS: Escalated
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
6. **Commit only the relay file** (`relay(needle-25-plan-qa-r2): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifacts under review: `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md`,
  `doc/recon-25-feedback-experiment.md`, and the matching `ROADMAP.md` row. The plan corrections are
  commit `ef36a2d`; round-one findings are preserved in `needle-25-plan-qa.md`.
- Reviewer: codex   ·   Producer: codex-producer
- Started: 2026-09-09
- Definition of Done: Review the whole artifacts and cited implementation. Confirm or reject that
  round one's three findings are resolved; the numeric primary and subset rules are coherent and
  falsifiable; the 1,000-row/30-session design supports its stated five-point claim; privacy remains
  aggregate-only; the matched arms isolate target correction; and the first PR scope is the smallest
  safe prerequisite. Use a literal `VERDICT: Approved`, `VERDICT: Changes requested`, or
  `VERDICT: Blocked` line so the relay validator can parse the result. Review only; do not edit
  project files.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

### Reviewer · codex · round 1

VERDICT: Changes requested

swept file: yes

- [Blocker] `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:202-209` — the primary promotion p-value remains an exact McNemar test, which treats the 1,000 paired rows as independent, yet the same rule deliberately samples repeated rows within 30 sessions and says clustering matters. A session-bootstrap interval does not repair the invalid primary p-value or its 623-pair power claim. **Fix:** make a predeclared session-clustered paired test/interval the primary inferential rule (with its alpha, direction, and aggregation weight), and base eligibility/power on the frozen session-size distribution; otherwise return `INCOMPLETE`.
- [Blocker] `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:211-215,237-239` — a 50-row subset passes whenever its *observed* change is at least -5 pp, even if its uncertainty is compatible with a much larger regression. That cannot support the stated protected-subset claim. **Fix:** require, for each subset, a prespecified session-clustered one-sided non-inferiority lower bound strictly above -5 pp, with sufficient eligible sessions/rows to estimate it; below that sufficiency threshold return `INCOMPLETE`.
- [Pass] Round one's numeric, privacy, and stale-target findings are resolved: the plan now names the primary effect, null, alpha, +5 pp threshold, and `INCOMPLETE` outcome (`PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:202-209`); keeps raw prompts, rows, labels, and paths private while limiting public receipts to aggregates (`:256-261`); and calls the old target a frozen sorter target rather than a hard negative (`:134-138,222-225`).
- [Pass] The first-PR boundary remains minimal and grounded: it is confined to corpus/audit utilities, tests, the plan/Roadmap, and an aggregate receipt (`PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:242-244`), with the existing extractor, serializer, loader, MLX, and paired-analysis seams traced in `doc/recon-25-feedback-experiment.md:17-24`.

Whole-file sweep: yes — no additional pre-existing defects surfaced in `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md`, `doc/recon-25-feedback-experiment.md`, or the matching `ROADMAP.md` row beyond the two decision-rule blockers above.

The only allowed round is exhausted without approval, so the relay is escalated. Handing off to codex-producer — go to the Producer window and say “take your turn”; resolve the two blockers under the escalated relay decision.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
