---
Goal: Adversarially review round 4 of PR #16 — the invocation/operand seam and its mutation controls
Date: 2026-09-09
Reviewer: agy
NEXT: Producer
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

# Adversarial Review Findings (Round 5)

## Executive Summary
Round 4 attempted a conceptual fix to invert the positional default (`command_region`) and guard governance operand-reading rules (`ANY_POSITION_GATE` / `_operand_clauses`). However, round 4 did **not** achieve a sound seam. Adversarial inspection identified 5 distinct defect classes comprising multiple blockers:
1. **Quote-unaware clause splitting (`_operand_clauses`)**: Splits on `&&`, `||`, and `;` without respecting string literals. Any quoted string (e.g. git commit message, python code, or echo message) containing a semicolon or `&&` followed by `mv` or `releases_app.py` creates a synthetic clause where `leading_program` evaluates to `mv`. This allows inert text to spoof Tier 3 governance labels (`promote_capture`, `complete_doc`, `park_roadmap_row`). Conversely, paths with a literal semicolon inside quotes are split and stripped of their governance label.
2. **Environment variable prefix blindness (`KEY=val`) in `command_region`**: While `leading_program` uses `_LEAD` to skip variable assignments, `command_region` blindly indexes `tokens[0]`. For any standalone tool (`./validate.sh`, `pytest`, `ruff`), `command_region` returns the env assignment (`"CI=1"`, `"PYTHONPATH=."`), dropping real invocations to `unmapped`. For executors (`bash`, `python3`), it breaks immediately at the executor, dropping script arguments.
3. **Boolean short flag subcommand swallowing**: `command_region` assumes *every* short flag consumes a following argument. Common boolean flags (`git -p diff`, `git -v status`, `make -s test`) consume the actual subcommand and replace it with `""`, dropping commands to `unmapped` or demoting them.
4. **`_FILEISH` false breaks**: `_FILEISH` triggers an immediate loop break on any token containing `/`. This causes standard hierarchical branch names (`git branch feat/foo`) to be truncated to `git branch`, demoting `create_branch` to `git_inspect`. In long flags with paths (`cargo --manifest-path /repo/Cargo.toml test`), it truncates before the subcommand.
5. **Brittle governance gate predicates (`_is_move`)**: `_is_move` hardcodes `_second_token(clause) == "mv"`, completely breaking on `git -C <dir> mv ...` or `git -c <cfg> mv ...` and demoting legitimate promotion/completion moves to generic `fs_mutate`. Furthermore, `python3 -c "code" arg` allows unquoted operands to be retained in `command_region` due to `prev_flag` mechanics and `text(tok, keep=False)` returning unquoted tokens intact.

The ~2.19% drop in Studio coverage (from 98.52% to 96.33%, representing 2,625 unmapped calls) is not purely false-positive removal; it conceals an entire class of real engineer invocations (env-prefixed commands, flag-modified git calls, and complex command invocations) that the round 4 changes silently discard to `unmapped`.

---

## Detailed Responses to Questions

### Q1. Break the Seam

The invocation-vs-operand seam fails in both directions:

#### Finding 1.1 (Severity: Blocker) — Inert commit message / string literal spoofs governance
- **Exact command**:
  `git commit -m "docs: add note; mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"`
- **Observed label**: `promote_capture` (`tx.label_bash` evidence: `git commit -m "docs: add note; mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"`)
- **Expected label**: `commit_changes`
- **Mechanism**: `split_segments` preserves the quoted string as a single segment. Then `label_segment` passes the segment to `_operand_clauses`, which executes `re.split(r"&&|\|\||;", seg)` *before* quotes are stripped. The semicolon inside the commit message creates a synthetic clause: `mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"`. Its `leading_program` is `"mv"`, satisfying `_is_move`. Its unquoted content matches `promote_capture`. Because `promote_capture` is GOVERNANCE (tier 3), it overrides `commit_changes` (tier 2).
- **Smallest correction**: `_operand_clauses` must use quote-aware clause splitting (matching the parser in `split_segments`) rather than naive regex splitting on `;`/`&&`/`||`.

#### Finding 1.2 (Severity: Blocker) — Python inline code operand spoofs governance
- **Exact command**:
  `python3 -c "import sys" validate.sh`
