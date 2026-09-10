# Issue #25 source-identity gate

## Verdict

**The source and separation tooling passes on the available private data; the feedback experiment
remains `INCOMPLETE` because the fresh evaluation inventory has only 17 sessions against the
predeclared 30-session floor.** No training was started.

## Evidence classification

- **Verified by this run:** the mounted Studio source yielded 65,585 namespaced q1 pairs across 316
  currently available sessions. Deterministic legacy-membership recovery selected 43,461 correction
  candidates from 257 of the canonical training corpus's 296 sessions.
- **Verified by this run:** the MacBook source yielded 2,806 evaluation candidates across 17 usable
  sessions. These are unreviewed candidates, not reference labels or an evaluation result.
- **Verified by this run:** session, source-event, exact q1, and full-context overlap are all zero
  between the correction and evaluation candidates and between the evaluation candidates and the
  entire current Studio inventory. Exact q1 and full-context overlap are also zero against all
  74,428 frozen canonical Studio pairs; the legacy rows do not contain comparable stable session or
  event IDs, and the receipt records those fields as unavailable rather than zero. The full private
  manifest is pinned by SHA-256 in `receipt.json`.
- **Verified by tests:** identities stay unchanged when identical transcript bytes and relative
  paths move under another mount prefix; a different source namespace changes them. The extractor
  rejects copied native tool events, and the manifest rejects empty inputs, output overwrite,
  contract/hash drift, missing source events, and every declared cross-boundary overlap.
- **Hypothesis:** reviewed target corrections will improve fresh-session top-1 accuracy by at least
  five percentage points. This run contains no model evidence for that hypothesis.

Natural repeated q1 inputs remain explicit. The receipt reports their group and occurrence counts;
the manifest builder does not silently remove them.

## Reproduction shape

1. Run `extract_claude_transcripts.py --source-namespace NAME` once for each private source root.
2. Run `build_experiment_manifest.py` with the namespaced Studio and fresh pair files, the canonical
   legacy membership file, its original source prefix, and the full prior Studio inventory as an
   exclusion boundary.
3. Keep the row-level manifest under ignored `data/`; retain only this aggregate receipt publicly.

Local source roots are deliberately omitted. The receipt pins every private input and schema by
hash without carrying prompts, commands, rows, credentials, or local paths.

## Validation

- `318 passed, 6 skipped, 6 deselected` in the full non-slow release suite.
- A deliberate mutation that disabled overlap rejection made the overlap test fail.
- A deliberate mutation that restored absolute-path session identity made the mount-prefix test
  fail.
- A second full private-data run produced byte-identical manifest and receipt files.
- Repository PDDA checks passed before implementation; final full-suite results are recorded in the
  PR.

## Next gate

Collect at least 13 additional eligible independent sessions, then rerun the manifest and freeze the
1,000-row sample. If the protected subsets or session count still miss their declared floors, the
experiment stays `INCOMPLETE`; do not train or relax the thresholds after seeing outcomes.
