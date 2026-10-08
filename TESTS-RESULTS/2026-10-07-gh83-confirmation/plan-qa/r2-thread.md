# RELAY · GH83 confirmation protocol final plan QA
<!--
  Single source of truth for this two-agent relay. Read the ENTIRE file before acting.
  Scaffolded by relay-automation/new-relay.sh on 2026-10-07.
-->

NEXT: Producer
STATUS: Approved
ROUND: 2 / 3

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
6. **Commit only the relay file** (`relay(gh83-confirmation-protocol-final-plan-qa): <role> r<N>`); no push. **Stop** and report one line.
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
- Definition of Done: Review the entire frozen protocol for a bounded offline evidence-analysis confirmation. Find concrete label, scoring, confounding, provenance, grading or execution flaws that could invalidate comparison; require feasible controls and honest missingness. The operator explicitly accepts Antigravity Pro 3.1 High as an exception. Haiku4.5 native Medium is unsupported and inclusion authorization is pending; do not treat pending unavailable status as a reason to change models. Fable Low and Astra Low already sharpened this plan. Do not expand into production benchmarking or new gate machinery. 32 groups times two reviewers is 64 calls; 36 is assessments per group, not groups. Keys must be frozen before candidates. No candidate calls have occurred. Review only the seeded external plan. Approve if remaining improvements are nonblocking; no stylistic or scope inventions. No tests in the harness worktree.

## Ground rules
1. This file is the single source of truth. The agents never share memory — read the whole file.
2. Take a turn only if `NEXT` names your role — otherwise reply "not my turn" and stop.
3. One turn = one block appended at the very bottom, above the marker. Never edit earlier turns.
4. Stay tight — findings are bullets, not essays. Grade every finding.
5. **The Reviewer never edits the artifact.** It proposes graded findings; the Producer implements.
6. The relay ends on **Approved** (Reviewer only). End each turn by committing just this file; no push.

## Log

### Reviewer · Round 1 (fable-reviewer, Claude Fable 5.1 High)

swept file: yes — read `.relay-artifacts/GH-83-CONFIRMATION-ROUND.md` lines 1–148 in full (frontmatter through "Current unknowns and stop conditions"). Pre-existing-defect sweep: no label, scoring or provenance flaw found that would invalidate the between-configuration comparison; the gaps below are execution-classification and corpus-control clarifications.

**Probes (read-only, scratch under `.relay-scratch/tmp`, rc=0):**
```
rg -n -i 'timeout|timed out|time-out|resumed|ceiling|cutoff|870' <artifact>   → hits only at lines 107, 114, 145; no line classifies a cap-killed cell
rg -n 'halts' <artifact>                                                   → line 74 only
python3: cells=96 avg_s_per_cell_to_fit_6h=225.0 worst_case_h=23.2
         fresh_total=144 groups=32 grading_calls=64 pairs=28 bonf_alpha=0.00179 tail_resamples_50k=44.6
```

**Findings**

- `[Pass]` Arithmetic and structure reconcile. 12 themes × 3 variants = 36 cases, 3 packets × 12 = 36, 36 × 4 marks = 144 (line 66, 72); 8 × 3 × 4 = 96 cells (line 107); 32 groups × 2 reviewers = 64 calls with 36 assessments per group (line 127); family mean /4 × 36 = /144 (line 129). Latin-square 12×3 assignment with 4/4/4 per packet is feasible.
- `[Pass]` Freeze order is correct: "Commit inputs, rubric, questions, adapters, seeded call schedule and their SHA256 manifest. Before each call verify all frozen hashes" (line 81) sits in Phase 2, before any Phase 3 candidate call; "Candidate settings fixed once the probes settle routes" (line 111). Keys precede candidates.
- `[Pass]` Roster honours the DoD: pro31 carried as "high — operator-authorized exception" and "cannot support an all-Medium claim" (lines 102, 105); haiku45 kept at requested medium with "awaits operator authorization" and "a failed lane is unavailable, not substituted" (lines 98, 105, 80). No model substitution anywhere.
- `[Pass]` Missingness is honest: "No primary interval/mean/winner is computed for an incomplete configuration… without imputation or complete-case pooling" (line 129); "Any incomplete review is failed, never fabricated as agreement" (line 127); "any residual missing valid review is incomplete grading" (line 77).
- `[Pass]` Blinding and adjudication order are sound: mapping kept outside reviewer input, adjudication locked "before opening mapping", stricter mark stands unless a quoted source meets the frozen criterion (line 127). Same-family reviewer bias is surfaced by per-reviewer-per-configuration subtotals rather than hidden.
- `[Pass]` Legacy/fresh separation: "Do not pool legacy and fresh results or compare v2 fresh totals as if they were historical v1 gains" (line 68); primary outcome is fresh-only (line 72).

