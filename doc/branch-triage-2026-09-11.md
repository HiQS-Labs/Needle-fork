# Branch triage — 2026-09-11

Scope: light–medium review of fetched origin refs, PR status, ancestry, file lists, relevant diffs,
and reported verification. This is not a new numerical validation or a branch-deletion audit.
Baseline: `main` at `497fc82`. No branches or worktrees were deleted.

## Active PRs

Historical snapshot at triage time; see the integration closeout below for current disposition.

| PR / branch | Observed state | Disposition and next action |
|---|---|---|
| [#8](https://github.com/HiQS-Labs/Needle-fork/pull/8) `fix/adapter-numerics-provenance` | Mergeable; 3 files, 119 added lines. Rejects adapters with missing/full-precision training provenance unless explicitly overridden. Historical tests and CodeRabbit pass predate current main. | First integration candidate: refresh against main, review the changed build contract, and run current build and non-slow tests. Mergeability is not numerical validation. |
| [#43](https://github.com/HiQS-Labs/Needle-fork/pull/43) `feat/gh-41-targeted-augmentation` | Mergeable; latest fetched head `974ddcf`; PR reports 400 passed, 6 skipped, 6 deselected and final review approval. CodeRabbit pending at inspection. | **Operator hold: do not merge or modify this branch; testing is ongoing elsewhere. Await explicit release of the hold.** Tooling advances #41; it does not complete the controlled model experiment. |
| [#6](https://github.com/HiQS-Labs/Needle-fork/pull/6) `governance/issue-is-sot` | Conflicts with main; 2 unique commits. Useful issue/receipt authority rules overlap recent ROUTER and SOP changes. | Refresh narrowly, preserving current documentation. Review section references after reconciliation. Do not discard the still-unlanded policy because its branch is old. |
| [#10](https://github.com/HiQS-Labs/Needle-fork/pull/10) `sop/operational-rails` | Conflicts with main; includes #6 plus one additional commit. True incremental diff over #6 is 63 added SOP lines. | Resolve after #6, or consolidate their useful policy into one replacement PR and explicitly supersede both. Do not treat the two full diffs as independent work. |
| [#42](https://github.com/HiQS-Labs/Needle-fork/pull/42) `experiment/coding-core-pilot` | Mergeable into `spike/mlx-finetune`, not main. Carries 35 commits absent from main, including its 33-commit spike base. | Park as experiment evidence. Any future main integration must select a bounded deliverable; do not retarget the entire historic spike. The private-trained comparison remains pending. |

## Branches without an open integration decision

`spike/mlx-finetune` has no PR of its own, is 33 commits ahead / 80 behind main, and is the parent
of #42. Preserve it as the parked #5 research base. Its integration disposition is explicitly
deferred; a future deliverable needs a focused PR rather than wholesale promotion.

These remote branch families have merged PRs and are retirement candidates, not active queues:

- Taxonomy/serialization: `phase-2/label-taxonomy-v1`, `phase-2/query-serialization`,
  `fix/2-positional-label-rules`, `fix/17-clause-splitting-and-env-prefix`,
  `fix/17-shape-rule-and-prose-flags`.
- Audit/data: `fix/20-audit-measurement-contract`, `audit/23-error-causes`,
  `experiment/25-feedback`, `experiment/25-audit-v2`, `feat/25-audit-readiness`,
  `data/deterministic-agent-adapters`, `data/agent-label-audit`, `data/zcode-blind-label-audit`,
  `data/zcode-mapper-correction`.
- Documentation: `docs/unstale-superseded-pointers`, `docs/oracle-collaborator-story`,
  `docs/oracle-readme-story`.

Squash-merged documentation branches still have unique commit IDs; that alone is not lost work.
Before retirement, verify patch/content preservation and check the owning checkout for uncommitted
and ignored artifacts. Two registered historical worktrees are marked prunable, but registration
state is not permission to remove another session's workspace. Remote branch deletion still needs
the explicit target-specific confirmation required by AGENTS.md.

## Ordered follow-through

1. Refresh and validate #8. Keep #43 on the operator's explicit testing hold until released.
2. Reconcile #6 then #10, or replace the stack explicitly with one reviewed policy PR.
3. Keep #42 and its MLX base parked until a bounded experiment or integration is chosen.
4. Retire verified merged branches only after preservation checks and required deletion approval.

The new hygiene rule in AGENTS.md applies to subsequent work. This triage does not merge, close,
retarget, or delete any of the five existing PRs.

## Integration closeout — 2026-09-11

Operator-authorized follow-through landed #46, #8, #6, then #10. Conflicts were resolved without
discarding current docs; a duplicate historical changelog entry from the stack was removed.
Verification: 384 non-slow tests passed, 6 skipped; 11 slow build/finetune tests passed;
governance check reported zero errors and warnings. The adapter guard changes CLI compatibility,
not quantization math. No branch or worktree was deleted.

Still tracked under [issue #1](https://github.com/HiQS-Labs/Needle-fork/issues/1):

- **Previous step 3, deferred:** private-trained Markov-1/phase-backoff comparison, using the
  already-agreed bounded protocol in README. Not run during integration. #42 and its MLX base
  remain parked research, not wholesale main-integration candidates.
- **Previous step 4, held:** #43 remains open at `974ddcf9b480a985c272ac5215bce87ea669436e`.
  Do not merge or modify its branch until the operator explicitly releases the testing hold.
