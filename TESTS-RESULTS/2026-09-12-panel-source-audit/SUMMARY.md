# Panel source audit — #53 completed

Two concrete Bash classification defects were found. The 12 audited examples all
align with their raw source and frozen projection; there is no observed row/key
mix-up. Context loss and coarse-label boundaries also matter, but this audit does
not establish why every model missed an event. Next: scoped mapper correction
[#56](https://github.com/HiQS-Labs/Needle-fork/issues/56), not more model calls or training.

## Scope and method

Audited the original nine all-seven misses plus the earliest correctly predicted
panel case for each of read, run_command and run_tests: 12 events, 12 distinct
issues. Selection stayed fixed after MiniMax got one of the nine right. This is
an outcome-enriched diagnostic sample, not an estimate of dataset error prevalence.

Used the retained Nebius SWE-rebench-openhands-trajectories snapshot, CC BY 4.0,
revision `35455389ab51bf5e2306bfd436ef72d0f98bf882`. Verified its SHA256 and replayed
the original seven-seat scorer. A Python line trace at the existing extractor's
row-emission point linked each frozen example to its unique raw next call. Checked
the prior call ID, matched response, active user request, chronology, exact feature
projection and target. Target results were inspected only as audit evidence, never
as prediction input. No dataset commands were executed.

## Findings

| Primary triage category for the nine misses | Events | Interpretation |
|---|---:|---|
| Concrete target-mapping defects | 2 | A unittest suite maps to run_command; a pytest version query maps to run_tests. |
| Coarse taxonomy boundaries | 3 | Directory view maps to read; two ad-hoc verification scripts map to run_command. |
| Material context loss | 2 | The previous test identity is cropped away; separator padding occupies about 81% of the visible observation. |
| Behavioral cause unresolved | 2 | A correct search or real test target was missed despite retaining the full previous response. |

These are coordinator-assigned triage buckets, not exclusive causal findings.
Additional caveats overlap buckets. All three controls reproduce their stored
targets; one has the same ad-hoc-script boundary and two have cropped observations.

### Confirmed defects, filed immediately as #56

- `python3 -m unittest -v bowler.tests` invokes a suite and its retained result
  reports two tests, but the classifier returns run_script, projected to
  run_command. Another audited event's **previous** unittest action has this
  same problem; its search target itself is correct.
- `python -m pytest --version` returns only version metadata, but maps to
  run_tests. A normal `python -m pytest tests/test_x.py -v` correctly maps to
  run_tests; generic Python scripts and `echo unittest` do not become test runs.

The shared `utils/corpus/taxonomy.py` named-test rule lacks unittest and matches
pytest without distinguishing metadata-only invocation. This also feeds private
44-label extraction: a future fix needs scoped regression checks there, not only
in the six-label projection. No mapper edits were made during this audit.

### Boundaries are not automatically defects

Native editor `view` always maps to read, including a directory listing. That
disagrees with the quiz's plain-language description of directory listing as search;
the call's path alone cannot reliably distinguish file from directory. This needs
an explicit future labeling policy, not a filename heuristic or silent relabeling.
Ad-hoc scripts containing assertions remain run_command under the frozen mechanical
policy, unlike named test runners. This explains a semantic distinction, not whether
a particular model would be right under a different policy.

The unanimous error case really does proceed from an error-bearing custom-script
result to an existing pytest test. The entire previous response is visible. There
is no evidence to relabel that target edit simply because all models chose edit.

### Context losses measured

All 12 task strings are clipped at 600 normalized characters; in ten, that cuts
inside the issue description. The omitted tail also contains the source agent's
staged work instructions. Five previous responses are tail-cropped (three misses,
two controls); one control loses only six characters. Thus cropping alone does not
separate correct predictions from misses.

Two missed pytest observations retain mostly separator padding while losing the
test identifier. A different miss retains only a generic exit-status response:
its prior cleanup command is not present in the feature schema. All 12 omit the
previous call's structured arguments, though some results echo paths or operations.
Adding useful completed-call context is a plausible later experiment, not a measured
accuracy gain from this audit.

## Verification and limitations

12/12 source alignments and chronological call/result links passed. The original
seven-seat score replay is unchanged. Red controls: wrong prior response ID removes
the audited row; replacing its next call rejects its old target; replacing the
future target result leaves the pre-action row unchanged. Non-slow tests: 441 passed,
6 skipped, 11 deselected. Source, mapper, script and private-artifact hashes are in
`metrics.json`. Detailed raw cases and coordinator annotations remain ignored locally.

Reproduce with `.venv-mlx-spike/bin/python TESTS-RESULTS/2026-09-12-panel-source-audit/audit.py`.
Stdout contains raw case details: retain it only under ignored `data/`. Replay needs
the retained source/panel artifacts. The semantic triage is human-readable coordinator
judgment, not an independent human audit or a score computed by the extractor itself.

No new model calls, downloads, training, runtime changes, or retroactive scores.
Original #51/#52/#54 evidence and all gates stand; PR #43 remains held. Stop this
audit here. Correct and verify #56 before selecting a separately versioned follow-up;
do not treat the panel leaderboard as calibrated on a clean semantic target.
