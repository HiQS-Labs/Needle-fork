# Issue #37 ZCode blind semantic-label sample freeze

**Verdict: the deterministic 200-row ZCode sample is frozen and ready for two independent blind
reviews.** This advances semantic validation only; it does not admit ZCode rows to training.

## Frozen source and draw

- Source: the same 21-session, 1,091-action Studio inventory committed in PR #38.
- Baseline replay: byte-identical to the committed ZCode coverage receipt.
- Coverage: 100% alias coverage, 99.725% mechanical mapping coverage, 26 mapped labels.
- Draw: 200 rows across all 27 predicted strata (including `unmapped`) and 18 sessions.
- Allocation: square-root stratification, floor 4 where population permits.
- Seed: `3701`.
- Sample format: `agent-label-blind-sample-v1`.
- Scoring contract: audit format v2, `stratified-srswor-v1`.

## Reproducibility and privacy receipts

- Source-file manifest SHA-256: `aebce80bfb73de4a6b77e68a87764cb5c011c1aa77d46a74de9dc19eebb4739b`
- Public aggregate plan SHA-256: `88a4b46daf5fb3fc77ebfcbe8ab4f1aa5051156fb6c29517adfa85c72b0275e2`
- Private blinded sample SHA-256: `4032909a6b6eb467d975ec38e3b593c6dec7fe70b6ed0e05a7ee6332979a98f5`
- Private held-back sorter SHA-256: `8f89363b5f7a5390e182569df5194767b4b5c5bc799ef3db896efb505807d07b`
- Two independent draws produced byte-identical plan, sample, and sorter files.
- The scorer contract accepted exactly 200 sample and sorter rows in a synthetic perfect-agreement
  probe. That probe did not create auditor answers for the real review.
- Raw tool arguments, commands, paths, source identities, and blind rows remain below ignored
  `data/` and are not committed.

## Next action

Give `data/agent-label-review/zcode-v1/sample.jsonl` independently to two reviewers. Each must return
exactly one `{id, label, confidence}` row per sample ID without seeing `sorter.jsonl`. Adjudicate only
their disagreements, then score through `utils/corpus/score_audit.py`.
