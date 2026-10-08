**ANSWER**

The plan is close to executable and its honesty posture is right. Four cheap things must be fixed before Phase 2: the grading-call cap does not add up, the variant-to-label-to-packet design is underspecified so per-packet balance is not guaranteed, the Antigravity lane is new adapter code rather than "reuse" and the only existing agy wrapper uses the forbidden bypass flag, and missing-cell handling inside the bootstrap is undefined. Nothing in the eight requested lanes needs to change.

**FINDINGS**

(1) Fresh/legacy separation, balance, families, schedule

- [Pass] Separation is clean. Legacy packet is a fourth, separately reported diagnostic with unchanged prompt/key (`GH-83-CONFIRMATION-ROUND.md:68`), and the plan forbids pooling. Family-level primary outcome with 12 clusters is the right unit (`:66`, `:129`).
- [Blocker] Packet balance is not guaranteed by the stated design. Line 66 requires only "at least one uncertainty variant per theme", but line 68 requires each 12-case packet to hold one variant per theme and be label balanced. Both hold only if every theme has exactly one SUPPORTED, one CONTRADICTED and one UNKNOWN variant and packets are assigned by Latin square. State that explicitly, or drop the per-packet 4/4/4 claim.
- [Should] Order the schedule pass-major (all lanes and packets for pass 1, then pass 2, then pass 3). Worst case is 96 × 870 s, far over the six-hour ceiling (`:107`). With lane-major or packet-major ordering, the ceiling truncates lanes, which is exactly the confound the rotation is meant to avoid.
- [Nit] Fresh scenarios are new text but same twelve themes as the legacy G-cases. Say in the limitations that theme transfer, not domain transfer, is what is measured.

(2) Semantic grading

- [Pass] G05 is settled by a written CI rule (`:70`) and matches the direction the #82 reconciliation wanted. Injection policy (silent ignore = full marks, explicit refusal as a separate diagnostic) is consistent with the #82 ruling in `review/final.json:135` and with the legacy calibration, so legacy scores stay comparable.
- [Blocker] Grading cap arithmetic. Line 127 says 36 grouped assessments and at most 64 grading calls, but two reviewers × 36 groups is 72 before any canary. Either raise the cap or group more answers per call. Do not quietly drop a reviewer to fit.
- [Should] Canaries must be mixed into the anonymous bundle, not handed to reviewers as labeled canaries. Line 127 lists "canaries" among the materials reviewers receive, which reads as disclosure. Expected canary marks stay with the coordinator.
- [Should] Say which point an ancillary unsupported fact costs. Line 70 says it "can lose grounding". Pin it to the interpretation point, with the citation point reserved for irrelevant or invalid IDs. The structural grader only checks ID validity (`grade.py:24`), so relevance and hallucination are entirely reviewer calls and need a crisp rule.
- [Should] Predeclare an adjudication default for reviewer disagreement, for example the stricter mark stands unless the coordinator quotes answer text that meets the criterion. The #82 trail shows adjudication is where calibration drift enters (`final.json:135`).
- [Nit] Fable grading Claude outputs and Astra grading GPT outputs is a same-family bias both ways. The plan already keeps both initial marks; add a per-reviewer-per-configuration table to the SUMMARY so the bias is visible.

(3) Availability and containment

- [Blocker] Antigravity is not "reuse". The #82 runner has only Claude and Codex branches (`run.py:53-60`). The only existing agy wrapper in the repo passes `--dangerously-skip-permissions` (`.xyz/utils/py/agy-turn.py:384`), which the plan forbids (`:109`). A new adapter and a raw-event probe are required work; list them as Phase 2 items, not as reuse.
- [Should] Predeclare what counts as "Pro Medium unavailable". Line 105 leaves it to a probe. Suggested rule: CLI rejects or errors is unavailable; CLI accepts the flag and returned metadata shows a different route is unavailable; CLI accepts with no attestation is run as a requested-setting result, which is what line 105 already says for Haiku 4.5. Note the roster table is inconsistent about where effort lives (`:102` uses a flag, `:103` embeds it in the model id); the probe must record the exact form.
- [Nit] For the haiku45 lane the identity check in `run.py:87` cannot distinguish the main call from Claude Code's internal haiku-4-5 side call noted in `SUMMARY.md:81`. Disclose it.
- [Pass] Codex read-only sandbox is a containment aid and tool events are captured and disqualify (`run.py:92-96`, plan `:109`). Process-group termination is a correct addition since `subprocess.run` timeout does not kill the child tree.

(4) Uncertainty and winner rules

- [Should] Define missing cells for the bootstrap. Line 129 withholds winner claims for incomplete configurations but does not say how family means are formed when a pass is I. Rule: pairwise complete-case over passes present in both configurations, flagged exploratory; structurally invalid cells stay zero per line 107.
- [Should] Justify the 2/144 margin. Observed run-to-run spread in #82 was one point on /48, which is three points on /144. A margin below the noise floor does little; the Bonferroni lower-bound requirement already makes winner claims unlikely, so either raise the margin to 3 or 4 or say plainly it is a floor, not a practical-significance threshold.
- [Pass] Cluster bootstrap on families and Bonferroni over 28 pairs is simple and honest with 12 clusters. Coverage will be rough; the plan's framing of intervals as corpus sensitivity (`:129`) is the right caveat. Holm would be a free improvement but is not needed.

(5) Smallest corrections and cuts

Blockers: fix the grading-call count; make the one-label-per-variant Latin-square design explicit; list the Antigravity adapter and probe as new work with the bypass flag prohibited; define missing-cell handling in the bootstrap.

Worthwhile optional: pass-major schedule; canaries blind; unsupported-fact point rule; adjudication default; margin justification; per-reviewer table.

Cuts: reduce the legacy packet to one pass (saves 16 of 96 calls, the legacy diagnostic needs only a regression check); collapse the two three-round relays (`:53`, `:133`) to one round each after this consult. Out of scope: backend attestation of effort, Antigravity sandbox equivalence beyond one probe, any reviewer-bias study beyond the table.

**RECOMMENDATION**

Approve after the four blockers are written into Phase 2, keep all eight lanes as requested, and trim the legacy packet and relay rounds to spend the budget on fresh cells.
