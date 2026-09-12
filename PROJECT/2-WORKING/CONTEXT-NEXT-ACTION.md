---
title: Context-aware next-action prediction
status: In progress
created: 2026-09-12
updated: 2026-09-12
owner: noelsaw1
goal: Measure whether observed task and tool-result context improves next-action prediction.
reversibility: Easy — offline experiment and scoped main commits only
---

# Context-aware next-action — #51

## Status

| What was just completed | What's next |
|---|---|
| Pivot pushed on main; converter and classifier implemented with witnessed leakage red controls. | Finish verification and run the frozen offline comparison once. |

Authority: [#51](https://github.com/HiQS-Labs/Needle-fork/issues/51), under
[#1](https://github.com/HiQS-Labs/Needle-fork/issues/1). This supersedes manual discovery #49,
stopped by the operator for time burden: one eligible request, zero ratings, no usefulness result.
It does not overturn #42/#48's failed gates. The target remains the next observed coding action:
`read`, `search`, `edit`, `run_tests`, `run_command`, or `git` — not purpose or generated commands.

## Bet and scope

Task text and the latest completed tool result may add signal missing from action history.
Alternative explanations: action persistence dominates; public issue-solving is too narrow;
bag-of-words cannot represent useful state. A failure of this probe does not distinguish all three.
Use [Nebius OpenHands trajectories](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories),
CC BY 4.0, revision `35455389ab51bf5e2306bfd436ef72d0f98bf882`.
Successful-only filtering is retained from #42, not a new contribution.

Grounding: [recon map](recon-context-next-action.md). Select existing converter, labels, baseline
and tests onto main; no whole-branch merge, MLX dependency, UI, manual annotation, synthesis,
private benchmark rerun, or held #43 change. Standard-library Naive Bayes is the smallest
dependency-free context probe, not a replacement production architecture.

## Execution and proof

1. Record pivot in #1/#49/#51, README, FINDINGS, collaborator briefing, ROADMAP and AGENTS;
   commit/push on main before the campaign. Preserve old results as dated history.
2. Add opt-in observation-aware extraction to the existing converter. Snapshot inputs before
   each single tool call using only already completed, ID-matched tool responses. Skip parallel
   calls and missing/ambiguous responses; controls clear history. Never include target arguments,
   target output, assistant reasoning, final patch or outcome flag in input features.
   -> Mutation controls must catch future-result leakage and broken tool-ID matching.
3. Freeze acquisition at offset 1000, at most 1000 source trajectories, 10 pages of 100,
   32 MiB per response and 320 MiB total; 30-second request timeout and 10-minute acquisition cap.
   Revision verified before and after; keep raw snapshot/hash private. First resolved trajectory
   per issue in source order (mark seen before extraction, no outcome-based reselection),
   hash issue ID into 80/20 train/eval before capping; at most 50 examples per issue, 10,000 train,
   3,000 eval. Remove exact shared feature-input signatures from train only, before fitting:
   canonical JSON of capped task, capped observation and action history, without target or IDs.
   Require >=1,000 train,
   >=200 eval and >=10 eval issues before fitting; report all six label counts and coverage.
4. Fit one fixed add-one multinomial Naive Bayes family with binary unigram features:
   last 12 positional action tokens; context variant adds task (600 characters) and latest
   observation (last 2000 characters), field-prefixed lowercase words, 20,000-token train-only
   vocabulary. Compare ordinary majority, repeat-last, Markov-1, phase backoff and action-only NB
   on exactly the same eval rows. Shuffle task/observation pairs among eval rows sharing the last
   action with seed 51; keep history/targets fixed and report actual changed-context coverage.
   -> No tuning after results; no future-action exclusion; no training on eval vocabulary.
5. Report pooled top-1, macro-F1 (six labels), per-label support/recall, ordinary action-change
   accuracy, and issue-macro accuracy; missing slices are null, never zero-row success.
   A follow-up is worth discussing only if context beats the strongest action-only comparator
   by >=5 percentage points overall and beats shuffled context by >=2 points, without reducing
   six-label macro-F1 versus action-only NB. This is a new resource rule, not #48's gate or
   significance. Low shuffle coverage (<50%) makes the context-control conclusion inconclusive.
6. Run focused tests with witnessed red controls and `pytest -q -m 'not slow'`; commit code before
   scoring. CPU only, no model download, <1 GiB estimated working set, 2 GiB address-space ceiling
   where supported and 2-minute fit/score time cap. Stop on a failed data/resource check.
   Retain receipt even for a no-go. Publish aggregate-only results and reconcile docs/issues,
   commit and push main. No automatic serving promotion regardless of score.

## QA checklist

- [x] Grounded paths, narrow blast radius, fixed hypothesis and limits documented before scoring.
- [x] Consult degraded: Codex answered; Agy timed out at 120 seconds. No cross-model agreement
  claimed. Codex found no blockers and requested deterministic issue selection and an explicit
  input-signature definition; both are now specified. Review assessed the plan, not working code.
- [x] Future leakage, tool matching, split isolation, train-only vocabulary, nonempty checks tested.
- [x] Future-output and tool-ID red controls witnessed and restored; non-slow suite passes
  (434 passed, 6 skipped before the final added CLI/control tests; final count in run receipt).
- [ ] Bounded real-data run completes or explicit refusal retained; receipt and docs agree.

Execution debugging uses debug-mantra. Reversibility Easy: scoped commits can be reverted without
changing source data or existing benchmark records. No change to training/export numerical contracts.

### Launch ledger

First launch at `3fe94b9` refused before acquisition/fit: this Mac rejects `RLIMIT_AS` (aliased
to RSS), including 256 MiB through 2 GiB and lowering both soft/hard limits. The conditional
"where supported" guard now records that platform limitation and uses 1 GiB measured-RSS
checkpoints in addition to fixed byte/example/vocabulary caps. Checkpoints are not a hard
allocation ceiling. Input features, sample selection and scoring gates are unchanged; no score
existed when this launch fix was made. Refusal retained under ignored data; new output directory
required for the next attempt. Regression covers disclosed degradation and the RSS tripwire.

Second launch retained all 1000 trajectories (285,443,921 bytes), then refused on an empty
`execute_bash` command. The retained snapshot contains two such calls in successful trajectories.
Before any fitting, clarify ambiguous-call handling: count and skip unlabelable calls and reset
history, never guess a target or bridge the gap. Legacy q1 still refuses. Reuse the exact snapshot
with `--source-run` only after comparison with its trusted original receipt hash; preserve both
refusal receipts and write to a fresh directory. Replacing both snapshot and trusted receipt is
outside this guard's trust boundary. Sample/feature/model/gate settings remain frozen.