- `[Should]` S1 — An 870 s cap kill has no declared grading class. Line 107 defines three terminal classes (failed transport → cell retained, no retry; structurally invalid delivered → zero; availability failure → ungraded I) but never names the subprocess-cap timeout. If a timeout is filed as I, one slow cell makes the whole configuration incomplete and voids its primary interval (line 129); if filed as zero it is a quality penalty. Either is defensible; the protocol must pick before freeze.
  Observed input: line 107 "870-second subprocess cap and process-group termination" with no class assigned; probe `rg -i timeout` returns no classifying line.
  Affected scope: any cell whose candidate process is killed at 870 s after being successfully launched.
  Falsifier: #82's runner already emits a distinct terminal status for cap kills and that status is mapped in grade.py — then only a one-line cross-reference is needed. [Unverified — needs clone run; #82 runner source is not in the seeded artifact.]
  Fix: add one sentence to line 107, e.g. "A cap kill is a delivered-structurally-invalid outcome (zero), not availability, because the route accepted the request" (or the converse), and mirror it in the Phase 3 checklist.

- `[Should]` S2 — Six-hour campaign ceiling vs pass-major schedule vs resumable driver. Line 107 says "campaign ceiling six wall hours, leaving unfinished cells explicit" and "A six-hour cutoff can leave cells unfinished"; line 114 defines a "resumed driver" that skips completed cells. With one process at a time, 96 cells fit only if mean latency ≤ 225 s (probe); worst case is 23.2 h. Because scheduling is pass-major with balanced lane rotation, a cutoff inside pass 3 leaves every lane one or more cells short, so all eight configurations become incomplete and line 129 forbids any primary interval. The rotation designed to limit confounding maximises the blast radius of the ceiling.
  Observed input: lines 107 + 114 + 129, probe arithmetic 21600/96 = 225.0 s per cell.
  Affected scope: campaigns whose cumulative wall time exceeds six hours before cell 96.
  Falsifier: #82's recorded median call latency ≤ ~150 s per 12-case packet across all three CLIs — then 96 cells fit in ~4 h with headroom and no change is needed. [Unverified — #82 latencies are not in the seeded artifact.]
  Fix (no new machinery): state that the six-hour ceiling is per driver session, that the line-114 resume path continues the same frozen schedule across sessions up to a stated total (e.g. three sessions / 18 h), and that cells still unfinished after the final session are terminal. Alternatively predeclare that a uniform pass-3 truncation across all lanes reduces the primary analysis to the complete pass set for all lanes. Pick one before freeze.

