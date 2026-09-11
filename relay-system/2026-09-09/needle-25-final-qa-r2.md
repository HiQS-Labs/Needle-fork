# RELAY · Needle 25 source-gate implementation QA round 2
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
6. **Commit only the relay file** (`relay(needle-25-final-qa-r2): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md
- Review scope: complete `origin/main...f1bb8a2` diff and every full changed source/test/receipt file.
  Round-one findings are preserved in `needle-25-final-qa.md`.
- Reviewer: codex   ·   Producer: codex-producer
- Started: 2026-09-09
- Definition of Done: Confirm or reject that q1 request/history/target are reconstructed from the
  hashed source event; fitting, prior-audit, and model-selection exclusions are all mandatory and
  checked; canonical recovery admits exact `(session, step, full row)` matches only; appended and
  mapper-drifted rows cannot enter; receipt claims match tracked aggregates; privacy and legacy
  compatibility hold; all tests are non-vacuous. Sweep all changed files. Review only; do not edit
  project files. End with exactly `**Verdict:** Approved`, `**Verdict:** Changes requested`, or
  `**Verdict:** Blocked`.

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

- [Blocker] Canonical-train recovery is still optional: `_legacy_membership` returns `(None, None)` when both correction-membership options are omitted (`utils/corpus/build_experiment_manifest.py:368-374`), and `build` then freezes all caller-supplied correction pairs (`utils/corpus/build_experiment_manifest.py:510-516`). That permits an `ok` manifest whose correction rows have never passed the required legacy `(session, step, exact full-row)` canonical-training gate, contrary to the approved correction-candidate rule (`PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:197-201`). Require the two membership inputs for this source-gate command and add a red control proving their omission leaves both outputs absent.
- [Should] The no-native-ID fallback does not implement its stated subagent isolation. Although `session_id` includes the relative path for reused parent `sessionId` values (`utils/corpus/transcript_events.py:94-98`), an action with neither tool-use ID nor record UUID still scopes its event ID to the shared raw `transcript_session_id` (`utils/corpus/transcript_events.py:130-141`). Two distinct subagent transcripts with that shared ID and an ID-less action at the same ordinal collide and are rejected as a duplicate. For the fallback branch, include the namespaced `session_id` (and retain native-ID copy detection where native identity exists); add a two-subagent missing-native-ID regression test.
- [Pass] Round-one q1-context and exclusion-boundary failures are now fail-closed: the verifier rebuilds and compares `recent_user_request`, `prior_actions`, and `step` from the source event (`utils/corpus/build_experiment_manifest.py:145-159, 214-231`), and every required boundary category must resolve to a supplied exclusion (`utils/corpus/build_experiment_manifest.py:454-472`). The corresponding red controls are present at `tests/test_corpus_identity.py:285-312`.
- [Pass] The tracked receipt still supports `INCOMPLETE`, not a training result: it records 17 evaluation sessions (`TESTS-RESULTS/2026-09-09-issue-25-source-gate/receipt.json:287-299`), below the 30-session floor (`PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md:206-208`), while its declared correction/evaluation and evaluation/exclusion q1/content overlaps are zero (`TESTS-RESULTS/2026-09-09-issue-25-source-gate/receipt.json:141-160`).
- [Unverified — no citation] I swept the changed identity, extractor, sampler, scorer integration, manifest builder, focused tests, and aggregate receipt; beyond the findings above, I found no additional pre-existing correctness defects. No test was run in this reviewer-only relay turn.

**Verdict:** Changes requested

handing off to codex-producer — go to the Producer window and say 'take your turn'.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
