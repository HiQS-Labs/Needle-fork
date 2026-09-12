# #59 round one — context refresh ready

Prepared 10,000 training transitions across 224 issues and a separate eligible pool
of 1,722 transitions across 40 previously unevaluated holdout issues. The model quiz
is **40 cases, one per issue**, not all 1,722 rows. No model prediction has been
collected or graded in this round.

The q3 opt-in restores issue-focused text, compacts separator padding before clipping
the prior result, and includes a bounded description of the last completed call.
It shares q2's chronological state machine and corrected #56 mapper. Native directory
views remain read; ad-hoc verification scripts remain run_command. No new labels.
This is a bundled context change, not identification of one causal feature.

## Data and limits

- Retained source: Nebius SWE-rebench OpenHands trajectories, CC BY 4.0, revision
  `35455389ab51bf5e2306bfd436ef72d0f98bf882`, 1,000 trajectories at offset 1,000.
  Source SHA-256 and all output hashes are in [manifest.json](manifest.json).
- Training uses only old training issue IDs. Fresh evaluation excludes **both** old
  partitions, uses the existing issue hash split and first resolved issue/trajectory,
  and caps the first 50 eligible transitions per issue. Exact inputs in either view
  are checked across partitions; zero training rows needed overlap removal.
- Target-blind quiz support: command 10, read 10, edit 8, tests 6, search 6, Git 0.
  The larger pool has all six labels, but the quiz cannot establish Git capability.
- All 40 shuffled contexts move to a different case in the same last-action group;
  action history and schema are unchanged. No target-based sampling/stratification.
- Corrected mapper changes 149 training targets and 1,421 histories relative to the
  retained old training data. Both comparison arms use these **same new labels**;
  this does not revise old accuracy scores.
- Observed peak RSS ~177 MiB; CPU-only. The Mac rejected RLIMIT_AS, so the 1 GiB RSS
  checkpoint is a tripwire, not an OS hard ceiling. Prompt sizes: 64,669 bytes (q2),
  84,683 each (q3 and shuffled). No downloads or neural training.

## Verification

New rich-context tests witnessed two failures on the old implementation, then passed.
Monkeypatched future-result leakage and wrong prior-result joining each made their
guard fail. Empty/old-issue/feature-overlap and output-exists controls fail closed.
Full non-slow suite: 486 passed, 6 skipped, 11 deselected. Repeated extraction to a
fresh directory produced all 10 identical data/packet hashes.

q2 all-source output is unchanged across the implementation: 55,942 transitions,
serialized SHA-256 `343300e19c0a601a906061b7a7b4397763e41d3eca899d89593120943bb1c709`.
All 13 frozen panel hashes match. Held PR #43 is still open at `974ddcf9b480a985c272ac5215bce87ea669436e`.

## Replay and next round

```sh
.venv-mlx-spike/bin/python -m spike.coding_core.context_refresh \
  --source-run data/context-next-action-2026-09-12-launch2 \
  --old-run data/context-next-action-2026-09-12-score \
  --out data/context-refresh-new-replay
```

Raw source, packets, keys, and paired JSONL remain ignored locally. The output path
must not already exist. Replay needs those retained private inputs.

Proceed immediately after this round's push to the frozen three-arm Qwen comparison
in [#59](https://github.com/HiQS-Labs/Needle-fork/issues/59). Plan review changed the
transport to tool-free HTTP; no executable agent harness receives source text.
Live price preflight caps total worst-case token cost at $1, including any retry.
No old gate changes or human-acceptance claim. Absolute wall deadline remains
2026-09-12 17:59:35 UTC.
