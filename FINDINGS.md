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

**ARCHITECTURE.md** written to repo root — full breakdown of the model/training stack (JAX/Flax `SimpleAttentionNetwork`, Hadamard MLP, Engram side-channel, mHC layer mixing), the runtime SDK + native-engine subprocess worker, agent tooling, environments, the playground HTTP server, cross-cutting contracts (checkpoint format, `.cact` binary, env vars), build/release, and test coverage. Two dead/orphaned code paths flagged: `needle/model/export.py:main` (unreferenced) and `needle/environments/*` (functional but unwired into CLI/SDK/tests).

**Prior Needle experience — "3-Eyes" project (rebalanceOS / Hypercart-Dev-Tools predecessor repo):**

| Date | Event |
|---|---|
| 2026-07-22 | 3-Eyes (GH-195) designed and merged: a unified supervisor meant to absorb three pre-existing sentinels — an XYZ debug flywheel, a **Cactus Needle** PDDA sentinel, and Rebalance collector-health — under one system. |
| 2026-07-27 | **Cactus Needle stack disabled and deleted** (`sentinel-daemon`, `sleuth-app`, `needle-router`, `cactus-serve` — the Needle SLM OpenAI-compatible server on :8081) — retired as "superseded by 3-Eyes," before the migration/adoption step for it was completed. |
| 2026-07-28 | 3-Eyes' own audit doc flags this as a gap: the "adopt Cactus-Needle" phase is declared unachievable/superseded, since Needle no longer existed to adopt. |
| 2026-08-16 | 3-Eyes carried into the current `rebalanceOS` repo's tracked history as an exempted "standalone package" during a repo-wide refactor. |
| 2026-08-17 | 3-Eyes itself found unstable in CI and **stood down** — pulled from CI, jobs unloaded, code left in place but not repaired. |

**Verdict:** Needle was not adopted as a long-term component — it was a legacy local-model server that 3-Eyes intended to absorb, but got deleted first (2026-07-27) as organizational churn, not due to a documented technical failure of Needle itself. No lessons-learned doc frames it as a Needle defect. 3-Eyes, the system meant to replace it, was itself later stood down as high-maintenance/low-value. Net takeaway for this repo: no reusable integration pattern or blocker specific to Needle survives from that project — the prior attempt never reached the point of exercising Needle's actual capabilities before being cut.