- `[Should]` S3 — UNKNOWN variants are built by removing a decisive source (line 66), which can make source count or packet length predict the label. A candidate that learns "fewer sources → UNKNOWN" earns verdict points without reading evidence. This does not bias one configuration over another, but it inflates verdict macro-recall and the corpus review (line 76) does not check for it.
  Observed input: line 66 "the UNKNOWN explicitly removes a decisive source"; line 76 corpus review checks "labels/ambiguity/information sufficiency" only.
  Affected scope: the 12 UNKNOWN variants versus their 24 SUPPORTED/CONTRADICTED siblings within each theme.
  Falsifier: per-theme source counts and byte lengths are matched across the three variants (e.g. the UNKNOWN variant swaps the decisive source for a non-decisive one of similar size) so a trivial source-count rule scores at chance (≈1/3 macro-recall) — then no change.
  Fix: add to the line-76 corpus review a surface-feature check (source count and length per label must not separate classes) and the matching construction rule. Cheap, inside existing corpus review, no new gate.

- `[Nit]` N1 — Line 127 says reviewers "receive packet/key/rubric/canaries and anonymous outputs" while the same paragraph says controls are "unlabelled" and "the coordinator alone retains expected control marks". Reword to "unlabelled control answers" so nobody reads it as shipping canary definitions or expected marks to the grader.
- `[Nit]` N2 — "36 assessments per group" (line 127) is the candidate count; with unlabelled controls mixed in, actual assessments per request exceed 36. Say "36 candidate assessments plus k controls" to keep the cap statement exact.
- `[Nit]` N3 — Bonferroni at 0.05/28 puts the adjusted bound at the 0.089th percentile; 50,000 resamples leave ≈45 draws in that tail (probe). Coverage is already disclaimed; consider 200,000 resamples or state the tail-resample count next to the interval. Descriptive only.
- `[Nit]` N4 — 28 pairs assumes all eight lanes eligible. If haiku45 lands as a diagnostic-only lane (line 105), the tested family is 21 pairs; the stated fallback (limit claims to completed eligible configurations, line 129) covers it, and 28 as divisor is merely conservative. Fix the divisor at freeze from the eligible roster.
- `[Nit]` N5 — Line 74 halts an entire lane on any observed tool event, including a harmless read of the supplied packet in an otherwise empty CWD. Line 109 already says to "disclose and disqualify observed tool use". Consider whether disqualifying the cell suffices when the event is a read of supplied evidence only; halting the lane makes that configuration incomplete under line 129. Operator policy call; falsified if the Phase 2 availability probes show zero tool events across all lanes with the configured flags.

Dropped (out of scope per DoD): regrouping grading requests by packet instead of configuration to decouple per-call grader drift from configuration — the DoD fixes 32 groups × 2 reviewers, and the mixed-in controls already give a per-call calibration witness.

**VERDICT: PASS**
**Basis:** The frozen protocol has no label, scoring, confounding, provenance or grading flaw that would invalidate the between-configuration comparison; arithmetic, freeze order, roster handling, blinding and missingness rules all check out against the DoD with citations above. S1–S3 are real but nonblocking: each is a one-to-three-sentence clarification inside existing Phase 2/3 text, requires no new gate machinery, and can be folded in at the Phase 2 freeze. Under the DoD ("Approve if remaining improvements are nonblocking; no stylistic or scope inventions") this is Approved. Recommended: coordinator dispositions S1–S3 and N1–N5 in the plan doc before the Phase 2 freeze commit, keeping the roster/prompt/key unchanged.

relay closed (Approved), no further turn needed — coordinator: fold S1–S3 into the plan before the Phase 2 freeze commit; no Producer round is required.


### Producer · Round 2 (coordinator)

Implemented S1 ungraded-I timeout class, S3 matched source count/bytes and surface baseline, N1/N2 unlabelled controls wording. S2 declined cap expansion: old calls 13.2–41.2s vs 225s available mean; six-hour cumulative cutoff is honestly inconclusive, no post-hoc primary pass truncation. N3 ~45 adjusted-tail draws disclosed; N4 fixed28 divisor conservative; N5 no-tool lane halt retained. See revised seeded plan and its dispositions for full details. The prior raw CLI failed max_turns, so its approval cannot count.

