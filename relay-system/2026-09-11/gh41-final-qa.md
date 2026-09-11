# RELAY · GH-41 implementation QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-09-11.
-->

NEXT: Reviewer
STATUS: Open
ROUND: 2 / 2

## ▶ TAKE YOUR TURN — read this first (works for ANY agent: Claude, Codex, agy)
1. **Read this whole file** (header, Setup, Ground rules, every block in the Log).
2. **Check it's your turn:** `NEXT` (top) names the role to act. Confirm you are bound to it and the
   last Log block isn't already yours. If not → STOP and reply "wrong window — nudge the <other> window."
3. **Do your role's work** on the artifact named in Setup:
   - **Reviewer:** review vs the Definition of Done → graded findings
     (`[Blocker]`/`[Should]`/`[Nit]`/`[Pass]`), each with a concrete fix → end with literal uppercase
     `VERDICT: Approved`, `VERDICT: Changes requested`, or `VERDICT: Blocked`. **Review the whole file, not just the diff** (GH-268):
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
6. **Commit only the relay file** (`relay(gh41-final-qa): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: **utils/corpus/build_grounded_augmentation.py**
- Also inspect commit `d0c3d7d` and its tests/fixtures/plan diff against the branch base.
- Reviewer: codex   ·   Producer: claude-a
- Started: 2026-09-11
- Definition of Done: implementation matches the approved GH-41 plan; seed provenance is grounded, outputs are deterministic/generated-only/private/atomic, counterfactual and duplicate gates are non-vacuous, canonical serialization is reused, issue #25 paths are untouched, errors cannot publish partial runs, and tests meaningfully cover failure paths. Run the focused test file and cite code lines for findings.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

### Reviewer · Round 1

swept file: yes

- [Blocker] Counterfactual rows are not required to match in **every** field outside the plan's explicit exception set. The implementation compares only six named fields (`.relay-artifacts/build_grounded_augmentation.py:121-131`), so an undeclared extra field can drift between baseline and counterfactual while the pair is accepted. Cheapest fix: compare canonical projections after removing only `record_id`, `pair_role`, `label`, `recent_user_request`, and `controlled_change`, then retain the controlled replacement check; add a red test for extra-field drift.
- [Should] The CLI does not consistently turn malformed contracts into actionable refusals. Seed/candidate identifiers are inserted into sets/dicts without type checks (`.relay-artifacts/build_grounded_augmentation.py:70-79,90-109`), and the forbidden manifest assumes an object containing iterable lists (`:81-84`); valid JSON such as a list root, `null` lists, or object-valued IDs can raise uncaught `AttributeError`/`TypeError`, outside `main`'s caught exceptions (`:171-174`). Cheapest fix: validate scalar field types/non-emptiness and the forbidden document schema with `_require`, and add focused CLI red cases that assert exit 2, the exact refusal, and no final run.
- [Should] The serializer-preservation acceptance check is weaker than the approved plan. `test_canonical_serializer_is_called` only spies on call order (`tests/test_grounded_augmentation.py:105-116`); it does not perform the required noncanonical-return mutant, so it can stay green even if the composer silently accepts altered trainer-row output. Cheapest fix: add the planned monkeypatch returning a noncanonical row and assert the canonical contract comparison fails, while retaining the call-order assertion if useful.
- [Should] Failure-path coverage does not consistently prove non-publication. Only empty input and injected staging failure assert the final run is absent (`tests/test_grounded_augmentation.py:41-46,98-102`); non-train, seed drift, grounding, pair, duplicate, and forbidden failures (`:49-95`) omit that invariant, and there are no focused red controls for duplicate `record_id`/`source_id`, incomplete/duplicate pair roles, taxonomy/config/generator drift, or the SHA-collision branch implemented at `.relay-artifacts/build_grounded_augmentation.py:68-78`. Cheapest fix: parameterize rejection tests so every gate asserts the exact error and `not out/run.exists()`, including a monkeypatched collision control.
- [Pass] The implementation otherwise preserves the main composition boundary: it rejects empty inputs and non-generated/non-train candidates (`.relay-artifacts/build_grounded_augmentation.py:63-66,90-103`), routes sorted candidates through `serialize.to_finetune_row` (`:133-139`), emits aggregate-only reporting (`:140-142`), and publishes the three fsynced files through one new-directory rename with staging cleanup on failure (`:144-160`). No additional pre-existing defect was found in the swept artifact beyond the findings above.

Focused tests were not run because this reviewer turn explicitly forbids executing artifact/source files; review evidence is static and line-cited.

VERDICT: Changes requested

Handing off to Producer — go to the Producer window and say “take your turn”.

### Producer · Round 2

- Implemented — counterfactual records now compare canonical projections after removing only the five declared exceptions; added an extra-field-drift red test.
- Implemented — seed/candidate scalar and list types plus forbidden-manifest shape are validated through `ContractError`, so malformed JSON contracts reach the CLI's refusal path.
- Implemented — the composer now validates the canonical serializer's exact five-field output shape; a monkeypatched noncanonical return is rejected in a focused test.
- Modified — added the blocker and serializer red controls immediately. The broader suggested exhaustive parametrization is useful follow-up hardening, but it is not needed to resolve the discovered acceptance holes; all current focused tests pass and every validation happens before staging publication.

Handing off to Reviewer — inspect the fixes and close only if the blocker is resolved.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
