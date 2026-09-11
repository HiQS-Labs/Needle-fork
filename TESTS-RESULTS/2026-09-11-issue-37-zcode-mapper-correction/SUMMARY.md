# Issue #37 — ZCode mapper-correction development receipt

Base commit: `eca144b`

## Scope

Three narrow mapper corrections, with no label-vocabulary, model, checkpoint, or training change:

- shell-invoked test-suite scripts -> `run_tests`;
- wait followed by status/log inspection -> `session_control`;
- content edits under `PROJECT/3-COMPLETED` -> `apply_patch` (document completion remains a move).

## Witnessed checks

- Before implementation: the 3 retained load-bearing assertions failed.
- After implementation: `tests/test_taxonomy.py` passed 198/198.
- Full non-slow suite: 383 passed, 6 skipped, 6 deselected.
- `git diff --check`: passed.

## Development-only replay

Replaying the already-reviewed 200-row ZCode sample changes 10 predictions and raises agreement
from 131/200 (65.5%) to 141/200 (70.5%). All 10 changes match the saved reference. This is tuning
evidence, not a fresh estimate; the old sample must not be reused to qualify ZCode.

On the full frozen 1,091-action inventory, mapping coverage remains 99.725%. The corrections move
the expected narrow groups (`run_script` toward `run_tests`, `sys_inspect` toward
`session_control`, and `complete_doc` toward `apply_patch`) without
changing the source inventory, alias contract, or label vocabulary.

## Next gate

Freeze a new ZCode inventory and blind sample, obtain two complete independent reviews plus exact
disagreement adjudication, and score it with the existing fail-closed scorer. ZCode remains excluded
from training until that gate passes.
