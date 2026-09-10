# Issue #25 correction audit and evaluation freeze

**Status: `INCOMPLETE`.** The targeted correction audit is complete and yields 19 conservative matched-target corrections. The evaluation audit remains blocked by its frozen 30-session floor, so no training can start.

## Verified result

- The correction population contains 20,181 reviewable calls after excluding 530 source-verified events with no command or path text. The deterministic exact allocator selected 400 rows across 254 sessions and 39 predicted-label strata; no session supplies more than 17 rows.
- Two blind auditors completed all 400 rows. They agreed with each other on 328/400 rows. A third blind reviewer adjudicated exactly the 72 disagreements.
- The adjudicated reference agrees with the mapper on 321/400 rows, or **80.25% on this deliberately session-spread sample**. This is not a population estimate, and no population confidence interval is reported because the session constraints give rows unequal inclusion probabilities.
- The 79 errors received complete, trace-grounded cause judgments. Every multi-action classification passes the deterministic requirement that the reference and another action both appear in the mapper's segment trace.
- Nineteen rows pass the conservative feedback filter: high-confidence reference, high-confidence cause, and a cause in shell visibility, inline semantics, or direct rule defect. Multi-action, taxonomy-boundary, reference-uncertain, and low-confidence rows remain excluded.
- The evaluation side has 2,709 reviewable calls across only 17 sessions. The sampler returned exit 2 and wrote no output because the frozen contract requires at least 30 sessions.

## Correction of superseded evidence

A prior constrained draw was reported as a stratified random sample with a 74.11% population estimate. Terra High review found that the session-constrained selection had unequal inclusion probabilities, so that estimate and interval were invalid. The same review supplied a small feasible case that the greedy allocator wrongly refused. The new exact allocator passes that red control, and targeted draws now fail closed by emitting sample statistics only. The prior result is withdrawn and excluded from current evidence.

## Reviewer limits

Cause assignments are reviewer judgments rather than proven causal effects. GPT-6 Astra Medium performed the cause review in a fresh context with the frozen taxonomy and deterministic segment traces. GPT-5.6 Luna High adjudicated auditor disagreements in a separate fresh context. A Gemini audit attempt timed out without an artifact and contributes no evidence. Low-confidence cause rows are excluded from the correction seed.

## Privacy and credential scan

Raw prompts, paths, commands, row IDs, and row-level judgments remain under ignored `data/`. Seven sample rows mention credential-related paths or environment-variable names. Pattern scans found no literal known token, private key, or sensitive assignment value; that scan does not prove arbitrary text contains no secret.

## Validation

- Focused corpus/audit suite: `61 passed`.
- Full non-slow suite: `342 passed, 6 skipped, 6 deselected`.
- PDDA: all checks passed; the optional LLM readiness review was not configured.
- Public receipt scan: all artifacts are nonempty; no raw row IDs, local paths, private-key markers, or known token patterns were found.

The tracked JSON files in this directory contain aggregate counts, label-pair metrics, definitions, and hashes only.
