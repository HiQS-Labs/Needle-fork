---
Goal: Adversarially review PR #16 — the #2 positional taxonomy fix
Date: 2026-09-09
NEXT: claude-a
STATUS: Open
---

# Context

`utils/corpus/taxonomy.py` maps shell commands to SDLC action labels. It is the **single source of
truth** for the Phase 2 Oracle: it produces both the training **targets** and the `RECENT ACTIONS`
**features** every predictor reads. A wrong label here contaminates every downstream comparison
equally, so defects are expensive and invisible in counts (a wrong label and a right label are the
same integer).

Issue #2 is the **third** instance of one bug class: a rule token appearing as an **argument** was
read as an **invocation**. `chmod +x validate.sh` scored `run_validate`; `echo pytest` scored
`run_tests`. Governance labels are the loudest false positives because they outrank everything on tier.
The first two instances were each patched with a list of specific programs. #2 demanded the conceptual
fix instead.

## What this PR claims

The default is **inverted**: a bare-name rule now matches only in **command position**; everything
after the command is data unless the program is known to take subcommands. Supporting mechanisms:
wrappers unwrap to their child (`timeout`, `nohup`, `nice`, `sudo`, `env`, `watch`, `xargs`,
`stdbuf`, `uv run`, `git bisect run`, `/usr/bin/time`); `python -m <mod>` resolves to the module;
quoted text is data everywhere; stdout redirection makes a content producer a write. Path-shaped
governance rules still read operands, because they match a directory move rather than a name.

## What to read

The full diff is seeded read-only at `.relay-artifacts/pr16.diff`. The complete post-fix tree is
readable at:

    /private/tmp/claude-501/-Users-noelsaw-Documents-GitHub-Repos-Needle-fork/f6167b18-a9a1-4f7b-919d-5815c595807a/wt-tax

Read `/private/tmp/claude-501/-Users-noelsaw-Documents-GitHub-Repos-Needle-fork/f6167b18-a9a1-4f7b-919d-5815c595807a/wt-tax/utils/corpus/taxonomy.py` (functions `_unwrap`, `_effective_clause`, `command_region`,
`label_segment`) and `/private/tmp/claude-501/-Users-noelsaw-Documents-GitHub-Repos-Needle-fork/f6167b18-a9a1-4f7b-919d-5815c595807a/wt-tax/tests/test_taxonomy.py`.

Claimed evidence: 212 passed / 6 skipped / 6 deselected; 38 new tests, 25 witnessed failing against
the pre-fix module first; measured on 2,054 local Bash commands, 292 labels change (14.2%), coverage
98.88% → 97.21%, and 4 governance labels lost — all claimed to be false positives.

# Questions

Answer each with a verdict and `file:line` citations. **Be adversarial: your job is to find what is
wrong, not to confirm the write-up.** Assume every claim above is unverified until you check it.

1. **Is the fix actually positional, or a disguised enumeration?** `SUBCOMMAND_PROGRAMS`,
   `EXECUTORS`, `_CONTENT_PRODUCERS`, `_SUBCOMMAND_DEPTH` and `ARG_CONSUMERS` are all lists. Does
   a program absent from every one of them get labelled correctly by the DEFAULT, or does the fix
   only work for programs someone remembered? Name a realistic command that still breaks.

2. **`command_region` correctness.** Walk its token loop. Does the flag/operand/`_FILEISH`
   interaction admit a command where an operand still lands in the region? Consider `git` with
   multiple path operands, `--` separators, `=`-joined flags (`--file=x.sh`), and quoted paths
   containing spaces. `_QUOTED` blanks quotes BEFORE tokenizing — what does that do to a real path
   like `"GitHub Repos/x"`?

3. **Rule-order coupling.** The PR states rule precedence is load-bearing and that only the haystack
   per rule changed. Verify that. Does any rule now see a haystack that makes an EARLIER rule
   unreachable, or a later one reachable that was not before?

