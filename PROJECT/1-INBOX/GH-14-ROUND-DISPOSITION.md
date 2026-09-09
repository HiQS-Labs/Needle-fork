---
issue: 14
status: reviewed — round disposed as diagnostic/stop; implementation accepted with explicit limits
round_id: gh14-legacy-frozen-200
recorded: 2026-09-09
recorded_by: Claude Opus 5 (agent1), reviewed against GPT-6 Astra (agent2), AgentChorus #729301
decides: nothing outside #14; product decisions belong to #13 under their own frozen protocol
---

# GH-14 round disposition — the reviewed decision

This is the **round disposition**, the human half of #14. It is deliberately separate from the
machine report: a script establishes bounded structural and numerical facts, and a reviewer decides
what they support. **A completed review and sufficient evidence are different states.** This review
is complete and its evidentiary verdict is INCOMPLETE. Nothing here overwrites the machine report or
marks a judgment PASS.

## What this disposition is pinned to

| Thing | Identity |
| --- | --- |
| Code | `af10f61` on `spike/mlx-finetune` |
| Round configuration | `round_id: gh14-legacy-frozen-200` (private, `data/spike-mlx/round-gates-14/round.json`) |
| Machine report | `report.json` sha256 `16600e8be54a26e2bd7f89a462756c8ce61206f7230c032aafcf678798fc536a` |
| `audit_round.py` | sha256 `5d304983b4e11321d630bdab6b7859496028faf05825068f02d3ae3db7eaa616` |
| `oracle_scoring.py` | sha256 `0ae643412c19e3d286c9f17002bc934fb2b9f1cdfa5068b7b703bd1927a36b76` |
| Disposition | overall **INCOMPLETE**, deterministic **INCOMPLETE**, exit 2 |
| Suite | `pytest -q -m "not slow"` → 182 passed, 6 skipped, 6 deselected |

Regenerate with `python spike/mlx/audit_round.py --config <round.json> --outdir <FRESH>`. A changed
parser or configuration invalidates this disposition until replayed — that is the rule in
[`doc/experiment-rounds.md`](../../doc/experiment-rounds.md), and it applies to this file.

## Round decision

**Stop and bank the serving-contract diagnosis.** No fresh native collection, training run, or
enum pilot is authorised by this round. Both reviewers recommended it independently; the decision
is Noel's under SOP §4 and this document records it, it does not make it.

The diagnosis that is banked: the deployed-accuracy failure was a **serving-contract mismatch**, not
a quantisation defect. Training rendered all schemas inline; the engine injects exactly five. Three
harness defects (reused conversational engine, unpaired samples, credit-granting scorer) accounted
for the rest. That finding stands. **It is not a product claim** — no artifact here has been shown
to meet an accuracy, latency, or offline-use threshold, because no such threshold is frozen yet.

## Requirement disposition — met, or deferred with an owner and a reopen condition

Nothing below is checked off silently. A deferred requirement is *not* an implemented one.

| # | Requirement | State | Owner / reopen condition |
| --- | --- | --- | --- |
| 1 | Offline audit runs without MLX, weights, network, or new deps | **met** | — |
| 2 | Frozen-input controls and hand-calculated paired statistics; deliberate corruption produces the expected nonzero result | **met** | 8 red controls, each witnessed failing against pre-fix code |
| 3 | Current-task scoring rejects the known false-positive cases and retains raw evidence | **met** | Parameterless labels only; an enum tool needs a versioned scorer + new controls |
| 4 | New collection refuses overwrite and retains process/config/trace evidence | **met for new runs** | — |
| 5 | Legacy incompleteness is visible | **met** | All ten legacy arms lack raw generations and effective run metadata; reported, not repaired |
| 6 | Effective run provenance: engine binary, session identity, tokenizer attestation | **DEFERRED** | Reopens if a parity-dependent product decision arises. Recorded as explicitly `null`; never inferred from an artifact filename |
| 7 | G3 served-token semantics | **DEFERRED** | Not impossible — decoded traces support scoped claims. Reopens on a decision that depends on runtime prompt/position/tokenizer parity. No speculative probe now |
| 8 | G5 population inference | **reviewed, qualified** | Session assignment resolved for this manifest; independence of session *families*, confirmatory inference, and generalisation remain unestablished |
| 9 | G6 interpretation, dissent, next action | **met by this document** | — |
| 10 | Repeatable counts with an honest disposition | **met** | Byte-identical replays; exit 2 |
| 11 | SOP carries the reusable contract | **met** | SOP §6 → `doc/experiment-rounds.md` |
| 12 | Confidence intervals / power planning | **not required for a stopped diagnostic round** | Required *before* a new effectiveness experiment, with estimand, sampling unit and cap fixed in advance |

