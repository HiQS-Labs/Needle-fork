---
title: Automatic Codex app shortlist and optional feedback
status: planning
created: 2026-09-13
updated: 2026-09-13
owner: Codex
goal: Make three broad next-action choices available without a manual rating workflow
gh_issue: 63
related: [1, 49, 62]
---

## Status

| What was just completed | What's next |
|---|---|
| Operator requirements confirmed; source recon complete; Agy QA pending. | Review plan, then separately authorize the app connection proof. No hooks installed. |

## Table of contents

- [Scope and interaction](#scope-and-interaction)
- [Phase 1 — prove the app connection](#phase-1--prove-the-app-connection)
- [Phase 2 — connect the predictor and private feedback](#phase-2--connect-the-predictor-and-private-feedback)
- [Later training and review](#later-training-and-review)

## Scope and interaction

Canonical issue: [#63](https://github.com/HiQS-Labs/Needle-fork/issues/63), under #1.
Grounding: [Recon map](RECON-CODEX-FEEDBACK.md). This is a usability/data-collection
trial of the simple Markov baseline, NOT the neural Needle model. Its approximately
85% top-three historical coverage is over six broad categories, not an 85% chance
of proposing the right task. #62's failed phase-model gate stays failed.

Confirmed requirements: this Codex app/chat, automatically after every completed
turn, normal work instructions unchanged, separate intended and completed feedback.
No command execution from a selection, no daemon, UI framework, extra model API,
automatic training, CSV homework, or new experiment branch. PR #43 stays held.

Proposed display (illustrative order, not an actual prediction):

```text
Needle [n17] — broad choices, not instructions:
1. Read code   2. Run tests   3. Edit code
```

Your next message can remain normal work text:

```text
Run the parser tests, then fix the empty-input failure.
#needle want 2
```

Later, report what actually happened using `#needle did n17 2`. `want` is a
preference; `did` is a user report, not independently verified execution.
Allow `none` and `skip` instead of forcing one of three; optional explanation can
stay in ordinary text. Bare `#needle 2` is shorthand for `want 2`, never `did`.
An omitted suggestion ID binds only to the immediately preceding displayed
shortlist in this session; older reports require an ID. Invalid, conflicting or
unknown IDs are not training labels. Quoted/code-fenced markers are not commands.
A marker-only message records feedback but authorizes no work. It still gets one
new automatic shortlist when that user turn completes, as requested.

The first version predicts categories from the last usable action, NOT the
meaning of the user's work answer. Keep that answer as separate optional training
material; do not claim the simple predictor understands it. Cold starts use clearly
marked global-prior choices. Unmapped activity is recorded as unknown, not invented.

**Bet:** a small persistent shortlist plus optional one-line feedback is tolerable
where the manual form was not. Failure: suggestions are too broad or repetitive,
or the app cannot display them cleanly. Integration is Easy to undo by disabling
only these hooks; publishing private work text is Costly and excluded.

## Phase 1 — prove the app connection

1. After implementation authorization, test a minimal trusted repo-local `Stop`
   hook in this installed app, using synthetic text only. Prefer JSON
   `systemMessage` (documented UI/event-stream warning) without `decision:block`.
   → Expect three readable choices visibly after a completed turn, not merely a
   log entry. Record app/runtime versions and exact payload. CLI success alone
   does not pass. Write findings back here before proceeding.
2. Prove `UserPromptSubmit` receives a synthetic normal answer plus marker
   unchanged, with stable session/turn identity. → Expect ordinary work text
   preserved. Additional context may explain metadata but must not promote user
   text into trusted instructions. Never execute shell fragments from the prompt.
3. QA gate: three consecutive completed turns, including a tool-free and a
   marker-only turn, each show exactly one list; no extra model continuation,
   repeated hook loop, subagent output, or blocked normal work. Disable the hook
   → display disappears (negative control). Re-enable → returns. Record synthetic
   evidence under `TESTS-RESULTS/2026-09-13-codex-feedback/`. If native warning
   display is absent/unusable, stop and ask about a fallback. Do not silently
   substitute manual invocation, an agent instruction, CLI-only support or a
   forced continuation. Such alternatives require a new user choice.

## Phase 2 — connect the predictor and private feedback

4. Only after Phase 1 passes, add one small stdlib dispatcher plus focused tests;
   reuse existing fitting/ranking and semantic mappings rather than duplicate
   them. Prepare a versioned local count table once from the retained trusted
   training split, never fit on holdout or each turn. Record training manifest,
   table hash, source revision and label version. Require nonempty six-label
   support; preserve all old predictor outputs/tests. No heavyweight model load.
5. Capture the context prefix before choices, using only this session up to the
   stop event. Pair tool calls/results where possible; distinguish completed,
   failed, outstanding and unknown activity. The historical adapter alone is not
   proof of completion. Do not interpret a request to act as an action performed.
   Bound hook runtime to two seconds and context to the latest 32 KiB at valid
   record boundaries, record truncation, and degrade to marked prior choices when
   parsing is incomplete. Missing table → visible unavailable notice, not fake
   choices. Normal work must continue on failure.
6. Add narrowly scoped Git ignores before the first private write. Store append-only
   events in `relay-system/.needle-feedback.jsonl`, with a hidden lock beside it,
   restrictive file permissions, file locking and duplicate event suppression.
   Pin this repo-local path rather than following archive redirection. Validate
   resolved paths/symlinks and refusal of tracked or unignored destinations.
   Reuse the existing transcript root, not old public review files. Each suggestion
   records session/turn/suggestion ID, timestamp, exact displayed ordered labels,
   context prefix/cutoff, source and table versions, fallback/truncation status.
   Each feedback event records its own ID, referenced suggestion, `want` versus
   `did`, label resolved against that frozen order, untouched ordinary answer,
   user-report provenance and validity. Missing feedback is not rejection. Log a
   suggestion as generated, not proof the user saw it; explicit feedback attests
   engagement. No automatic Git add, upload, archive redirect or model call.
7. QA gate: synthetic end-to-end records must be nonempty and replayable. Test
   two simultaneous sessions, duplicate delivery, restart, delayed explicit-ID
   reports, malformed/quoted markers, none/skip, disk errors and corrupt lines.
   Show that swapping choice order cannot change a past label; removing the ID
   check fails; adding later answer text to prediction context fails; disabling
   lock/idempotence fails concurrency checks. A later completed report must never
   overwrite an earlier preference. Verify unchanged normal instructions and no
   tool execution from metadata. Test actual XYZ collector with synthetic private
   markers → none copied; expose an ordinary-subfolder marker → detected control.
   Record red/green evidence in the receipt directory; private logs stay private.
   Run `pytest -q -m "not slow"` and review scoped diff before main commit/push.
   Disable hooks → ordinary app behavior restored, existing feedback retained.

## Later training and review

Records could support later training, but are not immediately a fine-tuning dataset.
Keep intentions, user-reported completions and independently observed tool outcomes
as different sources. Choices influence answers, so acceptance is not unbiased
accuracy. None/skip, blank examples and invalid matches never become positive labels.
Before any training: user-approved private-data review, secrets removal, purpose
and license/provenance checks, leakage-free pre-answer inputs, and whole-session
train/test separation. Six broad categories do not supply exact tool arguments or
the full 44-label taxonomy. No claim of automatic improvement while collecting.

Review usefulness after a short voluntary trial: was it easy to ignore/use, were
choices relevant, and did it save effort? User can stop at any time; no mandatory
rating quota and no numerical product-success claim based on sparse feedback.

Planning QA: pending Agy via the shipped relay harness. Review the whole plan for
app feasibility, privacy/collector behavior, feedback pairing, leakage, failure
paths and unnecessary complexity. Approval of the plan is not a working-app claim.