4. **The wrapper regex.** `_WRAPPERS` is one large alternation applied up to 6 times. Can it strip
   something that is not a wrapper — e.g. a file literally named `env`, or `nice` as an argument?
   Is the `xargs(?:\s+-\S+(?:\s+\d+)?)*` bound right? What about `sudo -u <user> <cmd>`?

5. **Are the negative controls real?** `test_unenumerated_program_with_a_rule_token_as_operand` is
   the class control. Would it still pass if the fix were reverted to a special-case list? If not,
   it is decorative. Check whether any new test asserts `unmapped` in a way that would pass
   vacuously.

6. **Coverage falling 98.88% → 97.21% is claimed as the intended direction.** Is that defensible, or
   is the fix now dropping labels it should keep? `sys_inspect` fell 84→68 and `run_tests` 21→8 —
   are those corrections or losses?

7. **Anything wrong, missing, over- or under-engineered** that these questions did not ask about.

Cite `file:line` wherever you disagree with a specific claim. If you find nothing substantive, say so
plainly rather than inventing findings — but say what you actually checked to reach that conclusion.

Write your verdict below. Set STATUS to Approved only if you would merge this as-is.

<!-- ▽ RELAY AUTOMATION: DO NOT MODIFY THIS BLOCK ▽ -->
▶ TAKE YOUR TURN (agy)
<!-- △ RELAY AUTOMATION: DO NOT MODIFY THIS BLOCK △ -->

## Log

### agy adversarial review (2026-09-09)

VERDICT: FAIL
Basis: Multiple critical defects invalidate the PR's core claims:
1. Operands still spoof governance invocations via `--` separators: `git diff -- validate.sh`, `git log -- validate.sh`, and `git checkout -- validate.sh` all mislabel as `run_validate` due to `command_region` flag handling.
2. The claimed "class-level control" in `tests/test_taxonomy.py:325-333` is decorative: `stat`, `realpath`, `shasum`, `basename`, and `dirname` were explicitly added to `ARG_CONSUMERS` in `utils/corpus/taxonomy.py:261-264`, short-circuiting before `command_region`.
3. True positive test runs were dropped: `run_tests` falling 21 -> 8 is not pure correction; `"$P" -m pytest` and `env -u VAR ... python -m pytest` are dropped to `unmapped` due to `_QUOTED` and `_WRAPPERS` defects.
4. Output suppression (`echo ... > /dev/null`, `cat ... > /dev/null`) is mislabeled as `apply_patch` because stdout redirection to `/dev/null` was not excluded.
5. Wrapper regexes fail on long options (`--verbose`, `--user=root`), `sudo -u <user>`, and `xargs -I {}`.
6. Subcommands are dropped for `make -C /repo test` (`_SUBCOMMAND_DEPTH = 1`) and `bash -o errexit validate.sh` (flag argument consuming token limit).

---

### Adversarial Findings by Question

#### 1. Is the fix actually positional, or a disguised enumeration?
**Verdict: Disguised enumeration for non-leaf programs; claims regarding unenumerated class controls are factually false.**

While an unenumerated leaf program taking data operands (e.g. `gzip file.txt`, `ffmpeg -i input.mp4`) defaults to `tokens[0]` (`utils/corpus/taxonomy.py:396-397`) and avoids false-positive operand matching, the mechanism fails to be generally positional:
- **False claim regarding class controls:** `SUMMARY.md:21-22, 40-41` and `tests/test_taxonomy.py:325-333` assert:
  > *"None of these programs is enumerated anywhere in the fix. If the fix were another special-case list, these would still be wrong."*
  This is refuted by `utils/corpus/taxonomy.py:261-264`:
  ```python
  "which": "sys_inspect", "command": "sys_inspect", "type": "sys_inspect",
  "whereis": "sys_inspect", "basename": "unmapped", "dirname": "unmapped",
  "realpath": "unmapped", "stat": "unmapped", "shasum": "unmapped",
  "sha256sum": "unmapped", "md5": "unmapped",
  ```
  `stat`, `realpath`, `shasum`, `basename`, and `dirname` were added directly to `ARG_CONSUMERS`. Because `label_segment` checks `lead in ARG_CONSUMERS` at line 501, before `command_region` (line 506), these utilities never exercise the positional default in production.
