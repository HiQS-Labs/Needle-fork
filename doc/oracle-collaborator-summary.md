# Needle Oracle: collaborator briefing

## TLDR

We’re exploring whether a tiny local model can suggest useful next steps during software work, including testing, Git actions, and project governance, cheaply enough to run alongside a larger coding assistant. We have built and exercised the training/export pipeline, assembled private activity traces, and tested both model-based and simple statistical predictors. The engineering path works, but useful recommendations remain unproven: label noise, a mismatch between training and native serving, and poor transfer from public coding-agent data have limited results.

Private-trained predictors and a context-aware OpenHands text classifier missed their gates. A seven-model quiz gave Fable 60.0% versus a 46.7% simple baseline on 30 public examples—not a milestone pass. The subsequent source audit found two action-classification defects, coarse-label ambiguities and context loss. Next is a narrow mapper correction before more model investment. The manual trial stopped for time burden with no ratings; usefulness and deployment readiness remain unproven.

## The story and evidence

| Attempt | What we learned | Consequence |
|---|---|---|
| A 44-action SDLC Oracle, including project-governance actions | We built the taxonomy, trace extraction, and an MLX training/export path. Early ranking scores did not establish useful native behavior; the native engine retrieved only five of 44 declared tools in the tested contract. | Separate training, ranking, and actual serving claims. [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1), [#5](https://github.com/HiQS-Labs/Needle-fork/issues/5), [#12](https://github.com/HiQS-Labs/Needle-fork/issues/12). |
| Auditing the training labels | A 399-row stratified audit estimated 77.84% population-weighted correctness (72.30–83.38% sampling interval). Coverage alone had hidden incorrect labels. | Improve source qualification; do not treat mechanically assigned labels as human ground truth. A stricter fresh evaluation remains capacity-limited to 541 of 1,000 required rows. [#25](https://github.com/HiQS-Labs/Needle-fork/issues/25), [#37](https://github.com/HiQS-Labs/Needle-fork/issues/37). |
| A narrower, six-action OpenHands pilot | With 500 training actions, LoRA achieved 27% top-1 on 100 development actions versus 37% for a first-order transition table. | Stop this generative pilot before a larger run or synthesis. [PR #42](https://github.com/HiQS-Labs/Needle-fork/pull/42). |
| A phase-aware transition table | It reached 42% on that development set, but only 25.23% on 23,442 eligible private actions from 63 sessions. The OpenHands-trained first-order table scored 28.78%; repeat-last scored 43.52%. | Public-source transition patterns transferred poorly. This does not settle whether fitting on our own training sessions would work. [Result](https://github.com/HiQS-Labs/Needle-fork/issues/1#issuecomment-5639743768). |
| Work-purpose classification, a separate side experiment | Frozen ModernBERT features reached 57.5% purpose accuracy on 40 records versus 50% TF-IDF and 42.5% majority; TF-IDF had better purpose macro-F1. Area classification and rejection policies remained inadequate. | Limited signal, no deployment qualification; this is classification of work, not prediction of the next action. [#31](https://github.com/HiQS-Labs/Needle-fork/issues/31). |
| External data and targeted augmentation | TAWOS did not cover the full eight-purpose taxonomy. A separate PR implements grounded, training-only augmentation tooling, with no measured model gain yet. | Volume alone does not solve domain and label mismatch. [#35](https://github.com/HiQS-Labs/Needle-fork/issues/35), [#41](https://github.com/HiQS-Labs/Needle-fork/issues/41), [PR #43](https://github.com/HiQS-Labs/Needle-fork/pull/43). |

## Current result — source audit (#53) completed

All 12 selected events align with retained source and call/result chronology. Two
concrete classification defects were found: unittest suite execution maps to
run_command, while a pytest version query maps to run_tests. Directory-view and
ad-hoc-script labels have semantic boundaries, and some context is discarded.
These findings do not explain every miss or estimate population label quality.
[Audit receipt](../TESTS-RESULTS/2026-09-12-panel-source-audit/SUMMARY.md).

Next is [#56](https://github.com/HiQS-Labs/Needle-fork/issues/56), a separately scoped
mapper correction, not implemented in the audit. No new training or model calls;
prior scores/gates stay frozen. MiniMax's separately requested addition scored
10/30 (33.3%); [#54](https://github.com/HiQS-Labs/Needle-fork/issues/54#issuecomment-5644221616)
retains that result and the narrow five-Chinese-model impressions.

## Previous result — seven-model panel (#52) scored and reviewed

Seven models answered the same 30 cases before targets were disclosed: Fable 18/30,
GLM 15/30, Astra and Gemini Flash 14/30, Qwen 12/30, DeepSeek 11/30, Tencent 9/30.
Phase-backoff scored 14/30. This reused development sample has no true Git actions
and one edit; selecting the best of seven is not evidence of general superiority.
[Receipt and Gemini 3.1 Pro review reconciliation](../TESTS-RESULTS/2026-09-12-next-action-panel/SUMMARY.md).

At that point [#53](https://github.com/HiQS-Labs/Needle-fork/issues/53) proposed auditing the nine
all-model misses plus three controls against retained raw trajectories. Distinguish
mapping defects from intentional taxonomy boundaries, missing context and behavioral
ambiguity; do not change labels merely to agree with models. No manual ratings,
new model calls or training were needed for this audit. It is now completed above.

## Previous result — context-aware pivot (#51) completed

See the [completed protocol](../PROJECT/3-COMPLETED/CONTEXT-NEXT-ACTION.md) and [receipt](../TESTS-RESULTS/2026-09-12-context-next-action/SUMMARY.md). One run fitted on 10,000 actions / 224 issues and evaluated on 3,000 actions / 68 other issues. Context beat shuffled context by 7.87pp but trailed phase-backoff by 2.43pp and reduced macro-F1 versus action-only NB. The fixed follow-up rule failed; any new model/representation experiment needs a separate scope decision. Main-first commits/pushes are now the operator's default; no new experiment PR without a real isolation need. PR #43 stays held.

Manual #49 ended with one eligible request and zero ratings, so it supplies no usefulness rate. The old private-trained round below completed and failed both gates; retained as history, not an instruction to rerun. [Receipt](https://github.com/HiQS-Labs/Needle-fork/blob/7f521b449c9d0f8351fdfc32c8c7180a44cbcf9f/TESTS-RESULTS/2026-09-11-private-transitions/SUMMARY.md).

## Previous milestone — superseded plan, now completed

1. Fit unchanged first-order and phase-aware transition predictors on the private training partition, proving session separation from evaluation.
2. Score once on the existing 63-session evaluation partition. The same model family must beat repeat-last by five percentage points overall (approximately 48.52%) and a training-derived destination baseline by ten points on action-change rows when the previous action is excluded.
3. Also report ordinary predictions on action-change rows and per-session distributions. The excluded-previous score is conditional destination accuracy: it does not show that a live system can detect when a switch will happen.
4. If both gates pass, design a small prospective serving experiment. If only one passes, consider a separately scoped experiment on action-run endings. If neither passes, stop investment in these two models at this representation.

Budget: standard-library tooling, one engineer-hour, no feature search. The evaluation partition has already informed decisions: it is disjoint from fitting but is reused development evidence, not fresh confirmation. Scores measure agreement with recorded labels, not human acceptance or whether an action was advisable. The broad private-label projection also limits interpretation. No result here proves next-action prediction impossible.

## Where the project lives

- Overall goals and cross-project arc: [XYZ-forge #467](https://github.com/HiQS-Labs/XYZ-forge/issues/467).
- Needle implementation and experiment history: [Needle-fork #1](https://github.com/HiQS-Labs/Needle-fork/issues/1).
- Supporting investigation log: [FINDINGS.md](../FINDINGS.md); measurements live in dated `TESTS-RESULTS/` receipts and linked issues.

Status reconciled 2026-09-12 through source audit #53 and follow-up #56. Experimental code and receipts in PR #42 are on its branch; they are not all present on `main`. The earlier private-trained milestone interpretation incorporated Astra/Fable discussion #743999; its failed gates remain unchanged.
