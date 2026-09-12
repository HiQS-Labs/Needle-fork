---
title: Context refresh recon
status: Shipped
created: 2026-09-12
updated: 2026-09-12
owner: noelsaw1
goal: Ground the opt-in refresh in the existing offline extraction seams.
roadmap_exempt: true
---

# Recon Map — context refresh

Commit: main `68836f3`. Mode: grep-only, one local lane (no graph tool available).
Supersedes the pre-#51 map for this change; no package/runtime code is in scope.

| Seam | Current path | Change / preservation |
|---|---|---|
| Local source identity | `context_probe.retained_source` | Reuse revision, byte cap and SHA verification; no download. |
| Projection | `prepare_openhands.project_call` → `project_bash` → shared taxonomy | #56 corrected mapper, unchanged mechanical native-view/script policy. |
| Chronology | `trajectory_rows(context=True)` → `_context_rows` | One matched completed response; reset missing/parallel/control boundaries. Add opt-in formatting, not a second state machine. |
| Feature identity | `context_probe.signature` | Hashes task/observation/history; place completed-call identity inside q3 observation so existing overlap contract covers it. |
| Selection | `context_probe.prepare` | Existing old capped split excludes 169 first-resolved issues. New small offline runner reuses iterator/split/projection; restrict fresh eval to unused holdout IDs. |
| Baselines / metrics | `baselines.fit/predict`, `context_probe.metrics` | Training-only frequency counts and six-label metrics; no new NB fitting or new classifier library. |
| Artifact consumers | offline tests and receipts | Fresh ignored directories only; q1/q2, frozen panel hashes, runtime/packaging untouched. |

State: pending call stores ID/label/name; result joins on ID/name before feature
emission. User/control/invalid/parallel events invalidate the observed prefix.
q3 additionally stores a bounded prior-call description in pending state; never
adds the target call to features before emission. Fail closed on bad input; fresh
output refusal preserves previous attempts. Rollback is a scoped revert, retaining
private outputs. No checkpoint/cache/serving writes.

Known inventory: 292 issues in old extracted train+holdout; 40 other hash-holdout
issues yield 1,722 capped eligible rows, before final exact-overlap checks.
Unknowns: label support in target-blind selected cases, context improvement, and
transfer outside this source. These are measurements, not reasons to tune selection.
