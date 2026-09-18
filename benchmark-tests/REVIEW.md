# Pre-publication review — 2026-09-17

Tracking: [Needle #65](https://github.com/HiQS-Labs/Needle-fork/issues/65).
Verdict: **publish as draft scaffolding; block real campaign execution** until the
pins, manifests, prompt and analysis policy described in README.md are frozen.

## Rebase review

The checkout began at `28e8563`, 44 commits behind `origin/main` (`8505484`).
Reviewed incoming history and overlap with the local PDDA edits and untracked
benchmark folder: origin changed none of those paths. Preserved the two tracked
edits in a local commit, then rebased onto origin without conflicts, stash, restore,
or remote history rewriting. Rebased preservation commit: `b896e12`.

## Scoring findings and corrections

- The original scorer crashed against its own schema: TB insert supplied 11 values
  for 10 columns; the meta insert also had nine placeholders for eight values.
- Incomplete tasks were omitted from the pass⁴ denominator; a fixture with four
  successful attempts plus one incomplete failed task incorrectly scored 1.0.
- Zero pass⁴ was treated as missing, violating the non-NULL meta schema and omitting
  zero performers from cohort z-scores.
- Missing GPQA data was presented as zero; duplicate attempts and mismatched item
  sets were not rejected. A misspelled database path created an empty DB.
- Median TB latency, output-token totals and GPQA domain breakdowns were never filled.

Corrected inserts, completeness/identity checks, zero handling and available
telemetry. Validate the whole observed round before atomically replacing derived
projections; preserve primitives and reject incomplete infra replacements. Added
transaction rollback and stale-cohort controls. Scope stays standard-library-only,
with no training, runtime, numerical/export, dependency or release-version changes.

## Verification receipts

Before corrections, `python3 -m pytest -q tests/test_benchmark_meta_score.py`
reported **13 failed**, witnessing schema integration, partial/invalid trials,
missing/unpaired data and missing-path controls. After corrections, the targeted
suite also covers zero GPQA/no-answer, infra replacement, rollback and cohort removal.

```text
python3 -m pytest -q tests/test_benchmark_meta_score.py tests/test_pdda_changelog.py
25 passed in 5.15s

uv run --no-project --python 3.12 --with pytest --with pydantic --with numpy \
  --with jax --with flax --with optax --with sentencepiece --with huggingface-hub \
  python -m pytest -q -m 'not slow'
538 passed, 6 skipped, 11 deselected in 24.88s

bash -n utils/pdda/pdda.sh
exit 0
```

The system Python initially failed full-suite collection because NumPy was absent;
the isolated uv test environment supplied existing project test/training dependencies
without changing pyproject.toml. PDDA tests exercise the actual shell checker, valid
and invalid dates, bracketless three/four-part versions and an old-matcher mutation
that warns before the current matcher passes.

No dataset downloads, model inference, paid calls, fine-tuning or benchmark campaign
were run. Synthetic controls establish scorer behavior, not scientific validity or
model quality. Candidate model facts and proposed benchmark versions remain
unverified draft inputs. The scorer cannot prove completeness against a manifest
that has not yet been created, including models/items absent from every input table.
