# Issue #37 ZCode blind semantic-label sample freeze

**Verdict: defer ZCode for mapper correction.** The deterministic 200-row blind audit estimates
only 72.02% semantic agreement with the frozen mapper, despite 99.725% mechanical coverage. ZCode
does not enter training.

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

## Blind review result

- Both auditors returned exactly 200 unique `{id, label, confidence}` rows; malformed or incomplete
  submissions would have failed before scoring.
- The auditors agreed without adjudication on 173/200 rows. A third reviewer saw and adjudicated
  exactly the 27 disagreements, without seeing either auditor answer or the sorter.
- Adjudicated sample agreement: **131/200 = 65.50%**.
- Population-weighted agreement: **72.02%**; 95% sampling interval **66.47–77.58%**.
- Assigned-label-only estimate: **72.22%**; 95% sampling interval **66.65–77.79%**.
- Governance estimate: **46.15%**. The governance population is only 13 actions and its displayed
  zero-width interval is not evidence of certainty; all-right/all-wrong tiny strata contribute zero
  estimated variance under the frozen scorer.
- Private auditor SHA-256 values: `a843280e08ad8866e756e2fa24ef5793d47a528d25dd59114a418b00050c767f1`,
  `9e8812a197484b18b446bda4142677016ded9e2fea65d9787f8954eb3605b20b`.
- Private adjudicator SHA-256: `2999ff6733bd7a725b5c9fe764647d2b886d725639ed582368d431854e494d9142`.
- Private adjudicated-score SHA-256: `fd441325b94f8c4e8e279cebaa73772df6879920948ae5b9aec3e3d355f825ef`.

Largest estimated error contributions are `run_script` (9.70 percentage points), `search_code`
(3.52 pp), `read_file` (3.11 pp), `sys_inspect` (2.84 pp), `fs_mutate` (1.76 pp), and `git_sync`
(1.73 pp). The most frequent observed confusion is `run_script -> run_tests` (9 sampled rows).
These concentrated, recognizable seams support defer-and-correct rather than rejecting the source.

## Decision and next action

Keep ZCode excluded from training. Trace the high-contribution confusion rows, specify only
source-grounded mapper corrections, and require witnessed red controls for each corrected mechanism.
Then rerun a newly frozen blind sample; do not rescore this sample as fresh evidence after tuning on
its errors.