- **Realistic commands that break by default:**
  Any unenumerated runner or execution tool not included in `SUBCOMMAND_PROGRAMS`, `EXECUTORS`, or `_WRAPPERS` has its subcommands or target scripts severed by `lead not in SUBCOMMAND_PROGRAMS -> return tokens[0]` (`utils/corpus/taxonomy.py:396-397`):
  - `bundle exec rspec` / `bundle install`: `bundle` is not in `PKG_MANAGERS`, `SUBCOMMAND_PROGRAMS`, or `EXECUTORS`. Region is `'bundle'` -> **`unmapped`**.
  - `just test` / `just build`: `just` is an unenumerated task runner. Region is `'just'` -> **`unmapped`**.
  - `tox -e py311` / `nox -s test`: unlisted test orchestrators -> **`unmapped`**.
  - `pipenv run pytest`: unlisted runner -> **`unmapped`**.
  - `parallel pytest ::: t1 t2`: `parallel` is unlisted -> **`unmapped`**.

#### 2. `command_region` correctness
**Verdict: Critical defect — Operands after `--` land in `command_region` and cause governance false positives.**

- **The `--` Flag Loop Hole (`utils/corpus/taxonomy.py:399-408`):**
  In the token walk for `SUBCOMMAND_PROGRAMS`:
  ```python
  for tok in tokens[1:]:
      if tok.startswith("-"):
          out.append(tok)
          prev_flag = True
          continue
      if not prev_flag and _FILEISH.search(tok):
          break
      out.append(tok)
      prev_flag = False
  ```
  When `tok` is `"--"`, `tok.startswith("-")` is `True`. `out.append("--")` runs and `prev_flag` is set to `True`.
  On the subsequent token (e.g. `validate.sh`), `not prev_flag` is `False`. The `_FILEISH` break is bypassed, and `validate.sh` is appended to `out`!
  Empirical verification:
  - `git diff -- validate.sh` -> region: `'git diff -- validate.sh'` -> **`run_validate`** (`utils/corpus/taxonomy.py:200`)
  - `git log -- validate.sh` -> region: `'git log -- validate.sh'` -> **`run_validate`**
  - `git checkout -- validate.sh` -> region: `'git checkout -- validate.sh'` -> **`run_validate`**
  - `git reset -- validate.sh` -> region: `'git reset -- validate.sh'` -> **`run_validate`**
  Governance rules outrank git on tier; thus operand files following `--` spoof governance invocations, directly reintroducing Issue #2.
- **`=`-joined flags (`utils/corpus/taxonomy.py:399-402`):**
  Flags like `--output=/tmp/validate.sh` start with `-`, so they are appended without `_FILEISH` checks. Then `run_validate` regex `r"(^|[\s/])(validate\.sh)\b"` matches the `/validate.sh` segment, labeling `git log --output=/tmp/validate.sh` as **`run_validate`**.
- **Quoted paths and escaping (`utils/corpus/taxonomy.py:383`):**
  `seg = _REDIRECT.sub("", _QUOTED.sub('""', seg))`
  Blanking quoted strings before tokenization discards script operands:
  - `bash "scripts/validate.sh"` becomes `bash ""` -> region `'bash ""'` -> **`run_script`** (loses governance label).
  - Unquoted escaped spaces (`git -C GitHub\ Repos/x status`) split across tokens without quote awareness, causing `Repos/x` to hit `_FILEISH` and break before `status`, returning **`unmapped`**.

#### 3. Rule-order coupling
**Verdict: Confirmed — heredoc handling creates ordering anomalies; content producers short-circuit `BASH_RE`.**

