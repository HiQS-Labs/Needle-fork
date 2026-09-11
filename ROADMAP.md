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
| The 400-row targeted correction audit is complete, and a snapshot-based source refresh now provides 2,913 isolated evaluation candidates across 32 sessions. | **Collect more independent, label-diverse evaluation sessions until the frozen sampler can allocate all 1,000 rows.** It currently allocates at most 541 under the label quotas and 40-row session cap; then freeze and review the draw before training. |

> **Corrected 2026-09-09.** This cell previously read *"first `needle finetune` run on JAX/CPU at
> `--max-len 2048`"*. That was superseded on 2026-09-07 by
> [#1's §4 decision](https://github.com/HiQS-Labs/Needle-fork/issues/1#issuecomment-5574864887):
> measured at ~150 s/step and ~127 h/epoch, the CPU path does not finish, and §4 is satisfied by MLX
> on the GPU (§4 and GH-5 are one lane). The pointer kept instructing that run after the measurement
> that killed it. `--max-len 2048` itself stands — it prevents target truncation.

## Ledger

### Queue / parked intake

- No parked intake docs.

### In progress

- [Label correctness audit — make the §2 gate trustworthy](PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md) — source identity and disjoint manifests are merged; #25 clears its 30-session floor but remains blocked because the frozen sampler can allocate only 541/1,000 evaluation rows under its label quotas and session cap. ([#20](https://github.com/HiQS-Labs/Needle-fork/issues/20), [#23](https://github.com/HiQS-Labs/Needle-fork/issues/23), [#25](https://github.com/HiQS-Labs/Needle-fork/issues/25))
- [Targeted grounded augmentation](PROJECT/2-WORKING/GH-41-TARGETED-AUGMENTATION.md) — build the training-only validation/composition gate without consuming #25 evaluation evidence. ([#41](https://github.com/HiQS-Labs/Needle-fork/issues/41))

### Completed

- [Phase 2 §1 — Freeze the v1 Oracle label taxonomy](PROJECT/3-COMPLETED/PHASE-2-LABEL-TAXONOMY.md) — v1 published as `oracle/labels-v1.json`; current Studio corpus has 71,763 calls at 96.41% mapping coverage. ([#1](https://github.com/HiQS-Labs/Needle-fork/issues/1))

### Deferred

- No deferred docs.

---

*Add new work here only when a real `PROJECT/**` doc exists to own the execution detail.*
