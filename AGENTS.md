# AGENTS.md

## Danger: commands agents must not run

- Never run `git reset --hard`, `git checkout -- <path>`, or a tree-wide `git stash` in a checkout
  whose state matters — they overwrite tracked work or hide state you or the operator still need.
  `git checkout -- <path>` restores **HEAD**, not the state before your edit; to undo your own
  experiment, copy the file first (`cp f f.bak`) and restore from that instead.
- Never run `rm -rf`, `find ... -delete`, or equivalent recursive cleanup through an empty,
  unresolved, relative, root, home, or otherwise unproven target path. Validate the path is a
  resolved, non-empty descendant of the intended directory immediately before the dangerous call —
  an empty variable does not fail: `git -C ""` uses the current directory, `cd ""` is a no-op,
  `rm -rf "$VAR/"` becomes `/`.
- Never force-push, rewrite history, or delete a git tag/branch on `origin` (`HiQS-Labs/needle-fork`)
  without explicit confirmation for that specific action.
- Never push to `upstream` (`cactus-compute/needle`). This fork's work lands on `origin` only.
- Never run a mutation-heavy or long training/finetune suite in a checkout whose state matters if it
  writes checkpoints, caches, or git state as a side effect — prefer a disposable clone or scratch
  directory for anything that downloads large artifacts or mutates `~/.cache/cactus-needle/`.

> **Safety and warranty:** this project is provided **"AS IS," without warranty**, under its Apache-2.0
> license. Coding models may choose commands through their own runtimes and safety controls, outside
> the intended workflow described here. Maintain tested, independent backups and follow
> industry-standard backup and recovery practices.

Read `GUIDING-PRINCIPLES.md` for the *why* — its "The North Star" and "Fork discipline" sections are
canonical and govern everything below.

Read `SOP.md` before running a finetune/quantization campaign, an eval sweep, or anything that
touches the daily PyPI release train.

Read `ARCHITECTURE.md` for the system map — entry points, the model/training stack, the runtime SDK,
and the implicit contracts (checkpoint format, `.cact` binary layout, hardcoded param paths) that a
change can silently break.

## What this file owns

This file is the behavioral playbook for work in this repo: decision quality, reversibility, blast
radius, planning shape, and proof. It does not restate the fork's *why* (`GUIDING-PRINCIPLES.md`) or
campaign-specific procedure (`SOP.md`).

## Operating principles

### 1. Lead with the line that survives skimming

Your first sentence gives the verdict, current state, or call. No setup first.

### 2. Make the bet explicit before acting

State the assumption, tradeoff, and failure mode that matter before you commit to a path. If a
future reader could not say "that assumption was wrong," you have not made the real bet legible yet.

### 3. Use one reversibility scale

Consequential changes get a read on the shared scale: **Easy / Costly / One-way door**, with one
line of why. If undoing it would take more than a day of focused work, it is at least Costly.
Costly changes need a rollback path. One-way doors — force-pushing `origin`, deleting a released
PyPI version's tag, restructuring the checkpoint format, reshaping code upstream still actively
maintains — need explicit confirmation before proceeding.

### 4. Size the blast radius before changing shared surfaces

Before a refactor, a change to `quantize.py`/`architecture.py`'s forward pass, a checkpoint-format
change, a dependency bump, or anything touching the `pyproject.toml` release surface, say what
ripples, what might break, and who notices (users pulling from PyPI, the daily release workflow,
anyone with a checkpoint trained on the old format). A change you cannot size is not ready.

### 5. One plan, one ordered list

When you give executable steps, put them in one numbered list in execution order. Keep verification
inline (`-> expect ...`). Do not scatter action items across prose.

### 6. Verified beats plausible

Do not claim success without the relevant test, script, or observable proof. If verification was
skipped or failed, say that plainly and include the result.

**A check that cannot fail is not a check.** A passing assertion is evidence only once you have seen
it fail: mutate the thing it guards — break the code, transpose the fix, delete the value — and
watch it go red. If you cannot make it fail, it is decorative, and it is worse than nothing because
it reports confidence it never earned.

**An empty input passes every check.** Before asserting anything about a benchmark result, an eval
score, or extracted data, assert that you actually got some: a failed command substitution yields an
empty string, a bad path silently returns zero rows, and a report generated from that looks CLEAN
against nothing. Size-check the artifact before trusting a verdict computed from it.

**Never expose the operator's machine to the network without asking.** Running the playground server
or the test suite is not permission to bind it to anything but `127.0.0.1`, and a tunnel or port
forward needs explicit permission each time.

### 7. Record only consequential bets

If a change is Costly, One-way door, or assumption-heavy, note the bet and its outcome somewhere a
future reader will see it — a CHANGELOG entry, the PR description, or a code comment at the seam.
Below that threshold, skip the ritual.

### 8. Stay quiet on trivial work

Most edits are small and reversible. Do not manufacture ceremony for a rename, typo fix, or other
local change.

## Repo-specific rails

- **This is a fork with an upstream, not a standalone project.** `origin` is `HiQS-Labs/needle-fork`;
  `upstream` is `cactus-compute/needle`, read-only. All work pushes to `origin`. Before a broad
  refactor, check whether upstream has moved the same files recently (`git fetch upstream && git log
  upstream/main -- <path>`) — reconciling a large local restructure against upstream drift is exactly
  the kind of Costly bet §3 asks you to name up front.
- **The daily release train is automatic and easy to trip accidentally.** `.github/workflows/release.yaml`
  runs on a cron gated to ~09:00 Pacific (plus manual dispatch): it runs `pytest -q -m "not slow"`,
  auto-bumps the patch version from the latest `vX.Y.Z` tag, builds, and publishes to PyPI as
  `cactus-needle`. A merge to the tracked branch is a release candidate whether or not that was the
  intent — keep `pytest -m "not slow"` green on every commit that could land there, and treat a
  version/tag bump as something that happened to a real, installable package, not a no-op.
- **Numerics-affecting changes are at least Costly by default.** `quantize.py`'s codebooks are shared
  bit-for-bit between JAX-side QAT and the `.cact` export path; `decode.py` and `export.py` both
  manually re-walk `architecture.py`'s Flax param-naming convention outside Flax itself. A change to
  any of these three needs an explicit statement that the others still agree with it — silent
  divergence there is a correctness bug that only shows up as a bad model, not a test failure.
- **Scratch and temporary files do not belong at the repo root.** Probes, one-off analysis scripts,
  captured output, half-written notes — anything you would not put in a commit — go in a gitignored
  scratch location (e.g. a `temp/` directory, or outside the repo entirely), not as `scratch-*.md` or
  `*.tmp` at the root. A file worth keeping gets promoted deliberately into `doc/`, `tests/`, or a
  commit — not left at the root for someone to puzzle over later.
- **Contain tree-touching subagents.** A session spawning subagents that will modify files in this
  repo should isolate them (a worktree or a separate clone) so a runaway destructive command hits a
  disposable checkout, not the tree you're working in. Read-only exploration doesn't need isolation.
- **Downloaded/generated artifacts are not source.** Engine binaries and weights fetched via
  `needle/agent/fetch.py` (cached under `~/.cache/cactus-needle/`), generated `.cact` exports, and
  JSONL training data are reproducible outputs — never hand-edit them in place or commit them as if
  they were source; regenerate via the documented CLI path instead.
