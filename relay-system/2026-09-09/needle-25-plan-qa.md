# RELAY · Needle 25 deterministic feedback plan QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-09.
-->

NEXT: Producer
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
6. **Commit only the relay file** (`relay(needle-25-plan-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifacts under review: `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md`,
  `doc/recon-25-feedback-experiment.md`, and the matching `ROADMAP.md` row at commit `66a2df9`.
- Reviewer: codex   ·   Producer: codex-producer
- Started: 2026-09-09
- Definition of Done: Independently audit the plan against `AGENTS.md`, `GUIDING-PRINCIPLES.md`,
  `SOP.md`, issue #25, and the cited code. Check that the reasoning is grounded; the source-identity,
  privacy, disjointness, red-control, power, paired-statistics, and rollback gates can fail; the two
  training arms isolate reviewed target correction; the scope is the smallest safe next PR; and
  every proposed experiment states a falsifier. Mark claims as verified from code/data, inherited,  [Unverified — no citation]
  or hypothesis where the distinction affects the decision. Review only; do not edit project files.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

### Reviewer · codex · round 1

Verdict: **Changes requested** — the matched-arm and disjointness design is sound, but the plan cannot yet make its promised ship/discard decision safely because its primary threshold is unspecified and its privacy text contradicts the repo's raw-transcript rule.

swept file: yes

- [Blocker] `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:196-223,233-237` — `primary effect`, the decision threshold, alpha/direction, and the numerical regression bound are only promised as future predeclarations. Thus “no primary improvement” and “regression-bound breach” cannot yet be falsified, while the Definition of Done claims a ship/discard decision. **Fix:** before pool selection, state the single primary metric/test, null/alternative and alpha, minimum effect or decision rule, numeric regression bound(s), and the exact `INCOMPLETE`/discard/ship outcomes; retain top-3 and resampling as secondary/sensitivity results.
- [Blocker] `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:239-243` — the assertion that existing prompt transcripts may remain public conflicts with the same file’s private-manifest/public-aggregate contract (`:186-195,233-237`) and the extractor’s explicit rule that real prompt output remains gitignored/private (`utils/corpus/extract_claude_transcripts.py:10-24`). It can authorize an irreversible disclosure while the plan otherwise promises none. **Fix:** remove or correct the authorization statement; state unequivocally that raw transcripts, prompts, rendered rows, and local paths remain private/gitignored, and that public receipts are aggregate-only after a secrets/path scan.
- [Should] `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:134-136` still calls the old label a “hard negative,” whereas the corrected experiment expressly forbids a `hard_negative` field or new loss (`:153-157,206-211`). **Fix:** rename it “Arm A frozen-sorter target/baseline target” and link the sentence to the matched-target comparison, preventing an implementer from reintroducing the withdrawn objective.
- [Pass] Source-identity, immutable-manifest, and cross-boundary session/exact-input gates are explicit, including red controls (`PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:181-195`); this directly closes the current extractor/audit identity loss (`doc/recon-25-feedback-experiment.md:17-20,32-34`).
- [Pass] The two training arms hold contexts, exposure, configuration, and validation behavior fixed while allowing only target/reasoning changes (`PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:206-211`), consistent with the token-level loader contract (`needle/model/finetune.py:194-251`) rather than inventing a class-weight or hard-negative objective.
- [Note] The live issue #25 record could not be independently read: `gh issue view 25 --repo HiQS-Labs/Needle-fork --comments` failed at the API connection. I treated its locally embedded plan and recon claims as inherited evidence, not independently verified live state.

Whole-file sweep found no additional pre-existing defects beyond the privacy contradiction and stale hard-negative wording above.

Handing off to codex-producer — go to the Producer window and say “take your turn”; resolve each finding in the relay and update the reviewed artifacts.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
