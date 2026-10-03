# GPT 6.1 Sol Low — frozen Phase 2 retest

Tracking issue: [#13](https://github.com/HiQS-Labs/Needle-fork/issues/13). Predecessors: [#80](https://github.com/HiQS-Labs/Needle-fork/issues/80), [#81](https://github.com/HiQS-Labs/Needle-fork/issues/81). Run date: October 2, 2026 Pacific.

**Provisional result: 42/48 and 42/48 (87.50%, B) on the unchanged 12-case Git/PR analyst packet.** These are coordinator semantic scores, without the independent second review used by #80/#81. The deterministic grader confirms 11/12 exact verdicts, 12/12 valid evidence-ID sets, and zero critical false `SUPPORTED` verdicts in each run. Both runs mislabel G05 as `CONTRADICTED` where the frozen key says `UNKNOWN`: a passing CI check belongs to the old head, while no current-head check is observed. The answers correctly explain that evidence gap despite choosing the wrong label.

| Configuration | Scores /48 | Mean | Exact verdicts /12 | Valid evidence IDs /12 | Semantic /24 | Wall seconds |
|---|---:|---:|---:|---:|---:|---:|
| GPT 5.6 Luna Medium (historical) | 44 / 43 | 90.625% | 11 / 11 | 12 / 12 | 21 / 20 | 29.95 / 33.04 |
| GPT 6 Luna Medium (#80) | 43 / 41 | 87.50% | 12 / 10 | 12 / 12 | 19 / 19 | 29.10 / 25.16 |
| GPT 6 Luna High (#81) | 44 / 43 | 90.625% | 12 / 11 | 12 / 12 | 20 / 20 | 38.24 / 30.33 |
| **GPT 6.1 Sol Low (this run)** | **42 / 42** | **87.50%** | **11 / 11** | **12 / 12** | **19 / 19** | **46.93 / 43.35** |

The Sol scores are provisional because the semantic marks have one reviewer. The narrow comparison shows no observed score gain over GPT 6 Luna Medium under the conservative reading; it does not establish model superiority, a latency distribution, or production readiness. G05 sensitivity, excluding only its disputed verdict point, is **84/94 = 89.362%** for Sol versus 83/94 for Luna Medium, 86/94 for Luna High, and 87/94 historically. This does not replace the frozen official key. G02 run 2 could gain one point under a lenient reading of its argument-token verification; the conservative grade does not award it.

## Method and evidence

- Exactly two sequential fresh Codex CLI 0.159.2 calls requested `gpt-6.1-sol` with `model_reasoning_effort="low"`, read-only sandbox, ephemeral session, ignored user config, no tools, no retries, no answer repair, and no temperature override. A prior synthetic access probe succeeded with this CLI; the older 0.155.0 binary rejected the model under ChatGPT login. No independent backend model attestation was emitted.
- Original explicit prompt SHA-256: `1863e246efa8215d944cf4c8a49753a3b0b8710ad6a5ee1b3c1bbfe51f472003`; source packet: `dc19001fd5d1b4ad68f96516edb4c9b4538364689410450c5d33513e8ee5431b`. The candidate worked in a disposable Git checkout containing only `QUESTIONS.md` and `packet.json`; the key and old answers stayed outside it. [Frozen inputs and grader](../2026-09-29-gh81-phase2/) are reused byte for byte.
- Full raw answers, parsed answers, prompts, events, receipts and stderr are in [runs](runs/). [Review notes](review.json) explain every semantic deduction; [verification](verification.json) records input/control checks and preflight. Distinct threads, nonempty answers, raw/parsed equality and zero observed candidate tool events were checked. Original grader positive and six negative controls passed.
- Preflight `pytest -q -m 'not slow'` in an isolated Python 3.12.14 environment with declared train/test extras: **545 passed, 7 skipped, 11 deselected**. No product or release files changed.

## Limits and cost

All 12 fixtures were previously used for development. Two repetitions are not 24 independent held-out cases. Explicit prompt bytes match prior runs, but CLI/system/project context and cache behavior differ, so this is a historical fixture comparison, not a controlled model-only effect estimate. No independent semantic review was performed for this follow-up; the raw responses should be read before relying on a one-point difference.

The two runs reported 27,359 input tokens each, including 12,288 cached input tokens; output was 1,335 and 1,286 tokens (including 26 and 0 reported reasoning tokens). At the [official GPT 6.1 Sol standard API rates](https://developers.openai.com/api/docs/models/gpt-6.1-sol) checked October 2, $2/M uncached input, $0.10/M cached input, and $10/M output imply roughly **$0.0447 and $0.0442** in API-equivalent token cost. These Codex CLI calls did not emit an actual bill, and the estimate is not a subscription charge.

No Oracle next-action prediction, private-history evaluation, live hook latency, or deployment gate was measured. #13's separate clean-room qualification remains open.