- **Observed label**: `run_validate`
- **Expected label**: `run_script`
- **Mechanism**: In `command_region`, when `lead in EXECUTORS`, `-c` sets `inline = True` and `prev_flag = True`. For the next token `"import sys"`, `text()` blanks it to `""`, but `if not prev_flag: break` does not trigger because `prev_flag` is True. `prev_flag` is then cleared. The following operand `validate.sh` is unquoted; `text("validate.sh", keep=False)` checks `if not _is_quoted(tok): return tok`, returning `validate.sh` intact despite `keep=False`. `command_region` produces `python3 -c "" validate.sh`, which matches `run_validate` (tier 3), beating `run_script` (tier 2).
- **Smallest correction**: In `text(tok, keep=False)`, return `""` whenever `keep=False`, regardless of whether `tok` is quoted; and break immediately after consuming the inline code argument for `-c`/`-e`.

#### Finding 1.3 (Severity: Blocker) — Unquoted inline interpreter tokens scored as invocations
- **Exact command**:
  `python3 -c print(ruff)`
- **Observed label**: `run_linter`
- **Expected label**: `run_script`
- **Exact command 2**:
  `python3 -c import(pytest)`
- **Observed label**: `run_tests`
- **Expected label**: `run_script`
- **Mechanism**: `text(tok, keep=False)` in `command_region` implements `if not _is_quoted(tok): return tok`. When inline code lacks outer quotes, `keep=False` is ignored, preserving `ruff` and `pytest` in `command_region`.
- **Smallest correction**: Ensure `text(tok, keep=False)` returns `""` when `keep=False`.

#### Finding 1.4 (Severity: High) — Standard git branch names with slashes demoted to inspection
- **Exact command**:
  `git branch feat/new-login`
- **Observed label**: `git_inspect`
- **Expected label**: `create_branch`
- **Mechanism**: In `command_region`, `_FILEISH.search("feat/new-login")` matches because of `/`. This triggers an immediate `break`, leaving `git branch`. In `BASH_RULES`, `create_branch` requires `branch\s+[^-]`, which fails on bare `git branch`, so it falls back to `git_inspect`.
- **Smallest correction**: Do not break on `_FILEISH` when the leading subcommand is `branch`, `checkout`, `switch`, or other branch operations where slash names are customary.

---

### Q2. Are the Mutation Controls Real?

**Analysis**: The existing mutation controls in `tests/test_taxonomy.py` test only coarse switches, missing the actual internal mechanisms, and omit entire rules:
1. **`test_disabling_the_positional_restriction_makes_the_class_controls_fail`**: Disabling `command_region = lambda seg: seg` tests that whole-segment matching causes `chmod +x validate.sh`, `stat validate.sh`, `tar -czf backup.tgz validate.sh`, and `echo pytest` to go red. However:
   - For `echo pytest`, in any realistic multi-clause command (`git status && echo pytest`), `echo` is dropped by `substantive_segments` (`_DISPLAY`), not by `command_region`.
   - Crucially, none of the internal mechanisms in `command_region` are mutation-tested:
     - No mutation control disables the `--` end-of-options break.
     - No mutation control disables `_FILEISH`.
     - No mutation control disables the short-flag `prev_flag` argument blanking.
     If any of those internal mechanisms is corrupted or removed, the mutation test suite stays completely green.
2. **`test_disabling_the_invocation_gate_lets_display_text_spoof_governance`**: Sets `ANY_POSITION_GATE` to return `True` for all keys.
   - It tests `promote_capture` and `park_roadmap_row`, but completely **omits `complete_doc`**, the third member of `ANY_POSITION`.
   - It only tests bare unquoted strings (`echo mv ...`, `echo releases_app.py ...`). As shown in Finding 1.1, when quotes and semicolons are present, the gate is bypassed in production without any monkeypatching.
3. **Attribution Control (`test_the_requirements_txt_fix_is_a_RULE_change...`)**: Accurately demonstrates that `touch requirements.txt` was fixed by deleting the rule token rather than by `command_region`.

---

### Q3. `ANY_POSITION_GATE` Scoping

