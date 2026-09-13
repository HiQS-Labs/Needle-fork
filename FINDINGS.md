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

### Historical next action — superseded by the 2026-09-12 entry below

One private-trained round with unchanged Markov-1 and phase-backoff. The same family must beat
repeat-last by five points overall and the training-derived conditional destination comparator by
ten points. Report ordinary transition accuracy too: a destination score conditioned on a true
switch does not demonstrate detecting that switch at inference time. Both passing earns a
prospective serving-experiment design; partial success supports considering a narrower question;
both failing stops investment in these two models at this representation. These are resource
decisions, not universal impossibility claims or measured human acceptance rates.

### Publication state (historical)

The active checkout `audit/23-error-causes` was 50 commits behind freshly fetched `main` and had
no unique commits. PR #42 targets `spike/mlx-finetune`; its branch differs from current `main`
across 147 files, including historical divergence. Do not promote that whole branch solely to
publish this story. This documentation update is based on current `main`; experimental code
promotion requires a separately scoped integration review.

## 2026-09-12 — context-aware next-action pivot (#51)

The private-trained round previously described as pending completed: phase-backoff scored 45.73%
overall versus 43.52% repeat-last, below its 48.52% gate; conditional destination accuracy was
40.81%, below 40.86%. Both gates failed. This is reused development evidence, not acceptance.
[Retained receipt](https://github.com/HiQS-Labs/Needle-fork/blob/7f521b449c9d0f8351fdfc32c8c7180a44cbcf9f/TESTS-RESULTS/2026-09-11-private-transitions/SUMMARY.md).

Manual discovery #49 stopped at the operator's request because of time burden: one eligible
request, zero ratings, one missing rating, no skips or ties. This says nothing about preference
between the suggestions; no rejection or acceptance label is inferred.

The operator authorized [#51](https://github.com/HiQS-Labs/Needle-fork/issues/51): retain the same
six next-action targets but add task text and the latest completed tool observation. The old
OpenHands converter retained task text and actions but discarded observations; the transition
predictor ignored task text too. That loss of context is confirmed in source, but whether restoring
it improves prediction is a hypothesis, not a finding. The earlier 500/100-action LoRA pilot used
this exact dataset and already filtered successful trajectories; it did not exhaust the dataset.

Planned at pivot time (completed below): one CPU-only text-classifier comparison against same-row action-only baselines and a
context-shuffle control. See the [protocol](PROJECT/3-COMPLETED/CONTEXT-NEXT-ACTION.md).
No manual labeling, model download, neural campaign, deployment claim, or #43 modification.
Main-first scoped commits/pushes supersede the branch-per-experiment default; old branches are
preserved, not wholesale merged or deleted.

### Same-day measured outcome

#51 completed one frozen run at `1bee790`: 10,000 train actions / 224 issues, 3,000 eval actions /
68 disjoint issues. Context NB 49.67%, action-only NB 46.83%, shuffled context 41.80%, phase-backoff
52.10%. Context improves its own-family top-1 and aligned-versus-shuffled comparison, but the
strongest-baseline margin is -2.43pp and macro-F1 drops from 0.4204 to 0.4072. Follow-up rule failed;
no tuning or serving followed. This dataset supplied usable examples for all six labels, but the
fixed text model did not beat the simple baseline. No claim of user usefulness or private transfer.

Two pre-fit refusals (unsupported macOS memory limit, then an empty source command) were retained
and fixed before the sole scored run. Snapshot extraction/fitting/scoring took 6.00 seconds and
~271 MiB peak RSS; acquisition occurred earlier. Tests: 441 passed, 6 skipped. Full pooled results,
selection caveats and red-control evidence: [receipt](TESTS-RESULTS/2026-09-12-context-next-action/SUMMARY.md).

## 2026-09-12 — seven-model next-action panel scored and reviewed (#52)

Seven locked responses supplied 210 predictions on the same 30 public examples
from 30 issues in #51's development partition. Fable 18/30 (60.0%), GLM 15/30,
Astra and Gemini Flash 14/30, Qwen 12/30, DeepSeek 11/30, Tencent 9/30.
Unchanged phase-backoff scored 14/30 (46.7%); Markov-1 12/30, repeat-last 9/30,
majority 7/30. Fable beat phase-backoff on six rows and lost on two: net four,
not established statistical superiority or a milestone pass.

All seven missed nine cases. Seven cases were unanimous, six correct and one
wrong; at least one model was correct on 21/30, an oracle bound, not an ensemble
result. True labels include zero Git actions and only one edit. Six-label macro-F1
retains zero for unsupported Git for every predictor. No general six-label
capability, personal preference, private-domain transfer or human acceptance claim.

The operator-requested relay-xyz review used its one-shot consult path with Agy
Gemini 3.1 Pro, high effort, and completed with one answer and no worker failures.
Adopted its recommendation to audit before more calls or training. Did not adopt
its proposed macro-F1 denominator change: uniformly removing Git scales every
score by 6/5 without changing the ranking. Its assertions that the top score is
a statistical artifact and that disagreement proves noisy labels are unestablished.
Its count of ten failures double-counted the one unanimous error within nine misses.

Task/observation truncation and the distinction between named tests and ad-hoc
verification commands are plausible failure sources, not diagnosed defects.
[#53](https://github.com/HiQS-Labs/Needle-fork/issues/53) tracks a proposed audit of
nine shared misses plus three controls, using retained raw events. No manual user
ratings or new model calls required. Audit not started; old gates and #43 hold stand.

Verification: frozen source/selection/response hashes, nonempty inputs, train/issue
separation, original baseline-score replay, independent confusion arithmetic,
malformed-input and wrong-prediction red controls, identical scorer replay.
441 non-slow tests passed, 6 skipped, 11 deselected; worker and consult harness suites
each passed 62/62. Public [receipt, scorer and aggregates](TESTS-RESULTS/2026-09-12-next-action-panel/SUMMARY.md);
raw per-case inputs and transcripts remain ignored locally.

## 2026-09-12 — bounded panel source audit (#53)

Completed the frozen 12-event inspection: nine original all-seven misses and three
controls. The later MiniMax seat (#54: 10/30, one original shared miss correct)
did not change selection. Verified the retained source digest, original score
replay, unique raw next calls, matched prior results, chronology and exact feature
projection. All 12 source alignments passed; no observed answer-key/row mix-up.

Confirmed two Bash classification defects and filed
[#56](https://github.com/HiQS-Labs/Needle-fork/issues/56) immediately. A unittest
suite runs tests but maps to run_command; a pytest version probe only prints
metadata but maps to run_tests. These affect two audited targets. The unittest
defect also affects one other event's previous action, not its correct search target.
The cause is the shared taxonomy's named-test matching, not source chronology.
No fix or retroactive relabeling performed.

Primary triage of the nine misses: two target-mapping defects, three coarse
taxonomy boundaries, two material context-loss cases, two behaviorally unresolved.
These are coordinator judgments, not independent human labels or proven causes;
secondary caveats overlap. Native editor directory-view maps to read; ad-hoc
assertion scripts map to run_command. Those boundaries need an explicit policy,
not silent changes to make model votes correct. The unanimous edit prediction's
actual target is a real pytest run; the full prior error-bearing response was visible.

All 12 tasks are clipped, ten inside the issue description. Five observations are
cropped (three misses, two controls; one control loses only six characters).
Two missed pytest contexts lose test identity while retaining roughly 81% separator
padding. A different generic-success observation omits that its preceding command
was cleanup. Previous structured call arguments are absent by feature design.
These are information losses, not measured evidence that restoring them improves
prediction. The purposive audit cannot estimate dataset-wide error prevalence.

Verification: 441 non-slow tests passed, 6 skipped, 11 deselected; wrong prior-result
ID and target-call substitution controls invalidate the original row, while changing
the future target result leaves the pre-action row unchanged. Published
[aggregate receipt and replay](TESTS-RESULTS/2026-09-12-panel-source-audit/SUMMARY.md),
retained raw events/annotations locally. Next is scoped #56 correction before more
model investment, not another training run. Original #51/#52/#54 scores and prior
gates remain unchanged; #43 remains held.

## 2026-09-12 — test-runner mapper correction (#56)

Corrected the two confirmed execution/metadata defects in the existing shared
label_segment seam. Effective unittest invocations map run_tests; unambiguous
pytest/unittest help and pytest version probes map sys_inspect, projected to
run_command. Metadata recognition is deliberately narrow, not a full CLI parser:
arbitrary option values or positionals do not trigger the metadata-only exception.
Native editor labels and ad-hoc-script policy are unchanged.

Debug-mantra regression work witnessed the pre-fix failures. The initial patch
bypassed an environment-prefix mutation guard; fixed by respecting the existing
command-position check. One new compound expectation was corrected to preserve
the existing equal-tier first-segment tie-break, rather than changing precedence.
Final focused suites: 263 passed. Non-slow suite: 468 passed, 6 skipped, 11 deselected.

A read-only differential across 16 Bash calls from #53's 12-event evidence changed
exactly three: two unittest invocations and one pytest version query. All 13 frozen
panel artifact/code hashes still match. No re-extraction, model call, training or
score revision. Historical #53 replay belongs at pre-fix f225278; do not update its
expected old labels to the new mapper. [Receipt](TESTS-RESULTS/2026-09-12-test-runner-mapping/SUMMARY.md).
Next is a separately scoped/versioned data refresh and bounded follow-up decision;
remaining directory-view and ad-hoc-verification semantics are not settled by #56.

## 2026-09-12 — versioned context refresh (#59, round one)

Prepared q3 as a bundled, opt-in context change: issue-focused task text, separator
compaction before observation clipping, and last completed call identity/selected
arguments. Target/future details remain excluded. Retained mechanical view/read and
ad-hoc-script/run_command policy; the quiz states it rather than guessing intent.

The verified retained snapshot supplies 10,000 train rows/224 old training issues and
1,722 eligible rows/40 issues absent from both old partitions. Freeze one target-blind
transition per fresh issue: command 10, read 10, edit 8, tests 6, search 6, Git 0.
Both context views use identical corrected targets/histories. The #56 mapper changes
149 training targets and 1,421 histories, not the frozen old data or its scores.

Full source q2 output stayed byte-equivalent (55,942 transitions); all 13 frozen panel
hashes unchanged. Repeated preparation matched all 10 generated packet/data hashes.
Witnessed red/green format tests and failing future-leakage/wrong-join mutations;
486 non-slow tests passed, 6 skipped. [Receipt and manifest](TESTS-RESULTS/2026-09-12-context-refresh/SUMMARY.md).
No prediction accuracy yet. Next is one fixed Qwen comparison, tool-free HTTP,
old/refreshed/shuffled context, <=$1 worst-case token-cost preflight and the operator's
two-hour total wall bound. No new training, human-acceptance claim or #43 changes.

## 2026-09-12 — fresh-issue context comparison (#59, round two)

The bundled context refresh did not qualify. On one transition from each of 40
previously unevaluated source issues, fixed Qwen scored q3 21/40 (52.5%), q2 23/40
(57.5%), shuffled q3 21/40 (52.5%). Markov and phase-backoff each scored 24/40 (60%).
q3 macro-F1 .3983 trailed q2 .4129 and phase .4820. q3 had zero newly correct cases
versus q2 and lost two. Recall included search 0/6; Git had no support. The binding
follow-up accuracy threshold was 65%, five cases above q3's result. No near-pass.

Corrected mapper labels/histories were identical between arms; packets and responses
were locked before scoring. Direct HTTP sends no tool schemas or files and never
dispatches response text. Two initial requests rejected disabled reasoning (HTTP400);
filed #60, witnessed its request test fail, enabled low reasoning and publicly amended
the infrastructure retry bound before any valid predictions. Same model, cases,
temperature, 4096 total output tokens and decision thresholds; no further retries.
All three corrected requests completed; reported inference cost $0.180610, 188.02
seconds total. Validation failures reported no token usage; CLI review dollar cost
is unavailable. Do not compare this fresh quiz numerically to the old panel as a model
improvement: samples, prompt policy and inference settings differ.

493 non-slow tests passed, 6 skipped. Replay matched; independent confusion arithmetic
and retrained action-table vectors matched. Wrong predictions fail the rule; tampered
locks/packets fail verification. All 13 frozen panel hashes remain unchanged.
[Receipt, limitations, protocol adaptation and aggregates](TESTS-RESULTS/2026-09-12-context-refresh/ROUND2.md).
Stop model investment in this exact refresh, not the entire project. Before another
campaign, decide whether exact observed-action prediction is the right product target;
action-change detection or plausible-next-step ranking are unvalidated alternatives
requiring separate scope. No neural training, human acceptance or deployment claim.

## 2026-09-12 — evidence preservation and prototype decision (#48 / #62)

Preserved #48's historical plan and two aggregate receipts on main at `bf6c196`,
with byte-identical summary/metrics and only two explicit archival plan annotations.
All four files, including the preservation receipt, were fetched at the landing
SHA through GitHub and matched local bytes. Nonempty counts/percentages verified;
altered-count, empty-group and false-pass controls rejected. Predictor/test blobs
already matched main. 493 non-slow tests passed, 6 skipped. Closed #48 without
merge or branch deletion; #43 remains the sole open PR, unchanged and held.
[Preservation receipt](TESTS-RESULTS/2026-09-11-private-transitions/PRESERVATION.md).

Scoped, but did not run, a one-hour top-three count-based comparison using #59's
10,000 training rows and 1,722 development rows across 40 reused issues. This is
a different exploratory endpoint, not a retroactive pass or human usefulness test.
One-shot consult returned 2/2: Codex CLI Sol High favors the check before a demo;
Agy favors parking entirely. Both advise against a demo now. Corrected Agy's
40-case versus 1,722-row misread and its equation of label-space coverage with
observed hit rate; retained its legitimate proxy-value concern. Rejected the
inference that no time for ratings proves no capacity to benefit from suggestions.

Coordinator recommends one capped kill test, adopting issue wins > losses while
keeping the one-hour bound. No shadow daemon, new data collection or expanded
training/model campaign; execution still awaits operator decision. A pass could
only reopen discussion of a separately scoped interaction study, not qualify an
Oracle. Skills influenced this by requiring a grounded, additive scope and an
explicitly reconciled disagreement, not a claimed model consensus.
[Scope](PROJECT/3-COMPLETED/SHORTLIST-FEASIBILITY.md) and
[consult provenance, limitations and adjudication](doc/shortlist-prototype-consult.md).

## 2026-09-12 — top-three shortlist check (#62) completed, park

Operator authorized the recommended one-hour check. Implementation froze at
`06b3bfb` before one count fit and locked prediction/score run on 10,000 training
rows / 224 issues and 1,722 development rows / 40 reused issues. Phase achieved
89.3789% issue-macro hit@3 versus strongest control Markov 85.1211%; +4.2578pp
missed the fixed +5pp rule by 0.7422pp. Macro recall improved 2.8824pp, with
34 issue wins / 3 ties / 3 losses. Two gates passed, but overall decision is park.

Pooled hit@3: phase 1,540/1,722 (89.43%), Markov 1,469/1,722 (85.31%), static
69.05%, repeat-plus-priors 75.03%, permuted-history phase 61.50%. History has a
narrow ranking signal; extra phase detail did not clear the chosen investment
margin. Edit recall fell from 98.58% to 90.04%; Git change coverage was 1/21.
High aggregate coverage is neither human acceptance nor a concrete next-step plan.

17 focused / 510 non-slow tests passed, 6 skipped; five in-memory mutations
witnessed red then green. Trusted input checks, old top-one parity, lock replay,
independent row/label/issue arithmetic and tamper controls passed. All 13 old
panel hashes and 10 #59 artifact hashes unchanged. Runtime 1.733 seconds; peak
RSS 197.4 MiB. No training, model API calls, manual calibration or PR #43 change.
[Receipt and reproducible locked-score replay](TESTS-RESULTS/2026-09-12-shortlist/SUMMARY.md).

Follow the frozen stop: park this count-based shortlist, no retuning or automatic
prototype. Broader product usefulness remains unproven; reopening requires a
separate concrete product question and explicit authorization, not another score
on this development set. This is learning where further complexity is not yet
justified, not a claim that all next-action ideas are impossible.
