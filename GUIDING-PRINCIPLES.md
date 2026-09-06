# Guiding Principles

North star for `needle-fork`, our maintained fork of [`cactus-compute/needle`](https://github.com/cactus-compute/needle) (package: `cactus-needle`) — a small tool-calling model plus its JAX/Flax training, quantization, export, and runtime SDK. When a choice is unclear, the option that keeps the fork durable, reversible, and easy to reconcile with upstream wins. `AGENTS.md` is the behavioral playbook; this is the *why*. Adapted in spirit from XYZ Forge's guiding principles — the swarm/multi-agent machinery in that source doc does not apply here and has been dropped.

## The North Star

There is no perfect architecture and no finished codebase. The bar is not perfection — it is that
every change leaves this fork **more durable, more reversible, and less duplicated** than it found
it, and that the three stay in balance:

- **Durable** — it removes the root cause and the next planned change builds on it, rather than
  being torn out when the obvious next feature lands.
- **Reversible** — the cost of being wrong is known and bounded before the change lands. A change
  nobody can undo is a bet, not a fix, and gets treated as one.
- **DRY** — nothing canonical lives in two places where it can drift. One source of truth per
  concept, and every other surface is a pointer or a projection of it.

**Do not build a new module, subsystem, or parallel code path when an existing one can be extended
easily, logically, and safely.** This repo already has real, load-bearing implicit contracts —
the checkpoint format between `finetune.py` and `run.py`/`export.py`, the hand-rolled Flax param
paths that `decode.py` and `export.py` both re-walk, the `.cact` binary boundary to the native
engine (see `ARCHITECTURE.md`). Extending one of these beats standing up a second, similar one that
now has to be kept in sync. If an existing abstraction genuinely cannot carry the new case, say so
in one line, with the reason, before forking it.

These three pull against each other, and that tension is the decision, not a problem to average
away: the most durable fix is often the least reversible, and collapsing two near-duplicates is a
DRY win that can widen the blast radius. Name the trade and pick; do not split the difference by
building both.

## Fork discipline

This repo tracks an active upstream. Two remotes exist for a reason:

- `origin` (`HiQS-Labs/needle-fork`) is where our work lands. Push here.
- `upstream` (`cactus-compute/needle`) is read-only context — never push to it, and never assume
  our commit history, branch names, or release cadence are visible to it.

A fork-specific corollary to DRY: **minimize divergence from upstream's structure.** A change that
reorganizes files, renames public symbols, or reshapes a module upstream still maintains actively
makes every future `git merge upstream/main` (or manual reconciliation) more expensive. Prefer
additive changes and narrow, well-isolated edits over broad refactors unless the refactor is the
point of the work. When divergence is unavoidable, say so and note it somewhere a future merge will
be read against (a comment, a CHANGELOG line, or the PR description).

## The quality bar

Every change and every claim about this model is a signal. It is high-quality only when it is all
four:

- **Attested** — carries its receipts: which command was run, what the output was, what checkpoint
  or config it used. A benchmark, accuracy claim, or "it works" needs a runnable trail, not a bare
  verdict.
- **Relevant** — ranked, not dumped. One real regression beats five nits and a phantom.
- **Fresh** — current, not stale. A claim checked against a checkpoint, config, or doc that has
  since changed is wrong by construction — say what revision it was checked against.
- **Structured** — one clear shape, easy for the next reader (human or agent) to act on.

Fail a pillar, and the claim isn't done.

## How it's built

1. **Numerics are load-bearing; treat them like contracts, not implementation detail.** The
   quantization codebooks in `quantize.py` are shared, bit-for-bit, between JAX-side
   fake-quant/QAT and the `.cact` export path in `export.py` specifically so training-time and
   deployment-time numerics match. A change to one side without the other is a silent correctness
   bug, not a refactor — treat any change touching `quantize.py`, `architecture.py`'s forward pass,
   or the parameter-naming convention `decode.py`/`export.py` depend on as at least Costly (see
   `AGENTS.md` §3).
2. **Build durable, not band-aid.** Durable means it removes the root cause and the next planned
   change builds on it — not a patch torn out when the obvious next feature lands. A band-aid is
   wasted work unless a demo or upstream-sync deadline strictly needs one, and a demo band-aid is
   tagged for removal so it isn't silently inherited.
3. **Least code that clears the bar.** This is a 14MB model for tiny devices — the whole point is a
   small footprint. Prefer reusing or extending what exists; the smallest change that stays correct
   and durable wins. Net-new dependencies (this repo has exactly one runtime dependency,
   `huggingface_hub`) are a cost to justify, not a default. Deleting code counts as progress.
4. **Honest; the maintainer decides.** Surface what failed and why — never mask a stalled finetune
   run, a failed quantization, or a broken export as success. Destructive actions (force-push,
   history rewrite, deleting a checkpoint or release artifact) require explicit authorization.
5. **Done means verified.** "Done" is the relevant tests green (`pytest -m "not slow"` at minimum;
   `slow` end-to-end build/finetune tests when the change touches that path) and, for anything
   claiming a behavioral or numerical result, an actual run whose output is shown or committed —
   not work that looks finished.
6. **Issue-first for anything non-trivial.** A change beyond a small, obviously-safe fix gets a
   GitHub issue first, so there's a queryable record of why. Genuinely trivial edits (typos, doc
   fixes, a one-line dependency bump) are exempt.
7. **Independent verification.** The change that produces a result should not be the only thing
   that grades it. A test, a second read of the diff, or a separate benchmark run — something other
   than "I ran it and it looked right" — before calling a nontrivial change done.

## Applying this

Adding a feature or weighing a tradeoff, ask: *does this keep the fork mergeable with upstream,
does it keep the model's numerics honest end-to-end, and is "done" provable by running something?*
If any answer is no, reconsider.

---

## Appendix: Doc Review Heuristics

When reviewing a PR, plan, or architecture note in this repo, apply these. Priority: numerical
correctness > fork mergeability > signal quality > implementation speed.

1. **Numerics preserved across the training/export boundary?** Any change to `quantize.py`,
   `architecture.py`'s forward pass, or a parameter-naming convention that `decode.py`/`export.py`
   also depend on needs an explicit statement that both sides still agree.
2. **Fork drift justified?** A structural reorganization, rename, or reshaping of code upstream
   still maintains needs a stated reason, not just "cleaner this way."
3. **Done verifiable?** Names a runnable check (a specific test, a benchmark script, an actual
   `needle run`/`needle build` invocation) — none named is a low-quality signal.
4. **Drift reduced, not created?** No duplicated docs, no second implementation of a contract that
   already exists (checkpoint format, tool-schema compiler, `.cact` layout).
5. **Next action singular?** One explicit next step, not buried in prose.
6. **Destructive ops surfaced?** No silent force-push, history rewrite, or checkpoint/release
   deletion — these are called out before they happen, not after.
