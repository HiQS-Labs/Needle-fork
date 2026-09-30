# Sonnet 5.5 and GPT 6 Luna High — Phase 2 results

Canonical issue: [#81](https://github.com/HiQS-Labs/Needle-fork/issues/81). Predecessors [#80](https://github.com/HiQS-Labs/Needle-fork/issues/80) and [#13](https://github.com/HiQS-Labs/Needle-fork/issues/13). Run date September 29 Pacific / September 30 UTC, 2026.

**Luna High recovered the Medium shortfall on this packet, matching historical GPT 5.6 Luna; Sonnet 5.5 did not outperform either Luna baseline consistently.** Two runs each, same 12 cases, original 48-point rubric. Final grading includes coordinator adjudication against historical calibration; independent literal-key scores are lower and preserved.

| Configuration | Run scores /48 | Mean | Grade | Verdicts /12 | Evidence /12 | Semantics /24 | Request wall seconds |
|---|---|---:|---|---|---|---|---|
| GPT 5.6 Luna Medium (historical) | 44 / 43 | 90.625% | B | 11 / 11 | 12 / 12 | 21 / 20 | 29.95 / 33.04 |
| GPT 6 Luna Medium (#80) | 43 / 41 | 87.50% | B | 12 / 10 | 12 / 12 | 19 / 19 | 29.10 / 25.16 |
| **GPT 6 Luna High** | **44 / 43** | **90.625%** | **B** | 12 / 11 | 12 / 12 | 20 / 20 | 38.24 / 30.33 |
| **Claude Sonnet 5.5 Medium** | **44 / 40** | **87.50%** | **B** | 12 / 10 | 12 / 12 | 20 / 18 | 17.49 / 20.95 |

No critical false SUPPORTED verdicts, executed/claimed mutation, or observed candidate tool use. All four fresh calls delivered structurally valid 12-case answers. Sonnet returned model metadata `claude-sonnet-5-5`; Luna selection was explicit `gpt-6-luna`. No independent backend attestation.

## What changed

Luna High gained **3.125 percentage points over Luna Medium**, tying GPT 5.6 Luna on total score. It gave better focused taxonomy verification and kept deployment uncertainty UNKNOWN in both runs. It still omitted the specific planning blocker/retired CPU direction and the primary-checkout/AgentChorus PR scope. G05 remains unstable: UNKNOWN in run 1, CONTRADICTED in run 2. High reported 475/326 reasoning tokens versus zero in the earlier Medium receipts; wall time increased. Two runs cannot establish a robust general improvement or causal effort effect.

Sonnet was faster in these two requests and gave stronger concrete auth-change/producer-consumer analysis, but run 2 lost points for omitted open PR state, premature cache reenablement advice, and wrong CI/deployment uncertainty labels. Its generic descriptions still missed requested details on G01–G03. Its no-tool advice was not executed. Scores span 44 to 40; it is not a consistent quality upgrade in this small sample.

## Per-case totals

| Case | Luna High r1 | Luna High r2 | Sonnet r1 | Sonnet r2 |
|---|---:|---:|---:|---:|
| G01 | 2 | 2 | 2 | 2 |
| G02 | 3 | 3 | 3 | 3 |
| G03 | 3 | 3 | 3 | 3 |
| G04 | 4 | 4 | 4 | 3 |
| G05 | 4 | 3 | 4 | 3 |
| G06 | 4 | 4 | 4 | 4 |
| G07 | 4 | 4 | 4 | 3 |
| G08 | 4 | 4 | 4 | 4 |
| G09 | 4 | 4 | 4 | 4 |
| G10 | 4 | 4 | 4 | 4 |
| G11 | 4 | 4 | 4 | 4 |
| G12 | 4 | 4 | 4 | 3 |

## Scoring limitations and sensitivity

[Independent review](review/independent.json) scored A/B/C/D **38/37/41/38**; the coordinator initially scored **44/43/45/41**, then accepted two additional losses for final **44/43/44/40**. [Final adjudication](review/final.json) records every disagreement. Literal receipt wording, explicit old-false computation, and mandatory revert investigation when no reenablement is proposed were not retroactively added as new historical penalties. This is judgment-based grading; the B grades are reconciled grades, not unanimous agreement. The independent literal-key High mean is below the prior independent Medium review (40/36 versus 38/37), so **do not claim reviewer-independent improvement**; comparisons depend on consistent final calibration.

G05's frozen key says UNKNOWN where many historical responses chose CONTRADICTED. Removing only that verdict point: historical GPT 5.6 Luna **87/94 = 92.553%**, GPT 6 Medium **83/94 = 88.298%**, Luna High **86/94 = 91.489%**, Sonnet **83/94 = 88.298%**. Thus High improves over Medium but no longer exactly ties historical Luna under this sensitivity; Sonnet still ties Medium. Do not relabel the key after seeing outputs.

## Historical full roster

No historical configuration was rerun except the newly requested Luna High; dates and harnesses differ.

| Historical Phase 2 configuration | Scores /48 | Mean | Grade |
|---|---|---:|---|
| Luna 5.6 Medium | 44 / 43 | 90.625% | B |
| Terra 5.6 Medium | 43 / 44 | 90.625% | B |
| Terra 5.6 Low | 44 / 44 | 91.667% | B |
| Codex Spark High | 42 / 44 | 89.583% | B |
| Codex Spark XHigh | 44 / 40 | 87.50% | B |
| Gemini 3.7 Flash High / Agy | 44 / 45 | 92.708% | B |
| Gemini 3.1 Pro High / Agy | 43 / 40 | 86.458% | B |
| Gemini 3.1 Flash-Lite / OpenRouter | 40 / 41 | 84.375% | C |
| Muse Spark 1.3 Contributor High | 42 / 41 | 86.458% | B |
| Gemma 4 31B QAT off / local | unavailable | — | I |

[Full current standard/promotional pricing table](PRICING.md) includes exact routes, cache rates, dates, caveats and new-run API-equivalent estimates. Sonnet's CLI estimates total $0.1617466; Luna High's API-equivalent total $0.00579082. These are not verified charges, and native context/cache behavior differs.

## Reproduction and verification

Frozen before inference at 9dd1339; completed preflight captured at 5c9d089. 545 tests passed, 7 skipped, 11 deselected. Original grader positive/six negative controls passed. Four input hashes match #80, explicit prompt SHA-256 `1863e246efa8215d944cf4c8a49753a3b0b8710ad6a5ee1b3c1bbfe51f472003`, four distinct sessions, 48 nonempty assessments, raw/parsed equality and zero observed tool events verified. See [protocol](PROTOCOL.md), [input manifest](input-manifest.json), [receipts](verification/run-checks.json) and raw per-lane files. No production/runtime/numerics/release changes.

Candidates ran in disposable two-file checkouts; key, prior scores and prior outputs stayed outside. Claude tools/MCP/skills were empty, hooks disabled; built-in agents-md/telemetry plugins were still listed. Native system prompts/tokenizers/caching differ, and the historical project context differs. Medium/High names do not imply equal vendor compute. Sonnet reported zero thinking tokens despite requested Medium. No retry, fallback, answer repair or temperature override. Review was a separate anonymized single-model advisory read via the existing relay-xyz consult transport, followed by coordinator adjudication; not a cross-model consensus panel.