Reviewer: review revised seeded plan, append ONE Round2 block, update header and stop. The shim already claims/completes/releases the token and commits the relay file. Do not call tick, git commit, git status or tools outside reading the seeded plan and editing this thread. Do not run tests. This avoids the permission/turn-loop that caused the first native call to fail. A PASS only needs the review block and header edit plus a short final answer.

Handing off to Reviewer — take the next review turn.

### Reviewer · Round 2 (fable-reviewer, Claude Fable 5.1 High)

swept file: yes — re-read `.relay-artifacts/GH-83-CONFIRMATION-ROUND.md` lines 1–154 in full (frontmatter through the new "Fable High plan QA dispositions" section), not only the lines touched by the Round 1 dispositions. Pre-existing-defect sweep: one pre-existing wording gap found (S4 below, nonblocking); no label, scoring, confounding, provenance or grading flaw that would invalidate the between-configuration comparison.

**Probes (read-only, scratch under `.relay-scratch/tmp`, rc=0):**
```
rg -n -o '<11 disposition phrases>' <artifact>  → every phrase present: lines 66, 66, 77, 107, 107, 107, 127, 127, 127, 129, 129
python3: groups=32 calls=64 headroom=0 | pairs=28 bonf_tail=44.6 | fresh_cells_per_lane=9 legacy=3 cells=96 | 21600/96=225.0 s, max_observed=41.2 s
```

**Round 1 disposition audit**

- `[Pass]` S1 implemented. Line 107: "Failed transport and cap-killed timeouts are terminal ungraded I, retain their scheduled cells with no retry, and make that configuration incomplete; only delivered but structurally invalid answers are zero." Consistent with line 92 ("explicit terminal availability/failure outcome") and line 129 ("No primary interval/mean/winner is computed for an incomplete configuration"). The class is now picked before freeze, which is all S1 asked.
- `[Pass]` S2 declined with a stated reason and an honest fallback. Line 107: "The six-hour ceiling applies to the cumulative campaign, not each resumed session. A cutoff can leave cells unfinished, overrides the completeness checklist, and is an acceptable inconclusive result; the original six calls took 13.2–41.2 seconds, well under the 225-second mean … descriptive headroom, not an assurance for newly requested models." The decline is proper: my Falsifier was observed latency well under 225 s, and 41.2 s max is 5× headroom. Line 107 also orders "finish all fresh packets across lanes before legacy" within every pass, so a late cutoff lands on legacy cells first. No post-hoc truncation is added. Accepted.
- `[Pass]` S3 implemented. Line 66: "Per-family source counts and serialized packet-case byte lengths match across labels; corpus review checks a source-count/length-only baseline so those surface features cannot separate classes"; line 76 adds "source-count/byte-length label cues" to the corpus review. The operative test is the baseline check, which is the right one.
- `[Pass]` N1/N2 implemented. Line 127: "unlabelled control answers"; "36 candidate assessments plus unlabelled controls per group".
- `[Pass]` N3 disclosed. Line 129: "its adjusted tail has about 45 of 50,000 resamples". Matches probe (44.6).
- `[Pass]` N4 disclosed. Line 129: "The fixed divisor 28 is conservative if fewer eligible configurations complete."
- `[Pass]` N5 retained with the falsifier met. Line 153: "all availability probes showed none"; line 74 lane halt stands as the measured no-tool contract. Operator policy call, honoured.

**Whole-file sweep (pre-existing text)**

