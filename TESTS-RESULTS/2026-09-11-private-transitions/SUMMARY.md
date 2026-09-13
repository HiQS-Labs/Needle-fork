# Private-trained transition round — 2026-09-11

## Verdict: stop under the agreed gates

Private training improved phase-backoff, but neither model met either predeclared gate.
This stops investment in these two predictors at the current six-action representation;
it does not establish that all next-action prediction is impossible. No serving work follows.

| Measurement | Reference | Markov-1 | Phase-backoff | Required |
|---|---:|---:|---:|---:|
| Overall, 23,442 actions | Repeat-last 43.5244% | 43.5244% | 45.7256% | 48.5244% |
| Conditional destination, 13,239 changes | Train-derived destination 30.8634% | 37.9711% | 40.8112% | 40.8634% |
| Ordinary prediction on changes | Repeat-last 0% | 0% | 14.0645% | Diagnostic only |

Phase-backoff's overall gain is +2.2012 percentage points, below the required +5.
Its conditional gain is +9.9479 points, below +10; seven more correct change destinations would
have cleared that gate, but the result is not rounded up and the overall gate still fails.
The conditional task excludes the previous action because an observed switch occurred; it does
not establish that a deployed predictor can detect that switch or give a useful suggestion.

## Frozen inputs and implementation

- Fit: 45,127 actions / 296 sessions, all six labels supported.
- Evaluate: unchanged 23,442 eligible actions / 63 sessions, of which 13,239 change action.
- Source: previously copied private canonical pairs, original session split; no re-extraction.
  45,128 train rows were eligible before removing one exact shared request/history/target row
  from training only. No shared session IDs or repeated session/step events were found.
- Ordinary predictor: selected from #42 at `18274fc`; same features, support floor 2 and tie rules.
  No raw prompt learning, new feature search, dependency, LoRA or MLX training.
- Conditional phase support is measured **after** previous-action removal: fine phase >=2,
  coarse phase >=2, Markov transition >=1, global change-destination fallback >=1.
  Every level excludes the previous action. The last distribution also defines the baseline;
  ties use global training target frequency, then lexical order.
- Code frozen at `082ca3a`; one fit/score invocation, 1.39 seconds wall time. Expected exit 1
  means the promotion gate failed, not a process crash. The source hash matched before/after.
- Command: `python3 spike/coding_core/baselines.py --private-pairs <private-pairs.jsonl> --out <private-result.json>`.
  Full hashes and per-session distributions are retained in the ignored private receipt, not here.
  [metrics.json](metrics.json) is the allowlisted pooled projection of that receipt.

## Verification

Post-run review hardening (2026-09-12): reruns additionally require
`--private-manifest <trusted-retained-private-manifest.json>`, with `input_sha256` from the retained
frozen input (the original private receipt can supply it). This manifest is trusted local provenance,
not generated from the candidate input at rerun time; deliberately replacing both defeats the check.
The hash stays private. The CLI also checks 45,127 train rows / 296 train sessions and one excluded
overlap row, alongside the existing evaluation counts. A same-size content-substitution regression
was witnessed red, then green. This hardens future reproducibility; it does not retroactively add a
pre-run guard to `082ca3a`, alter its receipt, or imply a new evaluation was performed.

- Preflight full non-slow suite: 384 passed, 6 skipped, 11 deselected.
- Extended suite: 395 passed, 6 skipped, 11 deselected; 11 focused tests passed.
- Final suite after adding CLI manifest/overwrite/empty-fallback guards: 398 passed, 6 skipped,
  11 deselected (14 focused tests). No fitting, prediction, or gate logic changed after the frozen run;
  subsequent changes only harden CLI input validation.
- 6,192 synthetic label/model comparisons against the original frozen evaluator matched exactly.
- Negative controls: making same-family AND into OR failed the gate test; disabling session
  overlap refusal failed the overlap test. Both restored; suite green before private fitting.
- Both plan advisors required explicit exclusion/backoff, split checks and same-family gates.
  Their privacy advice differed; the stricter private-only session-distribution rule was adopted.
  Advisors reviewed the plan, not the measured result. Raw logs remain private due to local paths.

## Limits and next decision

This is reused development evidence and agreement with imperfect projected labels, not fresh
confirmation or human acceptance. Legacy session/step checks and exact canonical content hashes
do not establish raw-transcript or semantic independence; common action transitions are expected
across sessions and were not removed. Broad `run_command` projection limits interpretation.
No statistical claim of significance is made from the small gate miss or pooled row count.

The agreed decision is **stop**, not more tuning against these labels. A materially different
product question needs a separately agreed scope. PR #43 remains on the operator's testing hold.
Tracked under [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1); implementation/receipt PR #48.
