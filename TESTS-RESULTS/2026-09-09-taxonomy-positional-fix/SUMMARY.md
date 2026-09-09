# Taxonomy #2 — argument positions are no longer read as invocations

**Date:** 2026-09-09 · **Issue:** [#2](https://github.com/HiQS-Labs/Needle-fork/issues/2) · **Blocks:** `v1.0.0` cut
**Supersedes the mapping numbers in:** `TESTS-RESULTS/2026-09-07-taxonomy-v1-studio/`
**Revised after an adversarial review by agy** (relay-xyz, review-only) failed the first attempt.

## What changed

The third instance of this bug class. The first two were fixed with lists of specific programs
(`ARG_CONSUMERS`, `PKG_MANAGERS`). The defect is not that certain programs take data — it is that a
bare-name rule could match **anywhere in a segment**. So the default is inverted:

> A bare-name rule matches only in **command position**. Everything after the command is data unless
> the program is known to take subcommands.

An unlisted program is handled by that default: `stat`, `realpath`, `shasum`, `basename`, `gzip`
appear nowhere in the fix and label correctly. **A test pins that they stay unenumerated**, because
the first attempt added them to `ARG_CONSUMERS` — which is checked *before* `command_region` — and so
its class control passed while testing nothing.

Path-shaped governance rules (`mv PROJECT/1-INBOX/… PROJECT/2-WORKING/…`) still read operands: they
match a directory move, not a name, so an operand cannot spoof them.

Supporting mechanisms: `--` ends options; `--flag=value` contributes the flag, never the value;
a flag's argument does not consume subcommand depth; tokenisation is quote-aware and a quoted token
is data unless it is an executor's script; wrappers unwrap to their child and accept long flags;
`<lead> -m <mod>` resolves to the module; stdout redirection to a real file (not `/dev/*`) makes a
content producer a write; a heredoc selects `run_script` only as a **fallback**.

## Verification

| Check | Result |
| --- | --- |
| `pytest -q -m "not slow"` | **236 passed**, 6 skipped, 6 deselected |
| New regression tests | 62 |
| Red before green | 25 witnessed failing against the pre-fix module; the 23 round-two cases all reproduced as defects before being fixed |
| The 14 instances reported in #2 | all re-labelled |
| agy's findings | 21 of 23 resolved; 2 are documented limitations below |

## Corpus impact — local transcripts

Measured on **2,087 Bash commands**, labelled by both mappers.

| Metric | Before | After |
| --- | --- | --- |
| Mapping coverage | 98.85% | **97.99%** |
| Commands whose label changed | — | **315 (15.1%)** |

Largest movements: `run_script` −166, `apply_patch` +136, `fs_mutate` +29, `unmapped` +18.
The dominant transition is `cat > file <<'EOF'` → `apply_patch`: writing a source file.

**Governance labels lost: 2, both verified false positives** — a relay-harness *locator* that names
relay scripts in a candidate-path loop, and a `gh issue create --title` whose text mentioned `pdda`.
That second one is the bug class exactly. No true governance positive lost.

**`run_tests` 22 → 14, adjudicated command by command.** The first attempt claimed the whole coverage
drop was false-positive elimination; agy showed that was false, and it was. After the fixes, six of
the eight remaining drops are corrections — `pytest` appearing as a `which` operand, inside a grep
pattern, inside `python3 -c` code, or as a path handed to `sed`/`git show`. Two are tier artifacts on
commands that both install and run tests, where a different segment now wins. **Coverage falling is
the intended direction only where the label was wrong; it is not a blanket justification.**

## Known limitations

- **Unlisted task runners degrade to `unmapped`:** `just test`, `rake test`, `bundle exec rspec`,
  `tox -e py311`. That is the safe direction — no wrong label — but it is a coverage gap, not a
  correction. Adding a rule per runner is enumeration and was deliberately not done here.
- **The Studio corpus was not re-extracted.** #2 requires it; the SMB share is not mounted on this
  machine. The 74,909-pair numbers in the 2026-09-07 receipt are **stale, not superseded by
  measurement**. Re-run and re-publish before cutting `v1.0.0`.
- `oracle/labels-v1.json` unchanged: no label's *meaning* moved, only which commands map to it.

## What the first attempt got wrong

Recorded because the pattern matters more than the individual defects. Three regressions were found
only by diffing a re-extraction, and six more only by adversarial review:

1. Hoisting the heredoc check above the ordered rules turned 44 real commits into `run_script`.
2. `\d?>` treated `2>/dev/null` as a content write, turning 34 reads into writes.
3. Reducing a heredoc-joined segment before the path-shaped rules hid a real `complete_doc`.
4. `--` treated as a flag left `git diff -- validate.sh` scoring `run_validate` — the defect #2 exists
   to remove, reintroduced by its own fix.
5. The class-level control was decorative: the programs it named were enumerated in the same diff.
6. Blanking quotes before tokenising destroyed quoted operands, dropping real test runs.

Rule *precedence* is load-bearing: the fix changes only the haystack each rule sees, never the order.
