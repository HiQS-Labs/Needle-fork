---
Goal: Final adversarial round before freezing the v1 label vocabulary as v1.0.0
Date: 2026-09-09
Reviewer: codex
NEXT: Producer
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

## 2026-09-09 · codex · Reviewer

VERDICT: FAIL
Basis: Finding 1 (Blocker) -- `git --exec-path /tmp/validate.sh status` scores
unmapped; an unlisted path-valued long option truncates command_region before the
subcommand. Q2: the flag tables are a return to the allowlist shape that failed twice.

Freeze is blocked. I found a seventh route: an unlisted long global option with a separate
argument can still make a real invocation lose its label. This is the same structural class as the
round-5 flag-table defects, but in the false-negative direction: the option argument is data, yet
because the table does not know the flag consumes it, `_FILEISH` treats the path argument as the
start of operands and truncates the command before the real subcommand.

Finding 1 - Blocker - real invocation loses its label through an unlisted path-valued long option.

- Exact command: `git --exec-path /tmp/validate.sh status`
- Observed: `unmapped`; `command_region()` is `git --exec-path`
- Expected: `git_inspect`, because this is a real `git status` invocation and the `--exec-path`
  argument is not the command.
- Smallest correction: stop relying on a hand-maintained allowlist for path-valued global options.
  Use a positional parser that classifies tokens as command-bearing or data-bearing from shell
  shape: for subcommand programs, consume a separate argument after long options until the next
  recognized command token when the token is before any subcommand and the successor is path-shaped
  or otherwise value-shaped; keep `--flag=value` dropping the value as today. If the code keeps a
  table temporarily, `git --exec-path` and `git --namespace` demonstrate the missing class, but a
  larger table is the return to the pattern that already failed twice.

Probe results, saved under `.relay-scratch/codex-v1-freeze-probes.txt`:

```text
git --exec-path /tmp/validate.sh status
  region= git --exec-path
  label= unmapped
git --exec-path=/tmp/validate.sh status
  region= git --exec-path status
  label= git_inspect
git --namespace foo status
  region= git --namespace foo status
  label= unmapped
git --namespace=foo status
  region= git --namespace status
  label= git_inspect
git --literal-pathspecs status
  region= git --literal-pathspecs status
  label= git_inspect
```

Q2. Yes, the flag tables are a return to the allowlist shape that failed before. The non-allowlist
formulation should be "subcommand discovery with token roles": once the lead program is known,
walk tokens until a real subcommand/target is identified, treating flags and their syntactic values
as data, not searchable command text. Unknown flags should not default to either "boolean" or "no
argument" globally; before the subcommand, an unknown long flag followed by a value-shaped token
must not be allowed to truncate discovery or expose that value as intent. The current code handles
some shapes (`--flag=value`, known separate-arg flags, `--`), but the separate-arg unknown case
still leaks.

Q3. I did not find a decorative mutation control in the reviewed block. The controls for quote-aware
splitting, env-prefix skip, end-of-options, `_FILEISH`, short-flag consumption, branch placeholder,
ANY_POSITION gates, and tokenizer quoting all disable a named mechanism and assert either the
wrong label returns or the protected token leaks back into `command_region()`. The end-of-options
control correctly asserts on `command_region()` rather than final label, avoiding the specific
"passes by rule order anyway" trap.

Q4. Keeping rare labels in the frozen vocabulary is defensible under the stated contract because the
contract explicitly says the support floor action is supplement, never delete or merge. The training
risk is real, especially for `publish_release` and `promote_capture`, but deleting them at the
taxonomy root would be the Costly and less reversible move. The freeze blocker here is sorter
correctness, not rarity alone.

Q5. The 78.1% multi-match rate is a serious warning, but by itself I would not call it an automatic
vocabulary-freeze blocker. It blocks any claim that 96.40% coverage means correctness. For v1.0.0,
the contract can freeze label names while still requiring sorter QA and supplementation. In this
turn, the concrete sorter miss above is enough to keep STATUS Open.