- **Heredoc coupling with post-`run_script` rules (`utils/corpus/taxonomy.py:518-522`):**
  In `label_segment`:
  ```python
  elif name == "run_script" and _HEREDOC_BODY.search(full):
      hay = full
  ```
  Because `run_script` regex (`utils/corpus/taxonomy.py:225`) matches `<<\s*'?[A-Z_]+'?`, any command with an uppercase heredoc delimiter (e.g. `<<'EOF'`) matches `run_script` when `hay = full`. Consequently, any rule appearing *after* `run_script` in `BASH_RE` (Rules 23–31: `gh_cli`, `cloud_cli`, `db_query`, `net`, `sys_inspect`, `search_code`, `read_file`, `find_files`, `fs_mutate`) is unreachable if fed by a heredoc:
  - `sqlite3 test.db <<'EOF'` -> **`run_script`** (preempts `db_query`)
  - `psql mydb <<'EOF'` -> **`run_script`** (preempts `db_query`)
  - `ssh server <<'EOF'` -> **`run_script`** (preempts `net`)
  - `gh api graphql <<'EOF'` -> **`run_script`** (preempts `gh_cli`)
- **Content producers short-circuit (`utils/corpus/taxonomy.py:499-500`):**
  `if lead in _CONTENT_PRODUCERS and _WRITE_REDIRECT.search(seg): return "apply_patch"`
  This executes before `BASH_RE`, making all rules in `BASH_RE` unreachable for redirected content producers (even when redirecting to `/dev/null`).

#### 4. The wrapper regex
**Verdict: Multiple regex failures in `_WRAPPERS` (`utils/corpus/taxonomy.py:285-304`).**

- **`sudo -u <user>` failure:**
  Regex is `sudo(?:\s+-\w+)*`. In `sudo -u root pytest`, `-u` is stripped as `-\w+`, but `root` is not flag-shaped. `_unwrap` returns `'root pytest'`, which fails to match any rule and evaluates to **`unmapped`**.
- **`xargs` flag bound bug:**
  Regex is `xargs(?:\s+-\S+(?:\s+\d+)?)*`. For standard `xargs -I {} pytest {}`, `-I` matches `-\S+`, but `{}` is non-numeric, so it is left unconsumed. `_unwrap` returns `'{} pytest {}'`, evaluating to **`unmapped`**.
- **Long flags (`--flag`) rejected on all wrappers:**
  Flags are matched using `-\w+`. Double-dash flags (where the second character is `-`, not `\w`) fail matching and remain attached to the child:
  - `/usr/bin/time --verbose ./validate.sh` -> unwraps to `'--verbose ./validate.sh'` -> **`unmapped`**.
  - `sudo --user=root pytest` -> unwraps to `'--user=root pytest'` -> **`unmapped`**.
  - `nice --adjustment=10 pytest` -> unwraps to `'--adjustment=10 pytest'` -> **`unmapped`**.
  - `watch --interval=2 pytest` -> unwraps to `'--interval=2 pytest'` -> **`unmapped`**.
  - `stdbuf --output=L pytest` -> unwraps to `'--output=L pytest'` -> **`unmapped`**.
- **Over-stripping path names ending in `time`:**
  `(?:\S*/)?time(?:\s+-\w+)*` matches any path ending in `/time`. An invocation of a local utility or script like `./time arg1 arg2` or `bin/time run` has its binary stripped and treats `arg1`/`run` as the command.

#### 5. Are the negative controls real?
**Verdict: The class control is decorative; negative control assertions are partially vacuous.**

- **Class control is decorative (`tests/test_taxonomy.py:325-333`):**
  The test claims to evaluate programs not enumerated anywhere. But:
  - `stat`, `realpath`, `shasum`, `basename` were explicitly added to `ARG_CONSUMERS` in the PR diff (`utils/corpus/taxonomy.py:261-264`).
  - `tar` is in `BASH_RULES:235` under `sys_inspect`.
  Because `label_segment` dispatches on `ARG_CONSUMERS` at line 501, 4 of the 5 test cases (`stat`, `realpath`, `shasum`, `basename`) return `"unmapped"` directly from the dictionary lookup without ever exercising `command_region`.
