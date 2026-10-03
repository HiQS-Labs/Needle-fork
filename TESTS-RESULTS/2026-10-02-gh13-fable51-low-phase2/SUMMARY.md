# Claude Fable 5.1 Low — frozen Phase 2 retest

Tracking issue: [#13](https://github.com/HiQS-Labs/Needle-fork/issues/13). Paired follow-up to [GPT 6.1 Sol Low](../2026-10-02-gh13-sol61-low-phase2/SUMMARY.md). Run date: October 2, 2026 Pacific.

**Provisional result: 43/48 and 42/48 (88.542%, B)** on the unchanged 12-case Git/PR analyst packet. These coordinator semantic scores have not had the independent second review used by #80/#81. The fixed grader confirms 11/12 exact verdicts, 12/12 valid evidence-ID sets, and zero critical false `SUPPORTED` verdicts in each run. Both Fable runs, like both Sol runs, label G05 `CONTRADICTED` instead of the frozen `UNKNOWN`: a passing CI check belongs to an old head and no current-head check is observed. Their prose correctly identifies the missing current-head check.

| Configuration | Scores /48 | Mean | Verdicts /12 | Valid evidence IDs /12 | Semantic /24 | Wall seconds |
|---|---:|---:|---:|---:|---:|---:|
| GPT 6.1 Sol Low (paired run) | 42 / 42 | 87.50% | 11 / 11 | 12 / 12 | 19 / 19 | 46.93 / 43.35 |
| **Claude Fable 5.1 Low** | **43 / 42** | **88.542%** | **11 / 11** | **12 / 12** | **20 / 19** | **45.57 / 45.13** |

Fable's one-point edge is a provisional semantic judgment on repeated development fixtures. It does not establish a general quality or speed advantage. Both models miss the explicit issue #2 blocker in G01, the decisive `echo pytest` argument-text distinction in G02, and the primary-checkout/AgentChorus scope in G03. Fable handles the effective G07 cache revert and its follow-up more fully; run 2 omits PR10's open-state qualification in G04. [Per-case review](review.json) records the deductions. Excluding only G05's disputed verdict point yields **85/94 = 90.426%** for Fable versus **84/94 = 89.362%** for Sol; the frozen official key remains unchanged.

## Method and evidence

- Two sequential fresh calls used Claude Code 2.1.288 via `npx`, requesting `claude-fable-5-1` and `--effort low`. Tool and MCP lists were empty, hooks/skills disabled, sessions not persisted, and no candidate tool use or spawned agent was observed. There were no retries, answer repairs, temperature overrides, or prompt changes. Returned message metadata names `claude-fable-5-1`; it is not independent backend attestation.
- The explicit prompt SHA-256 matches the Sol and earlier Phase 2 runs: `1863e246efa8215d944cf4c8a49753a3b0b8710ad6a5ee1b3c1bbfe51f472003`. Packet SHA-256: `dc19001fd5d1b4ad68f96516edb4c9b4538364689410450c5d33513e8ee5431b`. Candidate cwd was a disposable Git checkout containing only `QUESTIONS.md` and `packet.json`; the frozen key and prior responses stayed outside. [Original inputs and grader](../2026-09-29-gh81-phase2/) were reused byte for byte.
- [Raw answers, events, prompts and receipts](runs/) retain the two distinct sessions. [Verification](verification.json) confirms nonempty answers, raw/parsed equality, input hashes, zero observed candidate tool events, and the original grader's positive plus six negative controls. Repo preflight with Python 3.12.14 and `NEEDLE_TELEMETRY=0`: **545 passed, 7 skipped, 11 deselected**.

## Cost and limits

Claude Code reported **$0.48363275** for run 1 (16,539 one-hour cache-write, 531 cache-read, 3,054 output tokens) and **$0.1530875** for run 2 (17,070 cache-read, 2,976 output tokens); total **$0.63672025** in CLI cost telemetry, not a verified invoice. Output includes 718/724 reported thinking tokens. The [official effort guide](https://platform.claude.com/docs/en/build-with-claude/effort) lists low as supported, and the [model page](https://platform.claude.com/docs/en/models/fable-5-1/overview) lists API prices. Sol's earlier figure was an API-equivalent estimate from Codex usage, so these cost routes are not directly comparable.

Two calls on 12 previously seen fixtures are not 24 independent held-out cases. Claude Code and Codex have different system context, tokenization and cache behavior. No independent semantic review was performed for this follow-up; a one-point score difference is especially sensitive to that limitation. No Oracle next-action prediction, private-history evaluation, live serving latency, or deployment gate was measured. #13's separate clean-room qualification remains open.
