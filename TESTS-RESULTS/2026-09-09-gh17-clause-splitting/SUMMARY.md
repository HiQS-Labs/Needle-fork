# GH-17 — quote-aware clause splitting, and how much of the coverage drop was real loss

**Date:** 2026-09-09 · **Corpus:** Studio `~/.claude/projects` over SMB · **Mapper:** `11d04e8`
· **Control:** `b33b92a` · **Machine:** MacBook Pro 14" M4 Pro, Python 3.11.15
· **Issue:** [#17](https://github.com/HiQS-Labs/Needle-fork/issues/17)

Round 4 of #16 merged with no adversarial review. An `agy` headless review
(`relay-system/2026-09-09/pr16-round4-adversarial.md`) returned **VERDICT: FAIL** with five
defect classes. **All 21 counterexamples were reproduced against `b33b92a` before any fix:
21 confirmed, 0 refuted.**

## Result — both sides of a claim were miscalibrated

`267a171` said the §2 coverage fall (98.52% → 96.33%) was **entirely** false positives being
correctly removed. agy said the fall "conceals an entire class of real engineer invocations."
A control settles it: the pre-fix mapper (`b33b92a`) and the fixed mapper (`11d04e8`) run over
the **same** corpus, 71,724 calls, mapper the only variable.

| Mapper | Coverage | Unmapped | Governance |
|---|---|---|---|
| `b33b92a` (round 4) | 96.34% | 2,625 | 5.89% (4,225) |
| **`11d04e8` (GH-17 fix)** | **96.40%** | **2,582** | **5.90%** (4,234) |

**The fix recovers 43 calls — +0.06 pp.**

Round 4's total fall was ≈2.19 pp (≈1,570 calls). So of that fall:

- **≈43 calls (≈2.7%) were real commands wrongly dropped** — env-prefixed invocations, boolean
  short flags, long-flag path arguments.
- **≈97% remains attributable to false-positive removal.**

**I was wrong, and agy was wrong in the other direction.** "Entirely" was too strong — real loss
existed and I had asserted it did not. "An entire class" was also too strong — it is 43 calls in
71,724, not a large share. The number is what separates a real defect from a large one, and
neither of us had it when we made the claim.

## What was wrong in round 4

**The 4th instance of the bug class.** `_operand_clauses` split on `;`/`&&`/`||` with a plain
regex *before* quotes were considered, so quoted text forged a clause whose leading program was
`mv`:

```
git commit -m "docs: add note; mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"
  → promote_capture          (expected commit_changes)
```

A **commit message** spoofed a governance label. The same splitter also cut a real move whose
path contained a `;`. Round 4's *principle* — establish role first, then read operands — was
right; its clause splitter was unsound, and earlier rounds never probed it because they used
unquoted examples.

**Inline code.** `text(tok, keep=False)` returned an unquoted token intact, so `keep=False` was
silently ignored: `python3 -c print(ruff)` → `run_linter`.

**Three classes of real command dropped** (the 43 calls above): env prefixes (`CI=1
./validate.sh`), boolean short flags (`git -p diff`), long-flag path arguments
(`cargo --manifest-path /p/Cargo.toml test`).

**Token 2 taken literally, twice more.** `_is_move` and the package-manager delegate check both
broke on any global flag: `git -C /repo mv PROJECT/1-INBOX/a.md …` → `fs_mutate`.

## Mutation controls: the previous set could not have caught any of this

The old controls switched `command_region` and `ANY_POSITION_GATE` off as **wholes**, so every
mechanism inside `command_region` could be corrupted with the suite green. There is now one
control per mechanism — quote-aware splitting, the env-prefix skip, `--` end-of-options,
`_FILEISH`, the short-flag table, the branch-name placeholder — plus `complete_doc`, the third
`ANY_POSITION` member the gate control had omitted.

**Two of the new controls were themselves decorative on the first attempt**, and are recorded
here because that is the failure mode being guarded against:

- `--` is not load-bearing for `git diff -- validate.sh`; `_FILEISH` already breaks on it. The
  control passed with the mechanism removed.
- At label level `git_inspect` matches `diff` and wins on rule order whether or not the operand
  leaked, so the re-pinned control asserts on `command_region` directly.

## What this does not establish

- **Not a correctness measurement.** Coverage counts resolution. The remaining 2,582 unmapped
  calls were not hand-audited.
- **Label-to-label changes are not measured here.** The +9 governance calls are a *net* of false
  positives removed and real moves recovered; this receipt cannot separate them.
- **Ambiguity is unchanged**: `multi_rule_pct` 78.10%, against the control's 78.09%.
- **Five rounds have now found five disjoint defect sets.** Nothing here suggests the sixth does
  not exist.

## Reproduce

```sh
SRC="/Volumes/Macintosh HD-1/Users/noelsaw/.claude/projects"
python3.11 utils/corpus/measure_taxonomy.py --source "$SRC" --out raw-metrics.json
# control: same command from a worktree at b33b92a
```

Tests: `python3.11 -m pytest tests/test_taxonomy.py tests/test_serialize.py -q` → **191 passed**.
11 of the new assertions were witnessed red against `b33b92a` first.
