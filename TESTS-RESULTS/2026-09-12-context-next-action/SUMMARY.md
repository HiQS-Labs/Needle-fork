# Context-aware OpenHands next-action probe — #51

## Decision

**This fixed Naive Bayes context probe stops under its predeclared follow-up rule.** Aligned context
helped relative to the same classifier without text or with shuffled text, but did not beat the
strongest action-only comparator and slightly reduced macro-F1 versus action-only Naive Bayes.
This is evidence about a bounded representation/classifier, not proof that context or the dataset
cannot help. No usefulness, private-workflow transfer, significance or deployment claim.

## Source and frozen run

- Source: [nebius/SWE-rebench-openhands-trajectories](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories),
  CC BY 4.0, Nebius / Trofimova et al. (2025); revision `35455389ab51bf5e2306bfd436ef72d0f98bf882`.
- Protocol documented on main at `4f78a7d`, before implementation or scoring.
  Final scored code: `1bee790`. One actual fit/score run; no feature/threshold search.
- Offset 1000, 1000 source trajectories retained (285,443,921 bytes); 503 unresolved skipped,
  36 repeated issue/trajectory selections skipped. First resolved trajectory per issue, 80/20
  issue-hash split before caps, 50 examples/issue, 10,000 train and 3,000 evaluation maximum.
- Train: **10,000 actions / 224 issues**. Evaluation: **3,000 actions / 68 disjoint issues**,
  including **1,957 action changes**. Every label has support in both splits. Issue isolation and
  input-overlap checks passed; zero train input signatures required exclusion. Not repo-disjoint.
- Of the processed trajectories, 15,191 examples were eligible; caps excluded 2,191. Another 169
  source selections were skipped after their split filled. One unlabelable call in processed
  trajectories was counted/skipped with history reset. The full successful-source inventory had
  two empty shell calls; the other was outside the selected processing path.
- Input only: capped task text, last 12 completed actions, latest ID-matched tool observation.
  No target call arguments/results, assistant reasoning, final patch or outcome field in features.
  Resolved-only selection conditions the sample, not a feature proving optimal behavior.
- Fixed add-one multinomial Naive Bayes with binary unigram features; action vocabulary 72,
  context vocabulary 20,000 (training only). Test-time task/observation shuffle within last-action
  strata, seed 51; 2,994/3,000 contexts changed (**99.8%**). No retraining on shuffled evaluation.

## Same-row results

| Predictor | Correct / 3,000 | Top-1 | Macro-F1 (six labels) | Ordinary change accuracy | Issue-macro accuracy |
|---|---:|---:|---:|---:|---:|
| Majority | 876 | 29.20% | 0.0753 | 21.72% | 28.92% |
| Repeat-last | 1,043 | 34.77% | 0.3505 | 0.00% | 34.66% |
| Markov-1 | 1,470 | 49.00% | 0.4165 | 43.89% | 48.97% |
| Phase-backoff | 1,563 | **52.10%** | **0.4470** | 44.56% | **51.96%** |
| Action-only NB | 1,405 | 46.83% | 0.4204 | 39.86% | 46.99% |
| Context NB | 1,490 | 49.67% | 0.4072 | **48.95%** | 49.20% |
| Shuffled-context NB | 1,254 | 41.80% | 0.3421 | 40.52% | 41.78% |

Rule: context must gain >=5pp over the strongest action-only comparator, >=2pp over shuffled
context, and not reduce macro-F1 versus action-only NB. Actual margins: **-2.4333pp** overall
against phase-backoff, **+7.8667pp** against shuffle; macro-F1 **0.4072 < 0.4204**. No rounding,
post-hoc gate change or picking a favorable subgroup as the overall verdict.

| Label | Train support | Eval support | Context recall |
|---|---:|---:|---:|
| edit | 1,560 | 434 | 32.95% |
| git | 273 | 54 | 1.85% |
| read | 2,789 | 876 | 56.16% |
| run_command | 2,487 | 715 | 56.50% |
| run_tests | 1,149 | 357 | 65.55% |
| search | 1,742 | 564 | 38.30% |

The transition subset is diagnostic only, not a known live trigger. The context-shuffle contrast
shows sensitivity to aligned text on this sample, not causal user benefit. Single fixed model,
one shuffle, capped successful OpenHands trajectories, mechanically mapped labels and possible
shared-repository similarity limit generalization. Task and observation contributions are not
separated by this joint-text experiment. The larger/different sample cannot establish improvement
over #42's historical 100-row score by comparing percentages across experiments.

## Verification, resources and refusals

- **441 non-slow tests passed, 6 skipped, 11 deselected** before scoring. No build/finetune path
  changed, so slow training tests were not rerun. Focused tests cover timing, response matching,
  boundaries, deterministic split/selection, train-only vocabulary, shuffle, counters, and refusal.
- Mutation controls: future-output leakage and bypassed tool-ID matching each failed the targeted
  assertion, then passed after restoration. Mutations ran in memory, not in tracked source.
- Initial launch refused before download because macOS rejected RLIMIT_AS/RSS; reproduced at
  four sizes and with both soft/hard limits lowered. Second launch downloaded but refused on an
  empty command. Both refusal receipts retained privately; neither fitted or scored a model.
- Before scoring, documented explicit macOS degradation and count/skip/reset for ambiguous calls.
  Reused the hash-verified original snapshot; no sample/model/gate tuning. A substituted source
  with the same size is rejected. The retained receipt is the trust anchor, not self-authenticating.
- Completed snapshot extraction + fitting/scoring took **6.00 seconds**, peak RSS **283,885,568
  bytes (~271 MiB)**, CPU only. Download occurred in the prior launch. OS hard memory ceiling was
  unavailable on this Mac; fixed source/model caps and a 1 GiB RSS checkpoint tripwire remained.
  Checkpoints are not a hard allocation ceiling. No GPU or model download.
- Consult: Codex supplied a plan review and two incorporated determinism clarifications; Agy
  timed out. This is not cross-model agreement or code verification.

Public `metrics.json` retains pooled metrics only. Raw snapshots, example rows, source/code
hash receipts and manual-trial context remain ignored/private. PR #43 remains untouched.
