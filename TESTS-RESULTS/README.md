# TESTS-RESULTS

Receipts for every measured Phase 2 run, adopting the protocol from
[XYZ-forge#467 Message 4](https://github.com/HiQS-Labs/XYZ-forge/issues/467#issuecomment-5562314838)
as-is, matching [Orion-fork#1](https://github.com/HiQS-Labs/Orion-fork/issues/1).

```text
TESTS-RESULTS/
├── README.md                          # this file
└── YYYY-MM-DD-<campaign-name>/
    ├── raw-metrics.json               # machine-parseable execution records
    └── SUMMARY.md                     # human-readable comparison table
```

## Rules

- Write the folder **before** reporting a result.
- **Commit it.** Receipts are citable; gitignored receipts are not.
- A failed run still gets a folder, with `"status"` saying so.
- Assert non-empty before trusting any number — per [`AGENTS.md`](../AGENTS.md) §6,
  *an empty input passes every check*.
- Receipts carry **aggregates only**. No prompt text, no command strings, no file
  paths from the operator's sessions: `data/` is gitignored for that reason and a
  receipt must not launder it into git. `measure_taxonomy.py` enforces this by
  emitting evidence strings only under `--show-evidence`, which is local-only.

## Base fields (Message 4)

`timestamp`, `machine`, `chip`, `cores`, `memory_gb`, `os_version`, `git_commit`,
`branch`, `target`, `benchmark`, `wall_clock_seconds`, `timing_breakdown`,
`throughput`, `status`.

## Phase-2 fields

The varying thing must be in the record, so runs stay attributable:

| field | why |
|---|---|
| `label_set_version` | which frozen taxonomy the run used |
| `mapping_coverage` | §2 gate — share of calls resolving to a real intent label |
| `dataset_rows` | counted **after** `load_jsonl`, not after extraction (see the silent-drop hazard in #1 §3) |
| `qat_bits` / `export_bits` | training vs export numerics, so a parity regression is attributable |
| `metrics` | top-1, top-3, per-label governance vs coding, abstention P/R, confidence separation |
