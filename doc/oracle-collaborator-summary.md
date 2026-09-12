# Needle Oracle: collaborator briefing

## TLDR

We’re exploring whether a tiny local model can suggest useful next steps during software work, including testing, Git actions, and project governance, cheaply enough to run alongside a larger coding assistant. We have built and exercised the training/export pipeline, assembled private activity traces, and tested both model-based and simple statistical predictors. The engineering path works, but useful recommendations remain unproven: label noise, a mismatch between training and native serving, and poor transfer from public coding-agent data have limited results.

The private-trained comparison also missed its gates: phase-backoff reached 45.73% overall versus 43.52% repeat-last. Our next experiment keeps six next-action labels but adds task text and the latest completed tool result from OpenHands trajectories. It is bounded, automatic and CPU-only; the manual usefulness trial stopped for time burden with no ratings. We are testing prediction, not claiming recommendations or deployment readiness.

## The story and evidence

| Attempt | What we learned | Consequence |
|---|---|---|
| A 44-action SDLC Oracle, including project-governance actions | We built the taxonomy, trace extraction, and an MLX training/export path. Early ranking scores did not establish useful native behavior; the native engine retrieved only five of 44 declared tools in the tested contract. | Separate training, ranking, and actual serving claims. [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1), [#5](https://github.com/HiQS-Labs/Needle-fork/issues/5), [#12](https://github.com/HiQS-Labs/Needle-fork/issues/12). |
| Auditing the training labels | A 399-row stratified audit estimated 77.84% population-weighted correctness (72.30–83.38% sampling interval). Coverage alone had hidden incorrect labels. | Improve source qualification; do not treat mechanically assigned labels as human ground truth. A stricter fresh evaluation remains capacity-limited to 541 of 1,000 required rows. [#25](https://github.com/HiQS-Labs/Needle-fork/issues/25), [#37](https://github.com/HiQS-Labs/Needle-fork/issues/37). |
| A narrower, six-action OpenHands pilot | With 500 training actions, LoRA achieved 27% top-1 on 100 development actions versus 37% for a first-order transition table. | Stop this generative pilot before a larger run or synthesis. [PR #42](https://github.com/HiQS-Labs/Needle-fork/pull/42). |
| A phase-aware transition table | It reached 42% on that development set, but only 25.23% on 23,442 eligible private actions from 63 sessions. The OpenHands-trained first-order table scored 28.78%; repeat-last scored 43.52%. | Public-source transition patterns transferred poorly. This does not settle whether fitting on our own training sessions would work. [Result](https://github.com/HiQS-Labs/Needle-fork/issues/1#issuecomment-5639743768). |
| Work-purpose classification, a separate side experiment | Frozen ModernBERT features reached 57.5% purpose accuracy on 40 records versus 50% TF-IDF and 42.5% majority; TF-IDF had better purpose macro-F1. Area classification and rejection policies remained inadequate. | Limited signal, no deployment qualification; this is classification of work, not prediction of the next action. [#31](https://github.com/HiQS-Labs/Needle-fork/issues/31). |
| External data and targeted augmentation | TAWOS did not cover the full eight-purpose taxonomy. A separate PR implements grounded, training-only augmentation tooling, with no measured model gain yet. | Volume alone does not solve domain and label mismatch. [#35](https://github.com/HiQS-Labs/Needle-fork/issues/35), [#41](https://github.com/HiQS-Labs/Needle-fork/issues/41), [PR #43](https://github.com/HiQS-Labs/Needle-fork/pull/43). |

## Current milestone — context-aware pivot (#51)

See the [frozen protocol](../PROJECT/2-WORKING/CONTEXT-NEXT-ACTION.md) and [#51](https://github.com/HiQS-Labs/Needle-fork/issues/51). Preserve task/observation context, compare with action-only and shuffled-context controls, and report one bounded offline result. Main-first commits/pushes are now the operator's default; no new experiment PR without a real isolation need. PR #43 stays held.

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

Status reconciled 2026-09-12. Experimental code and receipts in PR #42 are on its branch; they are not all present on `main`. The final next-milestone interpretation incorporates the completed Astra/Fable discussion #743999.
