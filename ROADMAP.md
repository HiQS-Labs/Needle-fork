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
| Public-trained six-action pilots completed; the Astra/Fable review identified an untested private-training comparison. | **Run the bounded in-domain baseline round described in the [current arc](doc/oracle-collaborator-summary.md#next-milestone--agreed-not-yet-run) and tracked in [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1).** The stricter #25 lane remains capacity-blocked at 541/1,000 and is deferred in priority. |

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

- [Private-trained transition comparison](PROJECT/2-WORKING/PRIVATE-TRANSITIONS.md) — bounded follow-through under [#1](https://github.com/HiQS-Labs/Needle-fork/issues/1); no serving or #43 changes.

- [ZCode mapper recon and qualification](PROJECT/2-WORKING/RECON-ZCODE-MAPPER-CORRECTION.md) — PR #40 merged the scoped corrections; fresh blind qualification remains open in [#37](https://github.com/HiQS-Labs/Needle-fork/issues/37).

- [Label correctness audit — make the §2 gate trustworthy](PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md) — source identity and disjoint manifests are merged; #25 clears its 30-session floor but remains blocked because the frozen sampler can allocate only 541/1,000 evaluation rows under its label quotas and session cap. ([#20](https://github.com/HiQS-Labs/Needle-fork/issues/20), [#23](https://github.com/HiQS-Labs/Needle-fork/issues/23), [#25](https://github.com/HiQS-Labs/Needle-fork/issues/25))

### Completed

- [Phase 2 §1 — Freeze the v1 Oracle label taxonomy](PROJECT/3-COMPLETED/PHASE-2-LABEL-TAXONOMY.md) — v1 published as `oracle/labels-v1.json`; current Studio corpus has 71,763 calls at 96.41% mapping coverage. ([#1](https://github.com/HiQS-Labs/Needle-fork/issues/1))

### Deferred

- No deferred docs.

---

*Add new work here only when a real `PROJECT/**` doc exists to own the execution detail.*
