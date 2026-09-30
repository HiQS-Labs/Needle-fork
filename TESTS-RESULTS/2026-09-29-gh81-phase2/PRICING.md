# Full Phase 2 roster pricing — checked 2026-09-29 Pacific

USD per million text tokens. Triples below are **input / cached input / output**. Standard synchronous processing, short context, no tools, taxes, regional premiums or subscription allocations. Different effort settings share rates but can consume different token counts. Historical runs used CLI/Antigravity/OpenRouter/local routes; these reference prices are not historical bills.

| Model (tested configurations) | Standard, non-promotional reference | Current promotional rate / terms | Pricing route |
|---|---:|---|---|
| GPT 5.6 Luna (Medium) | $0.20 / $0.02 / $1.20 | No model-specific active token promotion identified | [OpenAI](https://developers.openai.com/api/docs/models/gpt-5.6-luna) |
| GPT 5.6 Terra (Low, Medium) | $2.00 / $0.20 / $12.00 | No model-specific active token promotion identified | [OpenAI](https://developers.openai.com/api/docs/models/gpt-5.6-terra) |
| GPT 6 Luna (Medium, High) | $0.10 / $0.01 / $0.50 | No model-specific active token promotion identified | [OpenAI](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| GPT 5.3 Codex Spark (High, XHigh) | $1.75 / $0.175 / $14.00 **gateway reference only** | No active token promotion identified for this gateway | [OpenCode Zen](https://opencode.ai/docs/en/zen/); direct OpenAI/Codex subscription per-token charge not established |
| Gemini 3.7 Flash (High, Antigravity) | $1.50 / $0.15 / $7.50 scheduled January 1, 2027 | **$0.75 / $0.075 / $3.75 through December 31, 2026** | [Google Developer API](https://ai.google.dev/gemini-api/docs/pricing); not Antigravity billing |
| Gemini 3.1 Pro (High, Antigravity) | $2.00 / $0.20 / $12.00 | No dated token promotion identified | [Google Developer API](https://ai.google.dev/gemini-api/docs/pricing), published Pro Preview reference; Antigravity alias equivalence not attested |
| Gemini 3.1 Flash-Lite (OpenRouter) | $0.25 / $0.025 / $1.50 | No dated token promotion identified | [OpenRouter](https://openrouter.ai/google/gemini-3.1-flash-lite), same published base rates; regional/Flex routes differ |
| Muse Spark 1.3 Contributor (High) | $0.10 / $0.002 / $0.20 | **Free on OpenCode Zen**, limited time, no end date published; distinct `muse-spark-1.3-contributor-free` route | [Meta](https://dev.meta.ai/docs/pricing-rate-limits), [Zen promotion](https://opencode.ai/docs/en/zen/) |
| Gemma 4 31B QAT (local, thinking off; unavailable in original run) | N/A — local inference | N/A | No API per-token bill for the tested local route; hardware/electricity cost not measured |
| Claude Sonnet 5.5 (Medium) | $2.00 / $0.20 / $10.00 | No active token promotion identified; these are permanent standard rates | [Anthropic](https://platform.claude.com/docs/en/models/sonnet-5-5/overview) |

## Terms that affect comparisons

OpenAI prompts above 272K tokens cost 2× input and 1.5× output for the whole request. Cache writes cost 1.25× uncached input: Luna 6 $0.125, Luna 5.6 $0.25, Terra $2.50 at short context. Regional/FedRAMP uplift is 10%. The separate GPT 5.6 **Sol** promotion does not establish a Luna/Terra promotion. Batch/Flex are processing tiers, not temporary promotions. [OpenAI pricing](https://developers.openai.com/api/docs/pricing).

Google Pro above 200K costs $4 input / $0.40 cached / $18 output; cache storage $4.50/MTok-hour. Flash 3.7 storage is $0.50/MTok-hour during the promotion, then $1.00. Flash-Lite storage $1.00. Eligible Google free tiers have quotas and different data-use terms; they are not a universal zero paid rate. Do not apply Google's promotion automatically to Antigravity or other gateways. [Google pricing](https://ai.google.dev/gemini-api/docs/pricing).

Contributor is a standing data-use discount: prompts/completions may train Meta models. Standard non-contributor Muse 1.3 is $1.25 / $0.15 / $4.25; it is a different contractual tier, not the non-promotional price of Contributor. Zen's free offering is a separate limited-time gateway promotion, with no published expiry on the reviewed page. [Meta pricing](https://dev.meta.ai/docs/pricing-rate-limits), [Zen](https://opencode.ai/docs/en/zen/).

Sonnet 5.5 cache writes are $2.50 (5 minutes) or $4 (1 hour). Batch halves input/output prices. Sonnet 5's former $2/$10 introductory offer became permanent August 10; the previously planned $3/$15 increase was cancelled. Sonnet 5.5 inherits $2/$10, so the advertised efficiency gain is fewer tokens/task, not a new token-price promotion. [Model docs](https://platform.claude.com/docs/en/models/sonnet-5-5/overview), [Sonnet 5 correction](https://www.anthropic.com/news/claude-sonnet-5), [5.5 announcement](https://www.anthropic.com/claude-sonnet-5-5).

No subscription usage is called free, and no API-equivalent estimate is presented as an invoice. “No promotion identified” is bounded to the linked public pages checked, not every partner, account credit, regional offer or private agreement. All rates can change.

## New-run telemetry and API-equivalent estimates

| Run | API-equivalent USD | Basis |
|---|---:|---|
| Luna High r1 | $0.00299106 | Standard short-context reference; total output already includes reasoning |
| Luna High r2 | $0.00279976 | Standard short-context reference; total output already includes reasoning |
| Sonnet Medium r1 | $0.08120620 | Matches CLI `total_cost_usd`; includes 1-hour cache creation at $4/MTok |
| Sonnet Medium r2 | $0.08054040 | Matches CLI `total_cost_usd`; includes 1-hour cache creation at $4/MTok |

These are reference estimates/CLI telemetry, **not verified charges**. Codex and Claude have different native context and cache accounting; the exact user prompt matches, their billable token totals do not. Sonnet reported zero thinking tokens; Medium was explicitly requested, which does not force a visible thinking budget.
