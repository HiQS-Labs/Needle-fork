---
title: "Recon Map — GH-41 targeted augmentation"
status: Complete
created: 2026-09-11
updated: 2026-09-11
owner: noelsaw1
goal: Trace the existing corpus seams and bound the GH-41 implementation surface.
roadmap_exempt: true
---

# Recon Map — GH-41 targeted augmentation

## Status

| What was just completed | What's next |
|---|---|
| The current corpus, serializer, generator, trainer, and test seams were traced at `b25436b`. | Use this map to review and execute the GH-41 build plan. |

Commit: `b25436b` · Mode: stale graph + direct read · Lanes: entry, state, contracts, build

## Subject and change class

Additive offline corpus-contract change: validate grounded synthetic candidates and compose them
through the existing Oracle serializer without changing model/runtime behavior.

## The seams

| Seam | Location | Crosses | Breaks if |
|---|---|---|---|
| Canonical query/row writer | `utils/corpus/serialize.py:74`, `:96` | extracted pair → trainer JSONL row | augmentation invents a second serializer or admits an unknown label |
| Real-pair builder | `utils/corpus/build_oracle_jsonl.py:39` | `pairs.jsonl` splits → train/holdout files | generated candidates can enter holdout or empty splits publish |
| Generic public augmentation | `needle/model/finetune.py:158` | arbitrary JSONL → provider-generated rows | Oracle-specific provenance is incorrectly pushed into the package API |
| Trainer renderer | `needle/model/finetune.py:194` | row dictionary → prompt and target tokens | composed rows do not retain the established shape |
| Contract tests | `tests/test_serialize.py:51`; `tests/test_generate.py:91` | serializer/generator behavior → CI | a gate passes without exercising its failure mode |

## Call paths in

`build_oracle_jsonl.main` → `serialize.to_finetune_row` → `serialize.serialize_query`.

`needle generate-data --augment` → `finetune.generate_main` → `augment_jsonl` →
`generate_dataset`. The latter is a generic public data generator and is deliberately not modified.

## State

Real/private corpora and generated outputs live under gitignored `data/`. Source code and
de-identified fixtures are tracked. The new composer will be the sole writer of its JSONL and
aggregate report, using temporary files followed by atomic replacement only after full validation.

## Contracts

- `taxonomy.LABELS_V1` / `LABEL_SET_VERSION` own valid Oracle labels.
- `serialize.to_finetune_row` owns the trainer row shape and abstention conversion.
- Generated candidates are training-only; issue #25 retains exclusive ownership of its active
  evaluation draw and correction comparison.
- The public repo must not receive private prompts, commands, paths, session IDs, or repository names.

## Build, failure, and rollback today

Corpus utilities are standard-library scripts tested through pytest. Repository acceptance is
`pytest -q -m "not slow"` plus `utils/pdda/pdda.sh run`. The change is additive and rolls back by
removing the new utility/tests/fixtures; no model or runtime artifact is migrated.

## Unknowns

| Unknown | Why it matters | What would settle it |
|---|---|---|
| Real-holdout model gain | Determines whether synthetic training data is useful | Phase 3 controlled experiment after fresh holdout availability |
| Provider-specific generation quality | Determines whether existing generation is sufficient | Independently review a later generated candidate sample; outside this implementation |

## Current-state radius

The change reaches offline Oracle training-data preparation and its tests only; issue #25 audit
state, runtime hooks, model numerics, export, native inference, and PyPI consumers remain untouched.
