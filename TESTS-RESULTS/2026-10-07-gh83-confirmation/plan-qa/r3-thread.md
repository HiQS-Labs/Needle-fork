# RELAY · GH83 protocol approval round 3
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-10-07.
-->

NEXT: Producer
STATUS: Approved
ROUND: 3 / 3

## ▶ TAKE YOUR TURN — read this first (works for ANY agent: Claude, Codex, agy)
1. **Read this whole file** (header, Setup, Ground rules, every block in the Log).
2. **Check it's your turn:** `NEXT` (top) names the role to act. Confirm you are bound to it and the
   last Log block isn't already yours. If not → STOP and reply "wrong window — nudge the <other> window."
3. **Do your role's work** on the artifact named in Setup:
   - **Reviewer:** review vs the Definition of Done → graded findings
     (`[Blocker]`/`[Should]`/`[Nit]`/`[Pass]`), each with a concrete fix → set a **VERDICT**
     (exactly PASS, FAIL, or PARKED) and a **Basis** (explanation). **Review the whole file, not just the diff** (GH-268):
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
     **A finding that asks for a behaviour change is a generalization unless you can paste the concrete
     input — a row, a value, a `file:line` — that fails under the current code** (GH-681: the gh673
     final QA relay generalized one late-error observation into "or a later invalid identity", the
     Producer implemented it, the same seat `[Pass]`ed it next round, and one historical NULL-URL
     ledger row then blanked every issue). Every `[Blocker]` or `[Should]` requesting a behaviour
     change MUST carry three lines: `Observed input:` (the failing input you saw), `Affected scope:`
     (the input predicate the change would govern), `Falsifier:` (the fixture or data that would show
     the change unnecessary or wrong, and its expected result).
     A `[Blocker]` must cite an observed failure. This is a protocol rule, not a mechanical check —
     the Producer may disposition a request lacking these as `Declined — unproven generalization`.
   - **Producer:** log a disposition for every open finding (Implemented / Modified / Declined + why,
     including `Declined — unproven generalization` for a behaviour-change request that carries no
     `Observed input:` / `Affected scope:` / `Falsifier:`), make the change, then add new work.
4. **Append ONE block** at the very bottom, directly **above** the marker line. Never edit earlier turns.
   Reviewer headings may be `### Reviewer · Round N`, `### Round N · Reviewer · <agent>`, `### Reviewer (<agent>)` (optionally followed by `— rN`), or `### Reviewer — Round N` (optionally followed by `(<agent>)`); follow the heading with a non-empty review body.
5. **Update the header:** flip `NEXT`; set `STATUS` (`Approved` closes — Reviewer only; else `Open`);
   the Producer bumps `ROUND` when opening a new cycle. If the max `ROUND` ends without `Approved`,
   set `STATUS: Escalated`.
