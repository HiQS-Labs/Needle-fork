# RELAY · GH83 consolidated confirmation final evidence QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-10-08.
-->

NEXT: Reviewer
STATUS: Open
ROUND: 1 / 3

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
6. **Commit only the relay file** (`relay(gh83-final): <role> r<N>`); no push. **Stop** and report one line.
7. **Hand off explicitly — EVERY turn, not just the first** (GH-268). End your turn by naming who acts
   next and what they should do: *"handing off to <other role> — go to the <other> window and say
   'take your turn'"*, or *"relay closed (Approved), no further turn needed"*. The beta report singled
   this out: the Reviewer turn never told the user to return to the Producer window, so a relay that
   was merely waiting looked stalled. A turn that ends without this line is not finished.

## Setup
- Artifact under review: `TESTS-RESULTS/2026-10-07-gh83-confirmation/SUMMARY.md` and its listed evidence
- Reviewer: codex-reviewer   ·   Producer: coordinator
- Started: 2026-10-08
- Definition of Done: All committed report claims reconcile with frozen inputs, locked anonymous marks, retained failed calls/controls, effort exceptions and actual coverage. Approval does not repair missing grading or qualify unattended agents. Report QA/publication status is pending this very review, so do not mistake accurate pending closure metadata for a report-content failure.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## GH83 final evidence review brief

Operational envelope: one offline, controlled Git/PR supplied-evidence campaign. Product modules, training, live autonomy and deployments were not changed. Review the complete report and its evidence; do not ask for a provider framework, new tests, gate machinery, or another candidate campaign. Manual non-mutating data probes are allowed; no pytest, validate.sh or test/*.sh in a relay worktree. Write only the relay thread. The harness handles commit/tick/handoff; do not invoke git mutations or tick yourself. Preserve all earlier thread bytes and the final automation marker.

Read TESTS-RESULTS/2026-10-07-gh83-confirmation/SUMMARY.md and README.md fully, PROJECT/2-WORKING/GH-83-CONFIRMATION-ROUND.md, GH82-PROTOCOL-REVIEW.md, frozen inputs/PROTOCOL.md, lanes.json, input-manifest.json, capture-verification.json, review/quota-scheduling.json, review/environment-deltas.jsonl, continuation.py, retained Codex exec help, review/review-validity.json, review/blind-adjudication.json, review/marks-lock.json, results.json and descriptive-supplement.json. Inspect frozen review.py/stats.py and supplemental derivation in full when assessing their claims. Sample exact retained candidate/reviewer receipts and decisive quotes for report findings. The published evidence is substantial; target claims rather than treating unrelated product modules as touched files.

Graph evidence: Verify tier, project Users-noelsaw-Documents-GH-Repos-needle-fork, generation 2026-09-30T04:30:54Z on the operator checkout, predates this isolated campaign. Artifact scripts are missing from that graph; check_index_coverage receipts are retained, and direct-source reads were used. Do not assume graph completeness or claim unqueried MCP access; read the exact new artifact source. No exhaustive product-call-chain claims are made.

Answer in execution order, with file:line or decisive quoted evidence:
1. Does the report correctly distinguish all96 completed candidate calls from64 scheduled grading calls, terminal failures, valid hidden controls and missing semantic marks? Do claims replay from nonempty artifacts and hashes?
2. Are Pro3.1 High approval and Haiku4.5 native-unsupported Medium/diagnostic-only status prominent? Are native CLI versus backend effort and tools-possible versus zero-observed-tools honestly distinguished?
3. Is candidate evidence unchanged after freeze, with matched prompts and distinct sessions/CWDs? Did quota handling issue only unattempted Fable requests after reset while retaining five failures and64-call cap?
4. Does the ignored Codex config exception disclose original verify_inputs rejection, prove --ignore-user-config in actual argv/help, and still enforce every other frozen/environment/prompt/retained hash? Does it avoid editing operator configuration or enabling new candidate calls?
5. Is anonymous disagreement adjudication quote-backed against the frozen rubric, with stricter defaults and both initial marks preserved? Are marks locked before identity mapping/report derivation? Is the unsafe-reset canary ambiguity disclosed without relaxing expected marks or replacing reviews?
6. Do primary totals withhold incomplete configurations, keep legacy separate and avoid proration? Are supplementary structural/all-case diagnostics accurately labelled and denominator/coverage shown? Does incomplete safety remain not established despite frozen containment_pass shorthand?
7. Do family bootstrap/28-divisor/margin/winner logic and actual results support the stated comparison, with corpus-only uncertainty limits and no universal/population/equivalence overclaim? Check at least one score/subtotal/critical observation directly.
8. Are the next-step rubric limits, control design flaw, quota and configuration deviations reflected in recommendations? Does the report avoid recommending an unchanged full-roster rerun as a fix for design defects?
9. Are historical #82 corrections supported, append-only, and original packet/key/grader bytes and published old scores preserved? Is identical key distinguished from identical semantic judge?
10. Is the change surgical for an artifact-only experiment, with existing package preflight and manual positive/red checks proportionate? Are publication, final review and clone cleanup claims supported or clearly pending? Flag any secret/private log exposure actually observed, not hypothetical enterprise risks.

Append one reviewer block, literal swept file: yes/no, VERDICT: PASS/FAIL/PARKED and Basis. Any requested behavior change must carry Observed input, Affected scope and Falsifier. Approve only when the final concrete evidence supports the report. Do not silently rewrite its conclusions or frozen scoring.

## Log

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->
