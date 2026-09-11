# Findings Log

Append-only log of investigation sessions on this repo. Each entry records process (what was run, by what) and results, with timestamps.

---

## 2026-09-06 — Architecture recon + prior-experience check

### Process

- **20:26 UTC** — Indexed `needle-fork` into the codebase-memory knowledge graph (`index_repository`, mode `full`). Result: 810 nodes, 3046 edges, 40 Python files, 0 skipped/parse-partial. 4 binary assets excluded by design (`.svg`/`.png`).
- **20:32 UTC** — Pulled graph-level architecture summary (`get_architecture`, aspects: structure/routes/layers/clusters/file_tree/boundaries) to scope the fan-out: identified 4 entry points, 7 HTTP routes, 8 env vars, 1 external package dependency (`huggingface_hub`).
- **20:35 UTC** — Ran `/recon` (adapted for a whole-repo architecture doc rather than a change-blast-radius map) with 3 parallel Sonnet subagents (`Explore` type), each read-only, ~8 min budget:
  - Lane 1 — model/inference core (`needle/model/*`, `_worker.py`, `_telemetry.py`)
  - Lane 2 — agent + environments + CLI (`needle/cli.py`, `needle/agent/*`, `needle/environments/*`)
  - Lane 3 — playground + contracts + build (`needle/playground/*`, `pyproject.toml`, `.github/workflows/release.yaml`, `doc/*`, `tests/` inventory)
- **20:52 UTC** — All 3 lanes completed and reconciled into `ARCHITECTURE.md`.
- **20:53 UTC** — Ran a 4th research agent (Sonnet, `Explore`) against the local clone of `rebalanceOS` (`Hypercart-Dev-Tools/rebalance-OS`, at `/Users/noelsaw/Documents/GH Repos/rebalanceOS`) to find this team's prior experience with Needle on the "3-Eyes" project — `git log --grep`, repo-wide `grep -i` for "needle" and "3 eyes" variants, and a read of the PDDA `PROJECT/` archive.

### Results

**ARCHITECTURE.md** written to repo root — full breakdown of the model/training stack (JAX/Flax `SimpleAttentionNetwork`, Hadamard MLP, Engram side-channel, mHC layer mixing), the runtime SDK + native-engine subprocess worker, agent tooling, environments, the playground HTTP server, cross-cutting contracts (checkpoint format, `.cact` binary, env vars), build/release, and test coverage. One dead code path flagged: `needle/model/export.py:536` (`main`, unreferenced). A second claim — that `needle/environments/*` was unwired from the test suite — was **retracted in the QA pass below**.

**Prior Needle experience — "3-Eyes" project (rebalanceOS / Hypercart-Dev-Tools predecessor repo):**

| Date | Event |
|---|---|
| 2026-07-22 | 3-Eyes (GH-195) designed and merged: a unified supervisor meant to absorb three pre-existing sentinels — an XYZ debug flywheel, a **Cactus Needle** PDDA sentinel, and Rebalance collector-health — under one system. |
| 2026-07-27 | **Cactus Needle stack disabled and deleted** (`sentinel-daemon`, `sleuth-app`, `needle-router`, `cactus-serve` — the Needle SLM OpenAI-compatible server on :8081) — retired as "superseded by 3-Eyes," before the migration/adoption step for it was completed. |
| 2026-07-28 | 3-Eyes' own audit doc flags this as a gap: the "adopt Cactus-Needle" phase is declared unachievable/superseded, since Needle no longer existed to adopt. |
| 2026-08-16 | 3-Eyes carried into the current `rebalanceOS` repo's tracked history as an exempted "standalone package" during a repo-wide refactor. |
| 2026-08-17 | 3-Eyes itself found unstable in CI and **stood down** — pulled from CI, jobs unloaded, code left in place but not repaired. |

**Verdict (3-Eyes):** Needle was not adopted as a long-term component — it was a legacy local-model server that 3-Eyes intended to absorb, but got deleted first (2026-07-27) as organizational churn, not due to a documented technical failure of Needle itself. No lessons-learned doc frames it as a Needle defect. 3-Eyes, the system meant to replace it, was itself later stood down as high-maintenance/low-value. Net takeaway for this repo: no reusable integration pattern or blocker specific to Needle survives from that project — the prior attempt never reached the point of exercising Needle's actual capabilities before being cut.

---

## 2026-09-06 21:25 UTC — QA review of the recon output

### Process

Independent verification pass (Opus) over the three documents produced above, re-checking every
load-bearing claim against source rather than against the subagent reports they came from. Method:
targeted `rg`/`sed` reads of `needle/cli.py`, `needle/model/export.py`, `tests/`,
`.github/workflows/release.yaml`, and a full sweep of `os.environ`/`getenv` call sites under
`needle/`. Verified at `33f3589`.

### Results — 4 defects found and fixed

1. **`ARCHITECTURE.md` contradicted itself on `needle/environments/` test coverage, and one side was
   wrong.** One section claimed the modules were "not wired into the CLI, SDK, or any test suite";
   another correctly noted they have contract tests. Ground truth: `tests/test_environments.py:6`
   imports `from needle import environments` and runs a full contract suite (registry/module
   agreement, tool surface, category coverage, tool execution, smoke). **Root cause: a false
   negative from a recon lane** whose repo-wide `grep` reported zero matches for a string that is
   plainly present — the known `grep --include` → ripgrep shim trap, which prints "0 matches" for a
   search that never ran. Fixed in `ARCHITECTURE.md`; the "dead/orphaned code" framing of
   `environments/` was retracted entirely.
