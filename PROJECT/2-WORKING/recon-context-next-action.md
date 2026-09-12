---
title: Context next-action recon
status: Shipped
created: 2026-09-12
updated: 2026-09-12
owner: noelsaw1
goal: Ground the context-aware experiment in existing extraction and baseline seams.
roadmap_exempt: true
---

# Recon Map — context next-action

## Status

| What was just completed | What's next |
|---|---|
| Bounded source trace completed. | Apply the sibling #51 protocol; no further recon lane needed. |

Commit: main `a487839`; selected source `18274fc` (#42), baseline `e05b4d6` (#48).
Mode: grep-only (no codebase-memory tool available); one local lane, bounded offline subsystem.

## Subject and change class

Extend the existing six-action OpenHands extraction and add a context-aware offline comparison.
No package runtime consumers; not a change to the canonical 44-label contract.

## Seams and call paths

| Seam | Read location | Crosses / risk |
|---|---|---|
| Source acquisition | #42 `spike/coding_core/prepare_openhands.py:139` `_remote_rows` | HF API revision guard and truncation refusal; existing downloader is not a byte-bounded immutable snapshot. New runner must cap responses and retain source. |
| Tool mapping | #42 `prepare_openhands.py:34` `project_bash`, `:54` `project_call` | Reuses main `utils/corpus/taxonomy.py:792` `label_bash`; transport arguments determine six labels. Shared taxonomy stays unchanged. |
| Query construction | #42 `prepare_openhands.py:89` `_query`, `:95` `trajectory_rows` | Old q1 keeps short issue and prior actions, ignores observations. Existing tests expect q1 bytes; preserve default mode. |
| Baselines | #48 `spike/coding_core/baselines.py` `fit` -> `predict` | Counts use history only. Import as offline comparator; never call private evaluation CLI. |
| Tests | #42 `tests/test_coding_core.py` | Projection, split, controls and baseline behavior; retain when selecting code onto main. |
| Packaging | `pyproject.toml` package discovery | Only `needle*` is packaged. `spike/` remains offline; no runtime dependencies or entry-point changes. |

## State, failure and rollback

Existing public converter writes JSONL/provenance via staging and refuses existing output.
New probe writes its own fresh ignored data directory, with a retained source snapshot and pooled
receipt. Source is data, never instructions to execute. No transcript commands are run.
Selected source files are absent on main today; import only named files, not research branches.
Rollback is a normal revert of scoped source/docs commits; retain private experiment receipts.

## Unknowns

| Unknown | Why it matters | Resolution |
|---|---|---|
| Usable observation coverage and label support in bounded sample | Could make the experiment inadequate | Count before fitting; fail on empty/sparse partitions, report unsupported labels. |
| Text adds predictive information | The hypothesis, not an established result | Same-row action-only and context-shuffle controls. |
| Generalization to operator workflow | Public issue-fixing is a different population | Not answered here; no acceptance/deployment claim. |

Current-state radius: experimental CLI consumers and their tests; no runtime, training/export,
PyPI dependency, private benchmark membership, or held #43 branch changes.