- **Vacuous `unmapped` assertions (`tests/test_taxonomy.py:297`):**
  `docker run --rm ruff:latest --help` asserts `"unmapped"`. But `docker` has no label in `BASH_RULES` or `LABELS_V1`. Any Docker command evaluates to `unmapped`, so this assertion passes vacuously.

#### 6. Coverage drop and label movements
**Verdict: Undefensible loss of true positives — `run_tests` drop (21 -> 8) drops real test executions.**

The assertion in `SUMMARY.md:55-57` that coverage falling 98.88% -> 97.21% was pure false-positive elimination is contradicted by transcript evidence in `~/.claude/projects`:
- Out of 13 dropped `run_tests` commands, genuine test invocations were lost:
  1. `W=... && cd "$W" && P="..." && "$P" -m pytest -q tests/test_taxonomy.py` -> dropped to **`unmapped`** because `_QUOTED` (`taxonomy.py:383`) blanks `"$P"` into `""`, causing `_DASH_M` and `leading_program` to miss `python`.
  2. `W=... && cd "$W" && P="..." && "$P" -m pytest -q -m "not slow"` -> dropped to **`unmapped`** for the same reason.
  3. `... env -u DATABASE_URL ... ../v/bin/python -m pytest ...` -> dropped to **`unmapped`** because `_WRAPPERS` (`taxonomy.py:292`) cannot parse `env -u VAR`.
  4. `... python -m pytest ... | grep -E "passed|failed"` -> converted to **`search_code`** because `env -u` broke pytest recognition and `grep` won segment resolution.
  5. `... "$P" -m pytest ... > /tmp/red.txt && mkdir ...` -> converted to **`fs_mutate`** because broken `"$P"` recognition fell back to `mkdir`.

#### 7. Additional findings: missing & broken edge cases
- **`> /dev/null` mislabeled as `apply_patch` (`utils/corpus/taxonomy.py:330, 499-500`):**
  `_CONTENT_PRODUCERS = {"cat", "echo", "printf", "tee"}`
  `_WRITE_REDIRECT = re.compile(r"(?:^|\s)1?>>?\s*\S+")`
  `2>/dev/null` was fixed, but stdout redirection to `/dev/null` was overlooked:
  `echo "hello" > /dev/null`, `cat file.txt > /dev/null`, and `printf "" > /dev/null` all map to **`apply_patch`**. Discarding output is not patching.
- **`tee` in `_CONTENT_PRODUCERS` is ineffective (`utils/corpus/taxonomy.py:327, 499-500`):**
  `tee` writes to a file passed as an operand (`echo "text" | tee file.txt`), not via `>`. Because `_WRITE_REDIRECT` requires `>`, `echo "text" | tee file.txt` evaluates to **`unmapped`**.
- **`_SUBCOMMAND_DEPTH["make"] = 1` breaks `make` flags (`utils/corpus/taxonomy.py:314, 398-412`):**
  `make -C /repo test` and `make -f Makefile test` truncate after the directory/file flag, yielding region `'make -C /repo'` and labeling as **`run_build`** instead of **`run_tests`**.
- **Executor flag arguments truncate scripts (`utils/corpus/taxonomy.py:391-394`):**
  `bash -o errexit scripts/validate.sh`: because `len(out) > 1` and `errexit` does not start with `-`, the loop breaks immediately, yielding region `'bash -o errexit'` and scoring generic **`run_script`** instead of **`run_validate`**.
- **Git global options break recognition (`utils/corpus/taxonomy.py:251-253`):**
  `git --no-pager diff`, `git --no-pager log`, and `git -c color.ui=always status` evaluate to **`unmapped`** because `git_inspect` and `git_sync` regexes only permit `(-C\s+\S+\s+)?`.

