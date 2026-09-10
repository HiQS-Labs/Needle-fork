# RELAY · Needle 25 source-gate implementation QA
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
6. **Commit only the relay file** (`relay(needle-25-final-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md
- Review scope: the complete `origin/main...b7dcee3` issue #25 branch diff and every full changed
  source/test file, especially `utils/corpus/transcript_events.py`,
  `utils/corpus/build_experiment_manifest.py`, the extractor/sampler/scorer integrations, and
  `tests/test_corpus_identity.py`.
- Reviewer: codex   ·   Producer: codex-producer
- Started: 2026-09-09
- Definition of Done: Independently check correctness, fail-closed behavior, legacy compatibility,
  determinism, source/event identity under mount moves and subagent transcripts, complete overlap
  boundaries, public-receipt privacy, non-vacuous tests, and agreement with the approved #25 plan.
  Verify the claimed real-data receipt and `INCOMPLETE` conclusion from tracked aggregates. Sweep the
  full changed files for pre-existing defects. Review only; do not edit project files. End with
  exactly `**Verdict:** Approved`, `**Verdict:** Changes requested`, or `**Verdict:** Blocked`.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

### Reviewer · codex · round 1

swept file: yes

- [Blocker] The source verifier authenticates the selected action and its current mapper label, but not the pair's `recent_user_request` or `prior_actions`: it only checks that the latter is a non-empty list at `utils/corpus/build_experiment_manifest.py:182-185`, then hashes and serializes those caller-supplied values at `utils/corpus/build_experiment_manifest.py:230-248`. A pair can therefore retain a valid source event/session/hash while substituting a different q1 context, evade exact q1/content overlap, and freeze an input that the transcript never produced. Reconstruct the bounded user/action context for the selected ordinal from the hashed transcript and require exact equality before hashing/serializing; add red controls independently mutating the user request and prior-actions that leave the manifest absent.
- [Blocker] Historical exclusions are optional, so this command can produce an `ok` receipt with no fitting/prior-audit/model-selection boundary: both exclusion flags default to empty at `utils/corpus/build_experiment_manifest.py:519-522`, and the only evaluation-exclusion checks iterate the supplied map at `utils/corpus/build_experiment_manifest.py:440-468`. That violates the approved decision rule requiring evaluation sessions be excluded from *all* fitting, prior audit, and model-selection evidence (`PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:197-201`). Make the required boundary inventories explicit command inputs (or require and validate named exclusions for each category) and add a red control proving omission refuses before either output is written.
- [Pass] The recorded aggregate receipt supports the present `INCOMPLETE` conclusion: it reports zero correction/evaluation session, event, q1, and content intersections at `TESTS-RESULTS/2026-09-09-issue-25-source-gate/receipt.json:136-155`, but only 17 evaluation sessions at `TESTS-RESULTS/2026-09-09-issue-25-source-gate/receipt.json:285-291`, below the 30-session floor in `PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:206-208`.
- [Pass] I swept the complete named implementation/integration/test files and found no additional pre-existing correctness defects. The focused identity suite passed: `9 passed in 0.52s` (`tests/test_corpus_identity.py:92-266` covers mount identity, duplicate events, manifests, drift, and declared overlaps).

**Verdict:** Changes requested

handing off to codex-producer — go to the Producer window and say 'take your turn'.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
