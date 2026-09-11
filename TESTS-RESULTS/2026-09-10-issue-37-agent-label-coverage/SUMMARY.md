# Issue #37 raw cross-agent label-coverage baseline

**Verdict: ZCode advances to blind semantic review; Codex and Agy remain mechanically
unqualified.** This run measures whether exact adapter aliases and native argument objects work with
the unchanged Claude `v1.0.0` mapper. It does not measure semantic label correctness and does not
admit any source to training.

| Source | Sessions accepted | Rejected | Actions | Alias coverage | Mapping coverage | Mapped labels | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Codex | 1,934 | 4 | 62,455 | 47.50% | 6.88% | 3 | Defer; tool and argument schemas differ |
| Agy desktop | 82 | 2 | 27,757 | 94.40% | 49.41% | 6 | Defer; argument schema differs |
| Agy CLI | 501 | 0 | 5,227 | 99.89% | 44.12% | 5 | Defer; argument schema differs |
| ZCode | 21 | 0 | 1,091 | 100.00% | 99.73% | 26 | Advance to blind label review |

## Verified by this run

- Each source result passed action-conservation assertions and contains a nonempty inventory digest.
- Two consecutive executions against the same source state produced byte-identical JSON for all
  four sources.
- Codex's dominant unmapped surfaces are wrapper-level `exec` calls and `exec_command` calls whose
  command field is named `cmd`; neither is silently reinterpreted by this baseline.
- Agy's `run_command` alias reaches `Bash`, but its command field is named `CommandLine`, so the
  unchanged mapper deliberately returns `unmapped` for those calls.
- ZCode already uses Claude-compatible `command` and `file_path` argument names.
- The committed JSON contains aggregate counts, field names, and hashes only. It contains no prompt,
  argument value, command, path value, native identity, or event identity.

## Validation

- Focused adapter plus audit suite: 23 passed.
- Deliberately disabling label-total conservation made its focused test fail; the source was then
  restored and the focused suite passed.
- Repository non-slow suite: 361 passed, 6 skipped, 6 deselected; 6 failures and 1 setup error are
  pre-existing environment failures because JAX is not installed in this checkout. The changed
  files do not import or touch JAX/model code.

## One next action

Create a deterministic, stratified ZCode review sample and measure semantic label correctness before
using any ZCode rows for development or training. Keep Codex and Agy deferred until explicit,
lossless argument projections are separately specified and tested; do not parse opaque Codex `exec`
programs as if they were native action records.
