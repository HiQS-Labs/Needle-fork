---
Goal: Final adversarial round before freezing the v1 label vocabulary as v1.0.0
Date: 2026-09-09
Reviewer: codex
NEXT: Reviewer
STATUS: Open
---

# Context

`utils/corpus/taxonomy.py` sorts a shell command into one of 44 SDLC intent labels. It is the
only supervision signal for a 45M model. The operator has decided to **freeze the vocabulary as
`v1.0.0`** after this round. You are the last review before that freeze.

**This file has failed adversarial review six times**, and every round found a defect set the
previous rounds did not:

| Round | Reviewer | Found |
|---|---|---|
| 1 | corpus re-extraction diff | 3 regressions no unit test caught |
| 2 | agy | 6 defect categories |
| 3 | Codex Astra | 5 escapes |
| 4 | Codex Astra (at close) | 3 blockers |
| 5 | agy | 5 defect classes, 21 counterexamples — **21/21 reproduced** |
| 6 | CodeRabbit | 2 defects *introduced by* round 5's fix, 2 overstated counts |

Six disjoint sets is the reason to expect a seventh. **Do not confirm. Find it.**

# The recurring bug class — six distinct routes so far

A command's **operands** or **displayed text** get read as its **invocation**, so text a command
merely mentions scores a label describing what that text would have done. Each fix closed one
route and the next round found another:

1. bare-name rules matching anywhere in a segment
2. `--` end-of-options treated as an ordinary flag
3. quoted operands blanked globally (broke *real* moves)
4. clause splitting that ran **before** quotes were considered — a **commit message** scored
   `promote_capture`
5. `text(tok, keep=False)` returning unquoted tokens intact
6. the **tokenizer** splitting `TITLE="fix pytest flake"`, so quoted text reached command position

# What to review — at `main`

- `command_region()`, `_TOKEN`, `_LEAD`, `_ENV_ASSIGN`, `_END_OF_OPTIONS`, `_FILEISH`
- `_SHORT_TAKES_ARG` / `_LONG_TAKES_ARG` / `_NUMERIC_ARG` — per-program flag tables, default boolean
- `_split_outside_quotes()`, `_operand_clauses()`, `ANY_POSITION_GATE`, `_is_move`, `_subcommand`
- `label_segment()` rule order; `BASH_RULES`
- `tests/test_taxonomy.py` — the per-mechanism mutation controls
- `oracle/labels-v1.json` — the vocabulary about to be frozen

# Questions

**Q1. The seventh route.** Find another way text that is not an invocation scores a label, or a
real invocation loses one. Give the exact command and the observed label.

**Q2. The flag tables are hand-maintained.** `_SHORT_TAKES_ARG` defaults to *boolean* for unknown
flags and `_LONG_TAKES_ARG` defaults to *no argument*. Both are per-program allowlists — the same
shape as `ARG_CONSUMERS` and `PKG_MANAGERS`, which were escaped twice before and which round 4
was supposed to replace with a conceptual fix. **Is this a return to the pattern that already
failed twice?** If so, what is the non-allowlist formulation?

**Q3. Are the mutation controls load-bearing?** Each disables one mechanism and requires the class
tests to go red. Two of them were decorative on the first attempt and were re-pinned. Check the
rest for the same fault: would any pass with its mechanism removed?

**Q4. Freeze readiness — the vocabulary, not the sorter.** 44 labels. `promote_capture` (8 calls)
and `publish_release` (2) sit below the 0.1% support floor and are being **kept**, with
supplementation deferred to #9. `no_action` has 0 by design. Is freezing `v1.0.0` with three
labels that have almost no training signal defensible, or does it bake in a contract that cannot
be honoured? Note the contract text itself says the floor's action is *"supplement, never delete
or merge"*.

**Q5. What we are NOT claiming, and should we be?** Coverage is 96.40% — that counts *resolution*,
not *correctness*. The ~2,580 unmapped calls have never been hand-audited, and `multi_rule_pct` is
**78.1%**: most commands match several rules and the winner is decided by rule order. **Does an
unaudited 78% multi-match rate make the freeze premature regardless of anything else?**

# Constraints

- **Review only.** `ALLOW_PATHS` is empty; edit nothing but this relay file.
- Report each finding as severity, exact command, observed vs expected, smallest correction.
- "I could not break it" is a useful and reportable result — say so plainly rather than padding.
- A finding and its proposed fix are judged separately: round 5's reviewer was 21/21 correct on
  diagnosis and wrong on one prescription, which would have regressed the file.

# Definition of done

Append findings, then `NEXT: Producer` with `STATUS: Open` if the freeze should be blocked, or
`STATUS: Approved` if you judge v1.0.0 defensible. Add a `VERDICT: PASS|FAIL|PARKED` line.

## Log

- 2026-09-09 · claude-a · Final pre-freeze review opened at `main` `3c357ff`. Review-only.