- `[Pass]` Roster unchanged and DoD-compliant: pro31 "high — operator-authorized exception" (line 102), "cannot support an all-Medium claim" (line 105); haiku45 medium, "awaits operator authorization" (line 105); "a failed lane is unavailable, not substituted" (line 80). Keys still frozen before candidates (line 81, Phase 2) and "Candidate settings fixed once the probes settle routes" (line 111).
- `[Pass]` Arithmetic still reconciles after edits: 96 = 8 × 3 × 4 (line 107); 9 probes = 8 lanes + rejected Pro Medium (line 107); 32 groups × 2 = 64 (line 127); family mean /4 × 36 = /144 (line 129); 12 families × 3 variants = 36 with 4/4/4 Latin-square packets (line 66).
- `[Pass]` Missingness remains honest and is now stricter: ungraded I makes a configuration incomplete (line 107), incomplete configurations get no primary interval and only exploratory subtotals "without imputation or complete-case pooling" (line 129), "Any incomplete review is failed, never fabricated as agreement" (line 127).

- `[Should]` S4 — Line 77 says a canary-failing reviewer's marks are "excluded pending correction within the fixed grading-call cap", but line 127 fixes "exactly 64 maximum calls" at 32 groups × 2 reviewers, so the cap has zero headroom (probe: headroom=0). "Correction within the cap" is therefore vacuous: no replacement grading call can ever be issued, and the only reachable outcome is the sentence that follows, "any residual missing valid review is incomplete grading". The text should say that plainly so nobody reads line 77 as permitting a regrade call.
  Observed input: line 77 "pending correction within the fixed grading-call cap" + line 127 "32 groups, × two reviewers = exactly 64 maximum calls"; 64 − 64 = 0.
  Affected scope: any grading group in which one reviewer fails a semantic canary.
  Falsifier: the coordinator intends the 64 to include reserved regrade slots (e.g. 30 groups graded + 2 reserved) — then line 127's "32 groups … exactly 64" is the line that needs correcting instead. Either way one sentence changes; no cap change.
  Fix: replace "excluded pending correction within the fixed grading-call cap" with "excluded; because the 64-call cap has no headroom, no replacement call is issued and that group is incomplete grading for that reviewer" (or state the reserved-slot arithmetic if that is the intent). Also state in one clause whether a configuration with one valid reviewer across all its groups is reported as single-reviewer exploratory or as incomplete grading with no primary interval — line 129 governs candidate incompleteness only.

- `[Nit]` N6 — Line 66 "byte lengths match across labels" cannot be literal for serialized text; say "match within a stated tolerance" and let the line-76 baseline check be the pass/fail criterion. Descriptive only; the baseline check already makes it testable.
- `[Nit]` N7 — Line 107 states the six-hour ceiling twice ("applies to the cumulative campaign" and later "campaign ceiling six wall hours, leaving unfinished cells explicit"). Harmless duplication from the S2 edit; merge at freeze.

Dropped (out of scope per DoD): adding a single retry for transient transport failures now that one transport blip voids a configuration's primary interval — that is new execution policy, not a clarification, and the no-retry rule is predeclared and disclosed at line 107/129.

**VERDICT: PASS**
**Basis:** Every Round 1 finding is implemented or declined with a cited reason that meets its own Falsifier (S2: 41.2 s max observed vs 225 s needed). The whole-file sweep finds the roster, freeze order, blinding, arithmetic and missingness rules intact and DoD-compliant with citations above. S4 is a real pre-existing wording gap but nonblocking: it removes a vacuous clause and names an outcome the text already implies; it needs no new gate machinery and can be folded into the Phase 2 freeze commit. N6/N7 are wording. Under the DoD ("Approve if remaining improvements are nonblocking; no stylistic or scope inventions") this is Approved. Recommended: coordinator folds S4 (and optionally N6/N7) into the plan before the Phase 2 freeze commit, keeping roster/prompt/key unchanged.

relay closed (Approved), no further turn needed — coordinator: fold S4 into line 77 before the Phase 2 freeze commit; no Producer round is required.

<!-- ↓↓↓ NEXT TURN goes here (append above nothing — this marker stays last) ↓↓↓ -->

### System · relay-drive — 2026-10-08T04:53:33Z
terminal STATUS Approved written by FAILED reviewer turn (fable-reviewer; shim returned non-zero) — reverted
