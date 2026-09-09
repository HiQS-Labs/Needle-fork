---
Goal: Adversarially review round 4 of PR #16 — the invocation/operand seam and its mutation controls
Date: 2026-09-09
Reviewer: agy
NEXT: Reviewer
STATUS: Open
---

# Context

`utils/corpus/taxonomy.py` maps a shell command to one SDLC intent label. It has now failed
adversarial review **four times**, and each round found a defect set the previous round did not:

| Round | Reviewer | Found |
|---|---|---|
| 1 | corpus re-extraction diff | 3 regressions **no unit test caught** |
| 2 | agy (you, headless) | 6 defect categories |
| 3 | Codex Astra | 5 escapes |
| 4 | Codex Astra, at close | 3 blockers |

**Round 4's fix has never been reviewed by anyone.** The review room closed before it landed and
the automated reviewer was rate-limited. It merged to `main` (`5ed316d`) on the strength of a
bounded-pass rule, not a clean round. You are the first adversarial read of it.

Four rounds finding four *disjoint* sets is the reason to expect a fifth. **Do not confirm. Find
the fifth set.**

# The bug class, stated precisely

A command's **operands** were being read as if they were its **invocation**. So text a command
merely *displayed* or *carried* could score a label describing what that text would have done:

- `echo mv PROJECT/1-INBOX/x.md PROJECT/2-WORKING/x.md` → scored `promote_capture` (a governance
  action) when it only *prints*
- `chmod +x validate.sh` → scored `run_validate` when it only changes a mode bit

This is the **third** instance of the class. The first two were fixed with allowlists of specific
programs (`ARG_CONSUMERS`, `PKG_MANAGERS`); both were escaped. Round 4 claims a conceptual fix.

# What round 4 changed

Read `utils/corpus/taxonomy.py` at `main`, specifically:

- `command_region()` — the subcommand-depth walk, its `--` end-of-options handling, and the
  `prev_flag` rule that **only short flags** consume a following argument
- `ANY_POSITION` / `ANY_POSITION_GATE` — the three labels allowed to match outside the command
  region (`promote_capture`, `complete_doc`, `park_roadmap_row`), each gated by a predicate
  (`_is_move`, `_is_roadmap_tool`) that must first establish the command's **role**
- `_operand_clauses()` — splits on `&&`/`||`/`;` and strips quote *characters* while preserving
  the values inside them
- `_WRAPPERS`, `_DASH_M`, `_WRITE_REDIRECT`, `_HEREDOC_BODY`
- `label_segment()` — rule order, and the heredoc fallback's position

And in `tests/test_taxonomy.py`, the **mutation controls**: tests that monkeypatch
`command_region` to the identity function and assert the class tests then go **red**.

# The design principle it implements

> Establish the command's role first, then read its operands with values intact.

An earlier attempt blanked quoted text globally. That was wrong in **both** directions: it missed
unquoted display data (`echo mv PROJECT/...`), and it destroyed the operands of a *real* move
written with quoted paths (`mv "PROJECT/1-INBOX/a.md" "PROJECT/2-WORKING/a.md"`).

# Questions for you — answer with executable counterexamples, not opinions

**Q1. Break the seam.** Construct a command that a reasonable engineer would write, where the
invocation-vs-operand distinction still fails — either direction: display text scoring a real
label, or a real action losing its label. Run it through `label_bash` and show the output.
Wrappers, `xargs`, `env`, `sudo`, `find -exec`, `sh -c`, subshells, process substitution,
backticks, `$( )`, heredocs, `&&` chains inside quotes, and `--` are all fair game.

**Q2. Are the mutation controls real?** For each control that disables a guard and asserts the
class tests go red — verify the test actually goes red **for the stated reason**, not incidentally.
A control that would pass even if the guard were doing nothing is decorative. Round 2 (you) already
caught one decorative control here; check whether the replacements repeat it in a subtler form.

**Q3. `ANY_POSITION_GATE` scoping.** The gate is evaluated per clause via `_operand_clauses`. Can a
clause boundary be forged so the gate's predicate passes on one clause while the label-matching
regex matches on a *different* one? Show it or show why not.

**Q4. Quote handling.** `_operand_clauses` strips `"` and `'` characters but keeps the values. What
does that do to a path that legitimately contains a quote, an escaped quote, or a `;` inside quotes?
Is there an input where stripping quotes *creates* a clause boundary that was not there?

**Q5. The three ANY_POSITION labels.** These are governance labels — the ones this model exists to
predict, and the ones with the least training support (`promote_capture` has 8 calls in the whole
corpus). A false positive here is worse than elsewhere. Is the allowlist of three correct, and is
each gate predicate tight enough? `_is_roadmap_tool` checks only that `releases_app.py` appears in
the command region — is that sufficient?

**Q6. Coverage as a gate.** Post-fix Studio coverage is 96.33%, down from 98.52%, and the claim is
that the fall is *entirely* false positives being correctly removed. A control re-ran the pre-fix
mapper over the same corpus and reproduced 98.52%, so the fall is attributable to the rule change —
but nobody hand-audited the 2,625 unmapped calls. **Is there a class of call that the fix now
wrongly drops to `unmapped`?** That would be a real regression hiding inside a number I have
described as an improvement.

# Constraints

- **Review only.** Do not edit any file except this relay file. `ALLOW_PATHS` is empty.
- Report each finding as: **severity**, the **exact command**, **observed** vs **expected** label,
  and the **smallest** correction. If you cannot construct a counterexample for a question, say so
  plainly — "I could not break this" is a useful result and will be reported as such.
- Do not soften. The previous three rounds were all correct to fail this file.

# Definition of done

Append your review below, set `NEXT: Producer` and leave `STATUS: Open` if you found defects, or
`STATUS: Approved` only if you genuinely could not break it.