6. **Commit only the relay file** (`relay(gh83-protocol-approval-round-3): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: **.relay-artifacts/GH-83-CONFIRMATION-ROUND.md** — the read-only path that
  `relay-drive.sh --artifact-file /private/tmp/needle-confirmation-x87ufg0r/PROJECT/2-WORKING/GH-83-CONFIRMATION-ROUND.md` seeds into the isolated worktree (read it there; do NOT edit it).
- Reviewer: fable-reviewer   ·   Producer: coordinator
- Started: 2026-10-07
- Definition of Done: Read entire seeded plan and confirm the protocol is sound for a bounded offline configuration comparison. Prior two Fable High reviews issued PASS; all material findings were dispositioned in the last section. This is the third and last review call. Prior signoffs were mechanically rejected (first native max_turns; second moved an old system block). This fresh scaffold has no system blocks. Keep ALL prior thread body bytes intact; only edit NEXT/STATUS/ROUND header and insert ONE Reviewer Round3 block directly before the LAST marker. NEVER move or reformat any previous body. Declare swept file: yes and VERDICT: PASS/FAIL. Quote plan spans for pass findings. No tests, scratch files, tick or git commands: the shim handles token and commit. Read the plan with Read, then Edit just this thread, then stop with short final answer. Antigravity Pro31 High is authorized; Haiku45 effort unsupported/pending is honestly disclosed. Do not invent production scope. Nonblocking improvements may be noted without withholding approval.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

### Reviewer · Round 3 (fable-reviewer, Claude Fable 5.1 High)

swept file: yes — read `.relay-artifacts/GH-83-CONFIRMATION-ROUND.md` lines 1–156 in full (frontmatter, all four phases, unknowns, both disposition paragraphs). Artifact not edited. No tests, fixtures or git run; one read-only arithmetic probe under `.relay-scratch/tmp/arith.txt`.

**VERDICT: PASS**

**Basis:** the protocol is sound for a bounded offline configuration comparison. Every bound is explicit and internally consistent, every prior S/N finding is dispositioned in lines 149–155, the Pro High exception and the Haiku 4.5 effort uncertainty are disclosed in the roster paragraph, and no production scope is introduced. Both nonblocking items below are clarity edits, not protocol changes, and do not withhold approval.

- `[Pass]` Counts reconcile. Probe (`python3`, rc=0): `calls 8*3*4 = 96`, `cases 12*3 = 36 ; points 36*4 = 144`, `count per packet per label = 4`, `pairs C(8,2) = 28`, `bonferroni tail draws = 44.6`, `groups 8*4 = 32 ; grading calls = 64`, `sec per call 21600/96 = 225.0`, `margin 2/144 % = 1.39`, `probes 8+1 = 9`. Matches artifact:107 "96 maximum scheduled candidate calls = 8 configurations × 3 passes × 4 packets, plus nine recorded synthetic availability probes", :66 "every packet has 4/4/4 labels", :127 "8 configurations × 4 packets = 32 groups, × two reviewers = exactly 64 maximum calls", :129 "adjusted tail has about 45 of 50,000 resamples" and "(~1.39 percentage points)", :107 "225-second mean needed for 96 calls in six hours".
- `[Pass]` Scale conversion is correct. :129 "Family means are /4; multiply the mean over families by 36 to express pair differences on /144" — mean of twelve /4 family means × 36 cases = /144.
- `[Pass]` Failure semantics are consistent across phases. :107 "Failed transport and cap-killed timeouts are terminal ungraded I, retain their scheduled cells with no retry, and make that configuration incomplete; only delivered but structurally invalid answers are zero" agrees with :129 "No primary interval/mean/winner is computed for an incomplete configuration" and :153 "S1 accepted: cap kills and transport failures are ungraded I and configuration-incomplete".
- `[Pass]` Blinding and grader independence hold. :127 "Use fresh grading sessions distinct from planning/corpus review; coordinator adjudication is also blinded until final marks are locked" and "Record per-reviewer-per-configuration subtotals to expose potential same-family bias"; neither grader (Fable High, Astra Medium) is a candidate lane in the :94–103 table.
- `[Pass]` Required disclosures present. :102 "high — operator-authorized exception"; :105 "The operator explicitly authorized Pro High on 2026-10-07; it is retained in the consolidated roster with a visible exception and cannot support an all-Medium claim" and "Haiku4.5 accepted the CLI flag, but official model docs say native effort is unsupported; its default/legacy diagnostic inclusion awaits operator authorization"; :129 "If any requested configuration is unavailable/incomplete, the claim is explicitly limited to completed eligible configurations".
- `[Pass]` Scope is bounded: :37 "no service, provider framework, new production module, new test suite or gate registry"; :145 "Caps: 3 plan relay rounds, 3 final QA rounds, 9 probes (including rejected Pro Medium), 96 candidate cells, 64 grading calls, six-hour candidate wall ceiling".
- `[Pass]` Pre-existing defect sweep: no contradictions found between Phase 2 corpus rules (:66–68), Phase 3 schedule (:107) and Phase 4 analysis (:129). Dispositions :153 and :155 account for S1–S4 and N1–N7; none reopened.
- `[Should]` (nonblocking) Predeclare the scope of canary failure. :77 "a reviewer failing a canary is invalid, its candidate marks excluded, with no replacement grading calls" can be read per group (that group's 36 marks) or per reviewer (all 32 groups). Observed input: :77 span above, with canaries mixed per group at :127 "Mix unlabelled single-case controls into those groups". Affected scope: grading-validity rule only; no inference or scoring change. Falsifier: if the intended reading is per group, add "for that group"; if per reviewer, say so and note that one failure then makes all eight configurations grading-incomplete under :77 "Any group lacking two valid independent reviews is incomplete grading". Either reading is conservative, so this does not block.
- `[Nit]` Roster table: give the haiku45 row (:98) a visible annotation matching the pro31 convention at :102, e.g. "medium — native effort unsupported per docs; diagnostic pending authorization", so the table alone does not read as eight clean Medium lanes.
- `[Nit]` :109 has a duplicated phrase ("slash commands disabled, sandbox; ineffective plan mode is omitted with slash commands disabled"); tidy wording, no semantic change.
- `[Nit]` :107 states the invalid-delivered-is-zero rule twice in adjacent sentences; keep one.

Relay closed (Approved), no further turn needed. Producer (coordinator) may apply the three nits and the canary-scope clarification before the Phase 1 commit at :54.


### Attestation · relay-drive — 2026-10-08T05:03:27Z
task: RELAY-GH83-PLAN-R3
reviewer: fable-reviewer
status: Approved
reviewed-head: 8f151e1af3d38443ae4026afe7a3e34924163201
added-range: 6420+5142
added-sha256: 2c2c327eedf890078d95d650057364d4bac685889a7d6e8d16f206d36acb7ad8
<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