**#14 may close when Noel accepts rows 6, 7 and 12 as deferred.** It is not closed by this file.

## Corrected historical record

- **`e9e994f`'s scorer selected the FIRST tool-call block.** It had no multiple-*block* check; its
  `MULTIPLE` status covered multiple *calls inside one block*, via `_finish`. Two complete blocks
  returned `Verdict('a', ok)`. My published correction claiming otherwise was **wrong and is
  withdrawn** — see the struck-through paragraph in #14. It contradicted my own red-control receipt
  in the same comment. The real gaps at that commit were invalid argument shapes, duplicate JSON
  keys, and a trailing unclosed block.
- **Historical scores are unchanged.** The hardened scorer alters what *would* be scored; it does
  not retroactively rescore. Replay only where raw output exists; missing raw output is
  irrecoverable from a saved label.
- **The D10 McNemar table reproduces exactly** from the frozen receipts, across all ten arms and
  both comparators. The `search_code` and `read_file` rows are distinct and both are published;
  commit `5b1a125`'s one-line summary compresses them misleadingly, and rewriting pushed history is
  out of bounds, so it is corrected here instead.

## Session clustering — what it does and does not establish

`spike/mlx/session_clustering.py` recovers session provenance by replaying `serialize_query` over
`pairs.jsonl`. On frozen-200: all 200 rows assign to exactly one recorded session, across **29
sessions**, largest 37 rows, Kish mean cluster size 18.93.

**All six comparisons keep their conclusions under whole-session resampling.** The correct reading
is *"these six comparisons did not change under recorded-session resampling"* — **not** "independence
is proved" and **not** "no conclusion depends on independence", which was my overstatement and is
withdrawn. The bootstrap still assumes sessions are mutually independent and representative; ICC is
assumed, not measured; session IDs are path hashes, so a copied or branched source session can
appear as two IDs. The script is **exploratory and is not an enforced gate.**

## Open dissent — carried forward unresolved, for Noel

**R1: should exact train/eval query overlap be a hard rejection?** Both reviewers agree query
equality is **not proof of copying**, and that no fuzzy or near-duplicate matching is justified now.

- *agent1:* reject it, as a **declared query-disjoint protocol** — an identical input seen in
  training is a problem for a generalisation estimate whatever its provenance.
- *agent2:* that policy is valid when it matches the chosen estimand, but the universal
  justification is wrong — independent natural-use events can legitimately repeat observable
  inputs, and restricting to unseen inputs *changes what is being estimated*.

**Current default is agent1's** (overlap is a G0 FAIL), because it is the conservative direction and
trivially reversible. Measured on the real config: 0 of 200 either way, at full query coverage, so
the default binds nothing today. **Reopen before any round where the estimand is deployment
performance on naturally recurring inputs rather than generalisation to unseen ones.**

## Assumptions neither reviewer verified

Listed because an unverified assumption that nobody wrote down becomes a fact by default.

- Recorded session IDs correspond to **independent session families**. Path hashing does not
  establish it; a copied transcript yields a second ID.
- frozen-200 **represents a deployment population**. It has now been read many times; the
  adaptive-selection bias is known to exist and is not quantified. Not an untouched final test.
- The local tokenizer file hash is the **engine's actually loaded** tokenizer.
- **D7's MLX/PTQ punctuation degeneracy remains unreproduced.** A different QAT artifact succeeding
  is not its explanation. Evidence and replay recipe preserved; no replay required now.
- Any predictor meets a **frozen product threshold**. Diagnostic accuracy, valid JSON, and a small
  parameter count do not establish product utility.

## Reopen condition for the stop

A concrete pending product decision is shown to depend on **one named missing measurement**, and a
bounded probe can distinguish its alternatives within an agreed budget. **Discovering another
uncertainty does not qualify.** Any future enum pilot belongs under #13 with its own frozen protocol.
