# Taxonomy #2 — argument positions are no longer read as invocations

**Date:** 2026-09-09 · **Issue:** [#2](https://github.com/HiQS-Labs/Needle-fork/issues/2) · **Blocks:** `v1.0.0` cut
**Supersedes the mapping numbers in:** `TESTS-RESULTS/2026-09-07-taxonomy-v1-studio/`

## What changed

The third instance of this bug class. The first two were fixed with lists of specific programs
(`ARG_CONSUMERS`, `PKG_MANAGERS`). The defect is not that certain programs take data — it is that a
bare-name rule could match **anywhere in a segment**. So the default is inverted:

> A bare-name rule now matches only in **command position**. Everything after the command is data
> unless the program is known to take subcommands.

That is why a program nobody enumerated — `stat`, `realpath`, `shasum`, `basename`, `tar` — is
handled by the default rather than needing an entry. Path-shaped governance rules
(`mv PROJECT/1-INBOX/… PROJECT/2-WORKING/…`) still read operands, because they match a directory
move rather than a name, and an operand cannot spoof them.

Supporting mechanisms: wrappers are unwrapped to their child (`timeout`, `nohup`, `nice`, `sudo`,
`env`, `watch`, `xargs`, `stdbuf`, `uv run`, `git bisect run`, `/usr/bin/time`); `python -m <mod>`
resolves to the module; quoted text is data everywhere; stdout redirection to a file makes a content
producer a write.

## Verification

| Check | Result |
| --- | --- |
| `pytest -q -m "not slow"` | **212 passed**, 6 skipped, 6 deselected |
| New regression tests | 38, covering wrappers, inline interpreter bodies, operands, quoting, redirection, heredoc precedence, `-m`, and a class-level control |
| Red before green | **25 of them witnessed failing** against the pre-fix module before any fix landed |
| All 14 instances reported in #2 | Every one re-labelled; none retains its buggy label |

The class-level control is the one that matters: it uses programs (`stat`, `realpath`, `shasum`,
`basename`, `tar`) that appear nowhere in the fix. A fourth special-case list would leave them wrong.

## Corpus impact — local transcripts

Measured on **2,054 Bash commands** from this machine's transcripts, labelled by the pre-fix and
post-fix mappers and joined per command.

| Metric | Before | After |
| --- | --- | --- |
| Mapping coverage | 98.88% | **97.21%** |
| Governance share | 2.75% | 2.53% |
| Static top-1 baseline | 28.35% | 20.45% |
| Commands whose label changed | — | **292 (14.2%)** |

**Coverage falling is the intended direction.** The lost 1.67pp is commands that were being given a
confident wrong label and are now honestly `unmapped`. The top-1 baseline falls because `run_script`
was absorbing unrelated commands; a less concentrated distribution is a harder, truer baseline.

Largest label movements: `run_script` −184, `apply_patch` +134, `unmapped` +39, `fs_mutate` +28.
The dominant transition (118×) is `run_script → apply_patch`: `cat > file <<'EOF'` **writes** a
source file. Both the old label and the first version of this fix got that wrong in different ways.

**Governance labels lost: 4, all verified false positives** — three from a relay-harness *locator*
that names relay scripts in a candidate-path loop, and one from `gh issue create --title` whose text
mentioned `pdda`. That last one is the bug class exactly. **No true governance positive was lost**,
checked by enumerating every command whose governance label changed.

## Not done, and why

- **The Studio corpus was not re-extracted.** #2 requires it; the SMB share was not mounted on this
  machine. The 74,909-pair Studio numbers in the 2026-09-07 receipt remain **stale, not superseded
  by measurement** — re-run `utils/corpus/extract_claude_transcripts.py` against the Studio source
  and re-publish before cutting `v1.0.0`.
- **`oracle/labels-v1.json` was not re-published.** No label's *meaning* changed, only which commands
  map to it, so the contract is unchanged; confirm against the Studio re-extraction.
- Three regressions in this work were found **only by diffing a re-extraction**, not by any unit
  test: hoisting the heredoc check above the ordered rules (44 real commits became `run_script`),
  treating `2>/dev/null` as a content write (34 reads became writes), and reducing a heredoc-joined
  segment before the path-shaped rules ran (a real `complete_doc` hid behind a `mkdir`). Each now has
  a test. Rule *precedence* is load-bearing: this fix changes only the haystack each rule sees.
