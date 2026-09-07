<!-- PDDA ROADMAP CONTRACT — this file is a POINTER/LEDGER, not a plan body.
     Allowed: queued intake / projects in progress / completed / attempted / deferred + links to PROJECT/** docs.
     NOT allowed: phase checklists, build steps, deep execution notes — put those in the project doc.
     Carve-out: a SHORT exception note is OK only when omitting it would hide an operationally critical fact.
     Coverage rule: every PROJECT/2-WORKING doc must be reflected here by a pointer (or opt out with roadmap_exempt: true).
     Enforced by `pdda.sh roadmap` + `pdda.sh roadmap-coverage` (deterministic) + utils/pdda/pdda-doc-ready.sh ROADMAP rubric (LLM). -->

# Roadmap

> **Pointer/ledger only — not a plan body.** Execution detail (phase checklists, build steps, QA
> gates, deep notes) lives in the linked `PROJECT/**` docs; keep it there. See the contract banner above.

## Status

| What was just completed | What's next |
|---|---|
| Phase 2 §3 `query` serialization shipped as one shared function for trainer and Stop hook, with the train/serve invariant as a test; token budget measured (schemas alone = 1,383 tokens) so §4 trains at `--max-len 2048` (2026-09-07). | Cut `v1.0.0-draft` → `v1.0.0`; first `needle finetune` run on JAX/CPU at `--max-len 2048`; §3b/§3c synthesis for the abstain slice and three thin governance labels. |

## Ledger

### Queue / parked intake

- No parked intake docs.

### In progress

- [Phase 2 §1 — Freeze the v1 Oracle label taxonomy](PROJECT/2-WORKING/PHASE-2-LABEL-TAXONOMY.md) — v1 published as `oracle/labels-v1.json`; Studio corpus re-extracted (74,909 pairs, coverage 98.52%). ([#1](https://github.com/HiQS-Labs/Needle-fork/issues/1))

### Completed

- No completed docs.

### Deferred

- No deferred docs.

---

*Add new work here only when a real `PROJECT/**` doc exists to own the execution detail.*