**Can a clause boundary be forged?**
**YES.**
In `label_segment`:
```python
gate = ANY_POSITION_GATE[name]
if any(gate(clause) and rx.search(unquoted)
       for clause, unquoted in _operand_clauses(full)):
    return name
```
While `gate(clause)` and `rx.search(unquoted)` are evaluated together per clause, the clause generator `_operand_clauses` uses `re.split(r"&&|\|\||;", seg)` on raw text without quote awareness.
Any string literal containing `;` or `&&` immediately followed by `mv ...` or `releases_app.py ...` (such as a commit message, python string, JSON payload, or echo argument) splits the string into a synthetic clause.
Because `_is_move` looks only at `leading_program(clause)`, the text immediately following the semicolon is treated as the leading command. Both `gate(clause)` and `rx.search(unquoted)` evaluate to `True` on the forged clause.

Executable verification:
- `git commit -m "note; mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"` -> `promote_capture`
- `echo "test; git mv PROJECT/2-WORKING/a.md PROJECT/3-COMPLETED/a.md"` -> `complete_doc`
- `python3 -c "x = 1; mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"` -> `promote_capture`

---

### Q4. Quote Handling

**Does stripping quotes destroy legitimate paths or create false boundaries?**
**YES.**
1. **Semicolon inside quoted path**:
   - Command: `mv "PROJECT/1-INBOX/note;1.md" "PROJECT/2-WORKING/note;1.md"`
   - Observed: `fs_mutate` (demoted from `promote_capture`)
   - Reason: `_operand_clauses` splits on `;` *before* quotes are stripped. The path is split across clauses, so neither clause contains both source and destination directories.
2. **Escaped quotes**:
   - `_TOKEN = re.compile(r"""'[^']*'|"[^"]*"|\S+""")`
   - `"[^"]*"` cannot handle escaped quotes `\"`. A command like `bash "scripts/validate\"1.sh"` is split into `['bash', '"scripts/validate"', '1.sh"']`, corrupting the token stream.

---

### Q5. The Three `ANY_POSITION` Labels

1. **Is `_is_roadmap_tool` sufficient?**
   **NO.**
   `_is_roadmap_tool` checks only:
   `return "releases_app.py" in command_region(clause)`
   - It only exists because `command_region` for executors (`python3`) terminates at the script name and discards subsequent tokens (`roadmap add`).
   - If `releases_app.py` is invoked with an environment variable:
     `PYTHONPATH=. ./releases_app.py roadmap add`
     `command_region` returns `"PYTHONPATH=."`, causing `_is_roadmap_tool` to return `False` and dropping the call to `unmapped`.
2. **Is `_is_move` sufficient?**
   **NO.**
   `_is_move` checks:
   `lead == "mv" or (lead == "git" and _second_token(clause) == "mv")`
   - If `git` is invoked with flags before the subcommand (e.g. `git -C /repo mv ...`, `git -c core.autocrlf=false mv ...`, `git --git-dir=/repo/.git mv ...`):
     `_second_token` is `"-C"` or `"-c"`, not `"mv"`.
     Executable verification:
     - `git -C /repo mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md` -> `fs_mutate` (expected: `promote_capture`)
     - `git -C /repo mv PROJECT/2-WORKING/a.md PROJECT/3-COMPLETED/a.md` -> `fs_mutate` (expected: `complete_doc`)
   - The gate is brittle and fails on legitimate git flag usage.

---

### Q6. Coverage as a Gate — Real Invocations Dropped to `unmapped`

The drop from 98.52% to 96.33% (2,625 unmapped calls) is not purely false-positive removal. Round 4 introduced three distinct systemic regressions that drop real engineer commands into `unmapped`:

