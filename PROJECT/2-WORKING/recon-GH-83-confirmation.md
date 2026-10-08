---
title: GH-83 confirmation recon
status: In progress
created: 2026-10-07
updated: 2026-10-07
owner: Codex
goal: Ground the artifact-local protocol extension.
gh_issue: 83
roadmap_exempt: true
---

# Recon Map — GH-83 confirmation

## Status

| What was just completed | What's next |
|---|---|
| GH82 runner, grader and evidence seams traced. | Apply the reviewed protocol within the same artifact boundary. |

Commit: baeb588ec1ec01b88d5663ed74244c7420af2fca · Mode: graph+source fallback · Lanes: A/B/C/D contained in parent.

## Subject and change class

Artifact-local runner/grader extension; controlled benchmark contract v2. No production caller.

## Seams

| Seam | Location | Crosses | Breaks if |
|---|---|---|---|
| CLI dispatch | TESTS-RESULTS/2026-10-07-gh82-3way-phase2/run.py:37 | packet/questions to Claude/Codex stdout and saved output | model/effort unsupported or metadata missing |
| Candidate isolation | same run.py:54 | external temporary git CWD, copied two files | key/history enters CWD or tool execution allowed |
| Evidence writer | same run.py:89 | exclusive raw files, receipts and parsed answers | empty/partial event output mistaken for success |
| Structural score | TESTS-RESULTS/2026-10-07-gh82-3way-phase2/grade.py:13 | JSON object + offline key to verdict/ID totals | new IDs break G03-only control or relevant-ID validity is mistaken for semantic grounding |
| Semantic review | same grade.py:2; review/final.json | independent prose judgement to /48 totals | equivalence and injection criteria drift after output inspection |
| Publication | SUMMARY.md / ROADMAP.md / GitHub #83 | artifact claims to remote issue | changed mean or ignored limitations misreported |

## Call paths and state

Operator -> run.py main -> fixed prefix + QUESTIONS + packet -> CLI subprocess -> raw events/stderr -> answer -> receipt. Packet/prompt hash asserted before dispatch; key/grader only compared in frozen artifacts, not asserted each call. Codex output path is outside candidate CWD; read-only instruction is not a proof of tool disabling. Claude tool/MCP/hook flags constrain runtime. Timeout catches exception but subprocess.run alone does not prove child-tree termination. Temp cleanup rmtree executes on freshly created parent; v2 validates target at use boundary.

Offline grade.py extract -> grade -> structural verdict/case-local ID checks; semantic evidence relevance and safety are reviewer work. Existing controls assume G03, hence require parameterization for fresh IDs. No product import/caller claim is made: these files are artifact-local entry scripts (read in full). Frozen legacy packet/key/results remain unmodified.

## Build, failure and rollback

Stdlib campaign scripts; Python 3.12 test/train extras for existing repo preflight. No new dependency or gate. Receipt contains requested settings, events, errors, timings and model usage; Codex has no returned backend model evidence. CLI flag acceptance is not independent identity/effort attestation. Invalid structure, tool events, process timeout or mismatch are explicit terminal statuses. Rollback abandons only this full clone; append corrections without editing historical results.

## Unknowns

Graph generation 2026-09-30 does not contain #82 paths: check_index_coverage reports missing freshness; exact source fallback performed. Pro Medium route support: settle with synthetic --effort medium probe + catalog/log. Haiku4.5 effort effectiveness: settle returned metadata/docs if available, otherwise unknown. Antigravity raw event/tool visibility: settle synthetic stream-json probe. System wrappers differ across CLIs; prompt SHA establishes explicit input equality only. Source consumers outside artifact reports were not exhaustively searched because no product module is touched.

## Current-state radius

Historical benchmark artifacts/report readers, coordinator filesystem and candidate CLI processes only; no product runtime or operational Git actor.
