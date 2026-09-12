# Test runner mapping correction — #56

Fixed the two defects found in #53 without regenerating datasets or scores.
The shared taxonomy now recognizes effective unittest invocations as run_tests.
Unambiguous pytest/unittest help probes and pytest version probes map to
sys_inspect (run_command in the six-label projection).

## Scope

Sixteen added lines in the existing label_segment seam reuse wrapper unwrapping,
command-position validation and quote-aware tokens. Future private 44-label
extraction and OpenHands six-label extraction consume this correction. Labels,
native editor behavior, model numerics and serving are unchanged.

Metadata recognition is deliberately bounded: help/version flags, optionally
quiet/verbose, and unittest discovery help. It does not interpret arbitrary
options/positional arguments as metadata-only invocations. For example, a version
string used as a -k expression must not become inspection. This is not a complete
parser for every runner/plugin CLI. Unknown forms retain ordinary runner treatment.
The existing compound-command tier and first-segment tie-break remain intact.

## Verification ledger

- Before the fix, the focused repro/controls run had 15 failures and 18 passes.
  One new compound expectation was subsequently corrected to respect the existing
  equal-tier tie-break rather than introduce a new precedence policy.
- Initial implementation surfaced an existing environment-prefix mutation-control
  failure. Requiring the existing command-position check corrected that bypass.
- Final taxonomy, coding-core and context-probe suites: **263 passed**.
- Full non-slow suite: **468 passed, 6 skipped, 11 deselected**. This includes
  27 new parameterized cases across taxonomy/native Bash and six-label projection.
- Read-only differential over the 16 Bash calls (previous/next) in #53's fixed
  12-event audit found exactly three changes: two unittest invocations changed
  run_script to run_tests; one pytest version query changed run_tests to sys_inspect.
  No source commands were executed. This is a bounded diagnostic differential,
  not a dataset-wide impact estimate or re-evaluation.
- All 13 hashes recorded by the frozen seven-model panel still match, including
  its retained training/evaluation inputs and locked responses. Published scores
  were not recomputed or revised.

Reproduce regressions with
`.venv-mlx-spike/bin/python -m pytest -q tests/test_taxonomy.py tests/test_coding_core.py tests/test_context_probe.py`.
The tests cover both direct label_bash and native Bash label_call, true runners,
wrappers, metadata probes, quoted data, generic scripts and compound precedence.

## Historical replay and next step

The #53 audit intentionally expected the old projection; replay it from its
pinned pre-fix commit `f225278`, not against this corrected mapper. Its receipt
remains historical evidence, not a test that should be updated to new labels.

Next: define a separately versioned data refresh and one bounded follow-up before
any new scoring. Directory-view/read and ad-hoc-script/test-intent boundaries
remain explicit policy questions; #56 does not decide them or authorize training.
No new model calls, downloads, dataset writes, runtime changes or PR #43 changes.