#### Class A: Inline Environment Variable Prefixes (`KEY=val`)
In `command_region`:
```python
lead = leading_program(seg)
if lead in EXECUTORS:
    out, prev_flag, inline = [text(tokens[0], keep=True)], False, False
...
if lead not in SUBCOMMAND_PROGRAMS:
    return text(tokens[0], keep=True)
```
`leading_program` uses `_LEAD` to skip `KEY=val` definitions, finding the actual program. But `command_region` unconditionally takes `tokens[0]`, which is `KEY=val`!
- `CI=1 ./validate.sh` -> `command_region` is `"CI=1"` -> `unmapped` (expected: `run_validate`)
- `PYTHONPATH=. pytest` -> `command_region` is `"PYTHONPATH=."` -> `unmapped` (expected: `run_tests`)
- `DEBUG=1 ruff check .` -> `command_region` is `"DEBUG=1"` -> `unmapped` (expected: `run_linter`)
- `FOO=bar bash scripts/validate.sh` -> `command_region` is `"FOO=bar bash"` -> `unmapped` (expected: `run_validate`)
- `PYTHONPATH=. ./releases_app.py roadmap add` -> `command_region` is `"PYTHONPATH=."` -> `unmapped` (expected: `park_roadmap_row`)
- `FOO=1 make test` -> `command_region` is `"FOO=1 make"` -> `run_build` (expected: `run_tests`)

#### Class B: Boolean Short Flags on Subcommand Programs
`command_region` assumes *all* short flags consume an argument (`prev_flag = not tok.startswith("--") and "=" not in tok`). When a boolean flag is passed:
- `git -p diff` -> `command_region` is `"git -p \"\""` -> `unmapped` (expected: `git_inspect`)
- `git -v status` -> `command_region` is `"git -v \"\""` -> `unmapped` (expected: `git_inspect`)
- `git -p log` -> `command_region` is `"git -p \"\""` -> `unmapped` (expected: `git_inspect`)
- `make -s test` -> `command_region` is `"make -s \"\""` -> `run_build` (expected: `run_tests`)

#### Class C: Long Flags with File Paths (`--flag=/path`)
For long flags where arguments are paths, `prev_flag` is `False`. The subsequent token matches `_FILEISH` and aborts `command_region`:
- `cargo --manifest-path /path/Cargo.toml test` -> `command_region` is `"cargo --manifest-path"` -> `unmapped` (expected: `run_tests`)
- `uv --directory /path run pytest` -> `command_region` is `"uv --directory"` -> `pkg_manage` (expected: `run_tests`)

---

## Minimal Recommendations for Round 5

1. **Environment Variables**: In `command_region`, skip tokens matching `^[A-Za-z_][A-Za-z0-9_]*=` so that token index 0 aligns with `leading_program`.
2. **Quote-Aware Clause Splitting**: Replace `re.split(r"&&|\|\||;", seg)` in `_operand_clauses` with a quote-aware tokenizer (mirroring `split_segments`).
3. **Short Flag Argument Discrimination**: Only treat short flags known to take parameters (e.g. `-C`, `-m`, `-u`, `-o`) as setting `prev_flag`, or inspect whether the next token is a known subcommand before consuming it.
4. **`_FILEISH` Guard Refinement**: Do not break on `/` if the token is a branch name operand to `branch`/`checkout`/`switch`, or if following a flag like `--manifest-path`/`--directory`.
5. **Git Subcommand Traversal**: In `_is_move`, unwrap git options (e.g. `-C <dir>`, `-c <k=v>`) before inspecting whether the verb is `mv`.
6. **`keep=False` Fix**: In `command_region.text(tok, keep=False)`, return `""` when `keep=False`, even if unquoted.

---

## Log

- 2026-09-09 · claude-a · Review request opened. Target: `utils/corpus/taxonomy.py` at `main`
  (`2706973`), round-4 invocation/operand seam + mutation controls. Review-only, `ALLOW_PATHS=""`.
  Reviewer must append findings and a `VERDICT:` line below.
- 2026-09-09 · agy · Adversarial review completed. Found 5 defect classes: quote-blind clause splitting enabling governance spoofing via commit messages and echo strings, env var prefix blindness dropping commands to unmapped, boolean short flags swallowing subcommands, branch names with slashes demoting create_branch, and brittle git -C handling in governance move gates.
  VERDICT: FAIL
  Basis: Blockers found in Q1 (display/commit message text scoring promote_capture, unquoted python -c operands scoring run_validate/run_linter), Q3 (forged clause boundaries in _operand_clauses), Q5 (_is_move failing on git -C), and Q6 (systemic unmapped regressions on env-prefixed commands like CI=1 ./validate.sh and boolean git flags like git -p diff).

