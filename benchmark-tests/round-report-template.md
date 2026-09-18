# Round {{ROUND_ID}} — {{MODEL_NAME}} ({{DATE}})

Template only: fill from retained primitives; do not publish unresolved placeholders.
The paired task/question manifests and protocol pins must be independently verified.

## 1. Configuration snapshot
- Protocol: {{PROTOCOL_ID}}, frozen at {{PROTOCOL_SHA}}
- Terminal-Bench: {{TB_DATASET}} @ {{TB_VERSION}}, harness commit {{HARNESS_COMMIT}}
- GPQA Diamond: {{GPQA_N}} questions (planned full Diamond: 198), zero-shot CoT, shuffle seed {{SHUFFLE_SEED}}
- Backend: {{BACKEND}} {{BACKEND_VERSION}}, quant {{QUANT}}, ctx {{CTX}}, temp {{TEMP}}
- Hardware: {{MACHINE}}

## 2. Terminal-Bench results
| Metric | Value |
|---|---|
| Tasks run | {{N_TASKS}} |
| Attempts/task | {{N_ATTEMPTS}} |
| Accuracy (trial-level) | {{TB_ACC}} |
| pass^4 (primary) | {{TB_PASS4}} |
| Median wall time/attempt | {{TB_MEDIAN_SEC}} s |
| Total output tokens | {{TB_TOKENS}} |
| Infra failures excluded | {{TB_INFRA_FAILS}} |

### Findings
- **What worked:** {{TB_WINS}}
- **Failure modes:** {{TB_FAILURE_MODES}} — categorize: tool misuse / environment mismatch / timeout / wrong-but-plausible edit / gave up early
- **Notable tasks:** {{TB_NOTABLE_TASKS}}

## 3. GPQA Diamond results
| Metric | Value |
|---|---|
| Questions | {{GPQA_N}} |
| Correct | {{GPQA_CORRECT}} |
| No-answer (extraction failed) | {{GPQA_NO_ANSWER}} |
| Accuracy (overall) | {{GPQA_ACC}} |
| Accuracy — physics | {{GPQA_PHYS}} |
| Accuracy — chemistry | {{GPQA_CHEM}} |
| Accuracy — biology | {{GPQA_BIO}} |
| Median tokens/question | {{GPQA_MEDIAN_TOKENS}} |

### Findings
- **Per-domain notes:** {{GPQA_DOMAIN_NOTES}}
- **No-answer rate context:** extraction failures should be treated as model failures (they count against accuracy), but log separately if >2% to check the prompt template

## 4. Meta grade
| Metric | Value |
|---|---|
| TB pass^4 | {{TB_PASS4}} |
| GPQA accuracy | {{GPQA_ACC}} |
| **Meta grade (geometric mean)** | **{{META_GRADE}}** |
| TB z-score vs round cohort | {{TB_Z}} |
| GPQA z-score vs round cohort | {{GPQA_Z}} |

**Interpretation:** {{META_INTERPRETATION}} — note whether the model is lopsided (high on one benchmark, low on the other). A lopsided profile with a decent meta grade still predicts uneven agent behavior.

## 5. Provenance & reproducibility
- Config file: results/{{ROUND_ID}}/eval-config.yaml (verbatim copy of frozen protocol + model row)
- Raw artifacts: results/{{ROUND_ID}}/{{MODEL_SLUG}}/tb-trials/, gpqa-responses/
- Exact command lines: results/{{ROUND_ID}}/{{MODEL_SLUG}}/commands.txt
- Incidents: results/{{ROUND_ID}}/incidents.log
- Hashed ordered task/question manifests: {{MANIFESTS}}
- Limitations, exclusions and deviations: {{LIMITATIONS}}

## 6. Comparison table (fills in as models complete)
| Model | TB pass^4 | GPQA acc | Meta grade | Notes |
|---|---|---|---|---|
| {{PREVIOUS_MODEL_ROWS}} | | | | |
