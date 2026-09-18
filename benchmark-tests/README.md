# Small/medium model benchmark scaffolding (#65)

Tracking issue: [Needle-fork #65](https://github.com/HiQS-Labs/Needle-fork/issues/65).
This folder is **draft scaffolding, not an executable or frozen model campaign**.
No model has been evaluated here and the candidate names/model-card claims have not
been independently verified in this review. This is separate from work-purpose
classification (#57/#210) and next-action prediction (#1).

- `eval-config.yaml`: proposed Terminal-Bench and GPQA settings; unresolved pins remain.
- `schema.sql`: round/model provenance, primitive trials, derived aggregates and incidents.
- `meta_score.py`: standard-library-only scorer for an already populated SQLite database.
- `round-report-template.md`: reporting shape, not a measured result.

## Scoring contract

For each observed model, require the same nonempty TB task and GPQA question sets.
TB requires exactly one valid result for each attempt ID 1–4 on every observed task.
Infrastructure failures remain primitive rows; add a replacement with the same slot
and `is_infra_fail=0` before scoring. Multiple valid replacements are rejected. Model
timeouts/failures are unresolved valid trials, not infrastructure exclusions.
GPQA requires exactly one attempt per registered question; a no-answer counts as
incorrect. Zero accuracy/pass⁴ is a real zero, not missing data.

Pass⁴ is the fraction of tasks where all four attempts passed, **not** pass@4 (at
least one success). The geometric mean is a descriptive composite of these two
benchmark metrics, not a general-intelligence or deployment-readiness grade.
Per-domain GPQA accuracy uses `biology`, `physics`, and `chemistry` domain IDs;
missing domains/telemetry stay NULL. Z-scores describe only the observed round cohort.

```bash
python3 -m pytest -q tests/test_benchmark_meta_score.py
# Once a separately approved collector has populated an existing schema.sql DB:
python3 benchmark-tests/meta_score.py benchmark-tests/results/R001/results.db R001
```

The scorer validates the entire round before atomically replacing all its derived
aggregates. Primitive rows are never rewritten, and nonexistent DB paths fail
without creating a file. Treat DBs as trusted local artifacts, not untrusted input.

## Before any campaign

Resolve and verify dataset/harness/backend/weights revisions, hardware and model
terms. Replace the informal task slice with a hashed ordered manifest and pin all
198 GPQA Diamond question IDs. Add the referenced but currently missing
`prompts/gpqa_prompt.txt`, choice shuffling and extraction controls. Freeze decoding,
thinking policy, token/time budgets, exclusions, repeat seeds and analysis gates;
independently review the protocol before inference.

The current scorer checks *observed* paired sets but cannot detect an item missing
from every model or a model missing from both benchmarks. It does not load the YAML,
enforce the proposed 198-question count, verify prompt/config hashes, or establish
cross-round comparability. Those need frozen manifest/provenance checks before real
results are publishable; do not interpret passing synthetic tests as that approval.

Keep datasets, raw responses and databases in ignored `results/` and never commit
credentials, machine paths or weights. Promote only deliberate, sanitized campaign
receipts under `TESTS-RESULTS/` following SOP.md. No new package dependencies or
Needle training/runtime/release-surface changes are introduced here.
