# Issue #25 evaluation readiness refresh

**Status: `INCOMPLETE`.** The evaluation source now clears the frozen 30-session floor, but the
unchanged allocator cannot produce the required 1,000-row draw under its label quotas and 40-row
per-session cap. No evaluation sample was written and no training can start.

## Verified result

- A private immutable snapshot contains 337 Studio and 18 MacBook transcript files. Snapshotting was
  required after a direct read of the live source correctly refused when a transcript hash changed
  between extraction and manifest verification.
- The rebuilt source gate isolates 2,913 evaluation candidates across 32 sessions and 41 predicted
  labels. All comparable overlap counts are zero against the 20,711-row correction side, the prior
  Studio evidence boundary, and the frozen legacy training corpus.
- The sampler excludes 100 events with no auditable command or path text, leaving 2,813 reviewable
  rows across 38 labels. The 32-session count passes the minimum of 30. Applying the 40-row
  per-session cap to this reviewable pool permits at most 604 rows before label quotas. The exact
  allocator can satisfy the frozen label quotas for only 541 rows, so it returned exit 2 and wrote no
  output for the requested 1,000-row draw.
- The 396-row raw-capacity shortfall requires at least ten additional sessions only if every new
  session contributes the full 40 usable rows. That is a mathematical lower bound; label
  distribution can require more sessions.

## Decision

Keep the target, seed, label allocation, label floor, minimum session count, and session cap
unchanged. Collect independent, label-diverse evaluation sessions and rerun the source gate and
allocator against a new immutable snapshot. Begin auditing only after the allocator writes exactly
1,000 rows; begin training only after that audit is complete and sealed.

## Privacy

Raw transcripts, prompts, commands, local paths, session identities, and row-level data remain under
gitignored `data/`. The tracked receipt contains aggregate counts and hashes only.

## Validation

- Public receipt values match the immutable private source manifest and aggregate receipt.
- The frozen sampler reproduced the 541-row ceiling, returned exit 2, and wrote no output.
- Full non-slow suite: `342 passed, 6 skipped, 6 deselected`.
- PDDA: all deterministic checks passed; the optional LLM readiness review was not configured.
- Public-artifact scan: all files are nonempty; no local paths, private-key markers, or common
  literal credential assignments were found.
