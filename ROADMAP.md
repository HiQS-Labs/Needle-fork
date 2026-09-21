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
| [#62 shortlist check](PROJECT/3-COMPLETED/SHORTLIST-FEASIBILITY.md) completed: +4.26pp over Markov missed +5pp; parked. | Operator requested [#63 app feedback plan](PROJECT/2-WORKING/CODEX-NEEDLE-FEEDBACK.md), a separate simple-baseline usability trial; no implementation yet. PR #43 remains held. |

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

- [GH-67: Jev zero-shot rerun of the #31 purpose/area holdout](PROJECT/2-WORKING/GH-67-JEV-PURPOSE-ZERO-SHOT.md) — active 2026-09-18; Lane A of [XYZ-forge #709](https://github.com/HiQS-Labs/XYZ-forge/issues/709). ([#67](https://github.com/HiQS-Labs/Needle-fork/issues/67))
- [Codex app shortlist and optional feedback](PROJECT/2-WORKING/CODEX-NEEDLE-FEEDBACK.md) — #63 planning and Agy QA; app connection proof must precede implementation. [Source recon](PROJECT/2-WORKING/RECON-CODEX-FEEDBACK.md).

- [ZCode mapper recon and qualification](PROJECT/2-WORKING/RECON-ZCODE-MAPPER-CORRECTION.md) — PR #40 merged the scoped corrections; fresh blind qualification remains open in [#37](https://github.com/HiQS-Labs/Needle-fork/issues/37).

- [Label correctness audit — make the §2 gate trustworthy](PROJECT/2-WORKING/LABEL-CORRECTNESS-AUDIT.md) — source identity and disjoint manifests are merged; #25 clears its 30-session floor but remains blocked because the frozen sampler can allocate only 541/1,000 evaluation rows under its label quotas and session cap. ([#20](https://github.com/HiQS-Labs/Needle-fork/issues/20), [#23](https://github.com/HiQS-Labs/Needle-fork/issues/23), [#25](https://github.com/HiQS-Labs/Needle-fork/issues/25))

### Completed

- [GH-77: Jev next-action follow-ups — stability, wording, richer state](PROJECT/3-COMPLETED/GH-77-JEV-NEXT-ACTION-FOLLOWUPS.md) — identical requests score 18–20 (17/100 rows flip); wording no effect; real issue text +9 (28), last tool result +2 more (30, inside noise); Markov-1 37 on the same rows. ([#77](https://github.com/HiQS-Labs/Needle-fork/issues/77))
- [GH-66: Needle 3 six-action pilot with enum extraction](PROJECT/3-COMPLETED/GH-66-NEEDLE3-PILOT.md) — Needle 3 L20 LoRA 28/100 vs Markov-1 37; falsifier (< 42%) triggered, arm stopped. Rung L7 27, untuned base 20, Jev zero-shot 21 on the same rows. Branch `experiment/needle3-pilot`, nothing lands on `main`. ([#66](https://github.com/HiQS-Labs/Needle-fork/issues/66))
- [GH-69: fresh 100-row consensus sample for the Jev classifier](PROJECT/3-COMPLETED/GH-69-JEV-FRESH-SAMPLE.md) — purpose 88/100, pre-registered confidence gate met (97.3% at ≥ 0.8, 75% coverage); area 60/94, not ready. Three-model consensus labels, no human gold. ([#69](https://github.com/HiQS-Labs/Needle-fork/issues/69))
- [Top-three shortlist feasibility](PROJECT/3-COMPLETED/SHORTLIST-FEASIBILITY.md) — #62 failed fixed lift gate despite better coverage; park count-based shortlist, no prototype.

- [Private-trained transition comparison](PROJECT/3-COMPLETED/PRIVATE-TRANSITIONS.md) — historical failed gates preserved from #48 without reimporting code; [preservation receipt](TESTS-RESULTS/2026-09-11-private-transitions/PRESERVATION.md).

- [Versioned context refresh and fresh-issue comparison](PROJECT/3-COMPLETED/CONTEXT-REFRESH.md) — both rounds completed; negative fixed-model comparison, verified tool-free client fix, no training. ([#59](https://github.com/HiQS-Labs/Needle-fork/issues/59), [#60](https://github.com/HiQS-Labs/Needle-fork/issues/60))

- [Test runner mapping correction](PROJECT/3-COMPLETED/TEST-RUNNER-MAPPING.md) — unittest execution and unambiguous metadata probes corrected; no old-data writes. ([#56](https://github.com/HiQS-Labs/Needle-fork/issues/56))

- [Panel source audit](PROJECT/3-COMPLETED/PANEL-SOURCE-AUDIT.md) — all 12 source/chronology checks passed; defects and context/taxonomy limitations recorded. ([#53](https://github.com/HiQS-Labs/Needle-fork/issues/53))

- [Seven-model next-action panel](PROJECT/3-COMPLETED/NEXT-ACTION-PANEL.md) — locked predictions scored; Gemini 3.1 Pro review reconciled; no milestone pass. ([#52](https://github.com/HiQS-Labs/Needle-fork/issues/52))

- [Context-aware next-action prediction](PROJECT/3-COMPLETED/CONTEXT-NEXT-ACTION.md) — bounded attempt completed; context signal present but NB follow-up rule failed. No further tuning/serving. ([#51](https://github.com/HiQS-Labs/Needle-fork/issues/51))

- [Phase 2 §1 — Freeze the v1 Oracle label taxonomy](PROJECT/3-COMPLETED/PHASE-2-LABEL-TAXONOMY.md) — v1 published as `oracle/labels-v1.json`; current Studio corpus has 71,763 calls at 96.41% mapping coverage. ([#1](https://github.com/HiQS-Labs/Needle-fork/issues/1))

### Deferred

- No deferred docs.

---

*Add new work here only when a real `PROJECT/**` doc exists to own the execution detail.*
