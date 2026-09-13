---
title: Shortlist feasibility Recon Map
status: Complete
created: 2026-09-12
updated: 2026-09-12
owner: noelsaw1
goal: Bound the existing counter and paired-data seams before scoping a shortlist check.
roadmap_exempt: true
---

# Recon Map — shortlist feasibility

## Status

| What was just completed | What's next |
|---|---|
| Counter and data seams traced; #62 executed through the additive offline adapter. | Historical map only; follow the completed shortlist result, no runtime integration. |

Read-only local trace at `bf6c196`; no graph service used, no delegated exploration.
Scope: one proposed offline count-ranking evaluator; no package/runtime integration.
Issue [#62](https://github.com/HiQS-Labs/Needle-fork/issues/62).

| Seam | Existing contract / implication |
|---|---|
| `spike/coding_core/context_refresh.py:prepare` | First resolved trajectory per issue/trace, train capped at 10,000, evaluation 2,000; matched q2/q3 history/target and overlap filtering. Reuse retained outputs, do not re-extract. |
| `context_refresh.py:main` | New-only directory/file writes; hashes all artifacts into manifest. Existing output has 10,000/1,722 rows over 224/40 disjoint issues; separate quiz samples one row per evaluation issue. |
| `baselines.py:fit` | Training-only global targets, change destinations, last-action transitions, fine/coarse phase counters; rejects no training rows. Count fit, not a neural model. |
| `baselines.py:phase_keys` | Last label, whether earlier history includes edit, and penultimate label; history only. |
| `baselines.py:choose` / `predict` | Deterministic count/prior/lexical tie break; phase support floor 2; returns ONE label per family, not an existing top-three list. Ordinary and observed-switch-excluded branches are different tasks. |
| Existing consumers | `context_probe.py`, `context_refresh.py`, `tests/test_coding_core.py`, `tests/test_private_transitions.py`; changing prediction would alter historical baselines. Add ranking offline without changing them. |
| Receipts | `TESTS-RESULTS/2026-09-12-context-refresh/manifest.json` pins schema, counts, hashes and dataset revision. `ROUND2.md` establishes this is now reused development evidence. |

Proposed read path: trusted committed manifest -> bounded paired files -> validate
schema/digest/counts/splits -> q2 histories + training targets -> existing `fit` ->
new local ranking adapter -> same-case shortlist metrics -> new private receipt ->
sanitized public projection. Prediction sees only history, never evaluation target,
task or observation. Evaluation targets are read only by the scorer.

Proposed writes: one `spike/coding_core/shortlist_eval.py`, one focused test file,
new dated aggregate receipt and current tracking docs. No baseline code, canonical
data, release files, runtime SDK, weights, user feedback CSV or PR #43 writes.
No abstraction layer or second feature extractor is needed. Preserve old top-one
predictions by comparison, rather than rewriting their implementation.

Failures: missing/changed retained artifact, empty/overlapping splits, unknown
labels, bad output cardinality or memory/time tripwire -> refuse scoring; leave
original artifacts unchanged. New-only output prevents accidental overwrite.
Rollback: revert only the additive evaluator/docs commit; private generated run
can remain ignored. No service/state migration involved (Easy).

Pre-implementation unknowns: hit@3 lift had NOT been computed; shortlist usefulness cannot be inferred
from these labels. No live integration seam traced because no integration is in
scope. Consult may advise against the proposed round or recommend a separate
interaction question; that would require a new explicit execution decision.

## Lessons Learned (For Future Agents)

The additive adapter preserved all old ordinary top-one outputs. Existing hash,
split and memory checks were reusable; no runtime integration was needed to answer
the bounded offline question. See [completed outcome](SHORTLIST-FEASIBILITY.md#outcome).