2. **The environment-variable inventory was incomplete and wrongly presented as exhaustive.**
   `ARCHITECTURE.md` stated "8 env vars," a figure taken from the knowledge graph's `EnvVar` node
   count rather than from source. A direct sweep found four more the list omitted:
   `NEEDLE_STRICT_VALIDATE` (`environments/_harness.py:12`), `ENABLE_PJRT_COMPATIBILITY`
   (`model/finetune.py:13`), and `TF_CPP_MIN_LOG_LEVEL`/`GRPC_VERBOSITY` (`cli.py:109-110`). Replaced
   with a source-verified list grouped by role, distinguishing vars *read as config* from vars *set
   as defaults*.
3. **Every example command in `SOP.md` was wrong** — the most serious finding, since that file is
   operational guidance and had already been committed and pushed. The commands were written from
   plausible-looking inference, not from `needle/cli.py`. Actual syntax: `needle run` takes
   `--checkpoint` (a **`.pkl`**, not a `.cact`) and `--query`, not a positional path and `--prompt`;
   `needle finetune` takes the JSONL path **positionally**, not via `--data`; `needle build` takes
   the checkpoint **positionally**, not via `--checkpoint`, and `--bits` accepts only `2` or `4`. The
   Step 5 verification command was doubly wrong — it tried to load a `.cact` through `needle run`,
   which cannot read one. Replaced with verified invocations plus a real `.cact` verification path
   (`export.read_export` for the structural round-trip, `needle.Needle(weights=...)` or
   `needle playground --weights` for behavior).
4. **`FINDINGS.md` inherited defect 1** in its own results summary; corrected above.

### Claims re-verified as correct (no change needed)

- `needle/model/export.py:536` (`main`) really is unreferenced: absent from `cli.py`, absent from
  `pyproject.toml`'s `[project.scripts]`, and the module has no `if __name__ == "__main__"` block,
  so no `python -m` path reaches it either. The rest of `export.py` is live (`write_export` is
  called from `finetune.py:441,479`; `read_export` is exercised by two test files).
- No test references the playground at all — `rg 'playground|_Handler|load-model|finetune/status'
  tests/` returns nothing, so the HTTP layer is covered only indirectly.
- The release workflow behaves as documented: twice-daily cron plus `workflow_dispatch`,
  `pytest -q -m "not slow"`, `sed` patch bump of `pyproject.toml` + `needle/__init__.py`,
  `twine check`, `pypa/gh-action-pypi-publish`, tag push — and it deliberately keeps the
  release-only commit on the tag rather than writing to `main` (`release.yaml:96-97`).

### Lesson for future recon in this repo

Two of the three lanes reported that they skipped the knowledge graph and worked from direct file
reads — which is the stronger method and is why their findings mostly held. The one materially wrong
finding came from a **search tool silently not running**, not from bad reasoning. Treat any
"0 matches" result as unconfirmed until re-run in a form known to work, and treat knowledge-graph
counts (node totals, `EnvVar` counts, "entry points") as leads to confirm, never as inventories to
publish — the graph also listed `export.py:main` as an entry point, which it is not.

---

## 2026-09-11 — Oracle experiments and revised next milestone

### Process

Reconciled the current GitHub issue #1 and child-experiment reports, `main`'s CHANGELOG,
PRs #42/#43, and the completed Astra/Fable AgentChorus #743999. Earlier entries above are historical;
this append supplies the missing experiment arc. See the [collaborator briefing](doc/oracle-collaborator-summary.md)
for a compact narrative and source links.

### Findings

- The overall umbrella is [XYZ-forge #467](https://github.com/HiQS-Labs/XYZ-forge/issues/467).
  [Needle-fork #1](https://github.com/HiQS-Labs/Needle-fork/issues/1) owns the Oracle implementation
  and running experiment record; its original plan and later comments include superseded decisions.
- Training/export plumbing has run, but ranking accuracy did not establish useful native serving.
  Issue #12 records the five-of-44-tool retrieval limitation in the tested serving contract.
- Label resolution is not correctness: the 399-row audit estimates 77.84% population-weighted
  correctness. Issue #25's fresh 1,000-row evaluation remains blocked at 541 selectable rows under
  its unchanged capacity and label constraints. These are different datasets from the older,
  larger private corpus used in the exploratory six-label experiment.
- Six-label LoRA: 27% on 100 OpenHands development rows versus 37% Markov-1; stopped.
  Phase-aware backoff: 42% on that development set, then 25.23% on 23,442 eligible private rows
  across 63 sessions, versus 28.78% OpenHands-fitted Markov-1 and 43.52% repeat-last; stopped.
- Correction to earlier interpretation: repeat-last is a persistence comparator, not demonstrated
  recommendation usefulness. Poor OpenHands transfer does not establish that private-trained
  predictors fail. The private evaluation has now informed decisions and is reused development
  evidence, although excluded from fitting.
- The separate purpose-classification experiment (#31) and augmentation tooling (#41 / PR #43)
  are not next-action efficacy evidence. Neither supplies a deployment-ready Oracle.

### Agreed next action, not yet measured

One private-trained round with unchanged Markov-1 and phase-backoff. The same family must beat
repeat-last by five points overall and the training-derived conditional destination comparator by
ten points. Report ordinary transition accuracy too: a destination score conditioned on a true
switch does not demonstrate detecting that switch at inference time. Both passing earns a
prospective serving-experiment design; partial success supports considering a narrower question;
both failing stops investment in these two models at this representation. These are resource
decisions, not universal impossibility claims or measured human acceptance rates.

### Publication state

The active checkout `audit/23-error-causes` was 50 commits behind freshly fetched `main` and had
no unique commits. PR #42 targets `spike/mlx-finetune`; its branch differs from current `main`
across 147 files, including historical divergence. Do not promote that whole branch solely to
publish this story. This documentation update is based on current `main`; experimental code
promotion requires a separately scoped integration review.
