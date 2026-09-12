# Seven-model next-action panel (#52)

Fable leads this exploratory sample at **18/30 (60.0%)**, versus **14/30 (46.7%)**
for the strongest simple baseline, phase-backoff. This is four more correct rows,
not a demonstrated general advantage or a milestone pass. Existing #51 gates stand.

## Results

| Predictor | Correct | Accuracy | Six-label macro-F1 | Change-only accuracy |
|---|---:|---:|---:|---:|
| fable | 18/30 | 60.0% | 0.466 | 52.4% |
| glm | 15/30 | 50.0% | 0.346 | 42.9% |
| astra | 14/30 | 46.7% | 0.405 | 47.6% |
| gemini | 14/30 | 46.7% | 0.434 | 47.6% |
| deepseek | 11/30 | 36.7% | 0.246 | 38.1% |
| qwen | 12/30 | 40.0% | 0.333 | 38.1% |
| tencent | 9/30 | 30.0% | 0.283 | 28.6% |
| baseline_majority | 7/30 | 23.3% | 0.063 | 23.8% |
| baseline_repeat_last | 9/30 | 30.0% | 0.224 | 0.0% |
| baseline_markov_1 | 12/30 | 40.0% | 0.263 | 33.3% |
| baseline_phase_backoff | 14/30 | 46.7% | 0.254 | 33.3% |

All predictors scored the same 30 cases from 30 issues. The action-change slice has
21 rows and uses ordinary predictions, without revealing that a switch will occur.
The four baselines were fitted on the unchanged, disjoint 10,000-row/224-issue
training partition; their original 3,000-row scores were independently replayed
and matched the #51 receipt before scoring this subset. No neural training or
context-NB rerun took place.

## Coverage and shared mistakes

Actual label support: run_command 10, run_tests 9, read 7, search 3, edit 1, git 0.
Six-label macro-F1 includes a zero contribution for the unsupported git class;
there is no evidence here about predicting true git actions and very little about
edits. Do not extrapolate this ranking to all six labels or operator governance.

Seven models agreed on seven cases; six of those were correct. All seven missed
nine cases. At least one model was correct on 21/30, which is an oracle upper
bound on these recorded answers, NOT a deployable ensemble score. No voting or
tie-breaking rule was predeclared or promoted. The unanimous error followed an
error-bearing observation, where every model predicted edit but the recorded next
label was run_tests. That disagreement is not proof the recorded action was best.

The latest observation is truncated, sometimes to generic success boilerplate;
tasks are capped at 600 characters and history at 12 broad labels. The code maps
ad-hoc Python verification scripts to run_command, but named tests/builds/linters
to run_tests. That distinction may differ from a model's semantic notion of test
intent. These are limitations to audit, not permission to relabel this scored set.

## Protocol, evidence, and limits

- Selection: deterministic, target-blind selection of 30 issues and one retained
  row per issue, seed needle-panel-v1-30. Inputs, targets, source hash and selection
  were verified against the frozen manifest and source. Seven responses were locked
  before scoring. See metrics.json for aggregate scores and input/code hashes.
- Public source: Nebius SWE-rebench-openhands-trajectories, revision
  35455389ab51bf5e2306bfd436ef72d0f98bf882, CC BY 4.0. Successful public coding-agent
  trajectories; not the operator's feedback CSV or personal preferences.
- The sample reuses #51 development examples. Seven models are not 210 independent
  observations. Selecting the best of seven on 30 rows creates winner-selection bias.
  Neither statistical superiority nor human usefulness is established.
- Different delivery paths: Fable/GLM interactive AgentChorus; Astra/Gemini through
  the consult harness; DeepSeek/Qwen/Tencent through Aider/OpenRouter. Model/effort
  attestation varies; GLM's Max setting is not independently attested. This is not
  a controlled vendor leaderboard.
- Collection cost reported by Aider: DeepSeek $0.04, Qwen $0.14, Tencent $0.07.
  Subscription lanes have no comparable cost accounting; $0.25 is not total cost.
- Reproduce with the retained private data using
  `python TESTS-RESULTS/2026-09-12-next-action-panel/score.py`. Its stdout includes
  per-case inputs: save it ONLY under ignored data/. Public metrics omit raw cases.
- Verification: 441 non-slow tests passed, 6 skipped, 11 deselected. Scorer checks
  reject empty/missing/duplicate/invalid labels; a perfect-score fixture becomes
  0% under wrong predictions; confusion-matrix arithmetic independently agrees.
  Prediction-permutation expected accuracies are analytic null diagnostics in
  metrics.json, not significance tests or context ablations.

## Next-step review

The operator-requested relay-xyz review completed through its documented one-shot
consult path, using Agy `gemini-3.1-pro-high`, high effort. One advisory answer,
zero failed workers; this was not an iterative artifact-approval relay. The raw
review is retained under ignored `data/next-action-panel-v1/consult-runs/`.
Worker and consult harness suites each passed 62/62; the vendored full-validator
script is absent, so full harness validation is not claimed.

Adopted: pause model calls and training; inspect the nine shared misses in the raw
source before deciding what to change. [#53](https://github.com/HiQS-Labs/Needle-fork/issues/53)
tracks those nine events plus three correctly predicted controls, a bounded
12-event local audit with no manual operator ratings. It has not started.

Review qualifications:

- The reviewer called fixed-denominator macro-F1 a blocker. Not adopted: the
  frozen six-label convention is explicit and applied to everyone. Uniformly
  omitting unsupported Git would multiply every score by 6/5 without changing
  the ranking. Omitting classes based on each model's predictions would instead
  introduce different denominators. Coverage limitations remain prominent.
- The review's assertion that Fable's lead *is* a statistical artifact is not
  established. Winner-selection bias is a limitation, not a demonstrated cause.
- Disagreement does not prove noisy labels or that models chose better actions.
  The audit must distinguish actual mapping defects, intentional taxonomy
  boundaries, insufficient visible context, and behavioral ambiguity; unresolved
  cases may remain unresolved. Do not relabel merely to agree with model votes.
- There are nine all-model misses, not the review's ten: the one unanimous error
  is already included in those nine.

No old gate is changed, no model is promoted, and PR #43 remains held. Any mapper
fix or subsequent experiment needs its own scope and separately versioned evidence.
