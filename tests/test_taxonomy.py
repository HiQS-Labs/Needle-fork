"""Regression tests for the Phase 2 Oracle label taxonomy (issue #1 §1, §2).

Both defects found while building this were visible only in the matched EVIDENCE,
never in the label counts -- a wrong label and a right label are the same integer.
So these tests assert on what a command resolves to and why, not on totals.
"""
import re
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "utils", "corpus"))

import taxonomy as tx  # noqa: E402

REPO = os.path.join(os.path.dirname(__file__), "..")


# --- segmentation --------------------------------------------------------------

def test_cd_preamble_is_not_the_intent():
    """78% of real commands start `cd "<path>" && ...`; `cd` is never the action."""
    label, _ = tx.label_bash('cd "/repo" && pytest -q')
    assert label == "run_tests"


def test_display_tail_is_not_the_intent():
    label, _ = tx.label_bash('cd "/repo" && git status | head -30')
    assert label == "git_inspect"


def test_heredoc_body_is_not_split_as_shell():
    """`python3 - <<'PY' ... PY` is one action; its body is Python, not shell."""
    cmd = "cd /repo && python3 - <<'PY'\nimport os\nos.rmdir('x')\nPY"
    assert len(tx.split_segments(cmd)) == 1
    assert tx.label_bash(cmd)[0] == "run_script"


def test_shell_loop_keywords_are_preamble():
    label, _ = tx.label_bash('for n in 1 2 3; do gh pr view $n; done')
    assert label == "review_pr"


# --- the defect that invalidated the first pass --------------------------------

def test_compound_command_is_not_labelled_by_rule_order():
    """`grep` in a compound must not be outranked just because git sorts earlier.

    The first pass matched an ordered list against the whole string, so this
    landed in `git_mutate`.
    """
    label, _ = tx.label_bash('cd "/repo" && grep -n "some_symbol" app/x.py')
    assert label == "search_code"


def test_merge_tree_is_inspection_not_mutation():
    label, _ = tx.label_bash("git merge-tree $(git merge-base origin/main HEAD) main")
    assert label == "git_inspect"


# --- the false positives that tiering introduced -------------------------------

@pytest.mark.parametrize("cmd", [
    'grep -i -E "recon|merge|release|pdda" notes.md',
    'rg -n "vendor" .xyz/relay-automation/CONSUMING.md',
    'grep -n "wave-reconcile" validate.sh',
])
def test_searching_for_a_governance_word_is_a_search(cmd):
    """A search that MENTIONS governance is not a governance move.

    Governance outranks search on tier, so without the arg-consumer rule these
    handed the highest-value labels their loudest false positives.
    """
    assert tx.label_bash(cmd)[0] == "search_code"


def test_reading_a_governance_doc_is_a_read_not_an_edit():
    label, _ = tx.label_call("Read", {"file_path": "/repo/CHANGELOG.md"})
    assert label == "read_file"


# --- governance detection ------------------------------------------------------

@pytest.mark.parametrize("cmd,expected", [
    ("utils/pdda/pdda.sh run 2>&1", "run_pdda_check"),
    ("bash relay-automation/relay-drive.sh --start", "start_relay"),
    ("python3 .xyz/utils/py/releases_app.py roadmap add --issue-num 5", "park_roadmap_row"),
    ("git mv PROJECT/1-INBOX/GH-6.md PROJECT/2-WORKING/GH-6.md", "promote_capture"),
    ("git mv PROJECT/2-WORKING/GH-6.md PROJECT/3-COMPLETED/GH-6.md", "complete_doc"),
    ("gh issue create --title x", "file_issue"),
    ("gh pr create --fill", "open_pr"),
    ("gh pr merge 12 --squash", "merge_pr"),
    ("gh release create v1.2.0", "publish_release"),
])
def test_governance_invocations(cmd, expected):
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("path,expected", [
    ("/repo/CHANGELOG.md", "update_changelog"),
    ("/repo/ROADMAP.md", "update_roadmap"),
    ("/repo/RELEASES.md", "cut_release"),
    ("/repo/PROJECT/1-INBOX/GH-9.md", "file_capture_doc"),
    ("/repo/PROJECT/2-WORKING/v0.5/FINDINGS.md", "update_working_doc"),
    ("/repo/AGENTS.md", "update_governance_doc"),
    ("/repo/src/app.py", "apply_patch"),
])
def test_edit_paths_carry_the_governance_signal(path, expected):
    """The first pass read only `command`, so every one of these was `Edit`."""
    assert tx.label_call("Edit", {"file_path": path})[0] == expected


# --- gaps found against the full Mac Studio corpus -----------------------------

@pytest.mark.parametrize("cmd,expected", [
    ("git -C /repo status", "git_inspect"),
    ("git -C /repo commit -m x", "commit_changes"),
    ("git -C /repo push origin main", "git_sync"),
])
def test_git_dash_C_does_not_break_the_git_rules(cmd, expected):
    """`git -C <path> <verb>` put 25 leading-`git` commands in `unmapped`."""
    assert tx.label_bash(cmd)[0] == expected


def test_test_conditional_is_preamble():
    """`[ -f x ] && ...` was the single largest unmapped leading token."""
    assert tx.label_bash('[ -f pyproject.toml ] && pytest -q')[0] == "run_tests"


@pytest.mark.parametrize("cmd,expected", [
    ("python3 -m pytest tests/", "run_tests"),
    ("npx tsc --noEmit", "run_build"),
    ("swift build/run.swift", "run_script"),
    ("$TICK/scripts/run.sh --once", "run_script"),
    ("sleep 2", "sys_inspect"),
])
def test_interpreters_and_plumbing(cmd, expected):
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("tool,expected", [
    ("mcp__github__issue_read", "read_issue"),
    ("mcp__github__issue_write", "file_issue"),
    ("mcp__github__pull_request_read", "review_pr"),
    ("mcp__github__get_commit", "git_inspect"),
    ("mcp__github__some_new_thing", "gh_cli"),
    ("mcp__codebase_memory__list_projects", "session_control"),
])
def test_mcp_tools_carry_intent_in_the_name(tool, expected):
    """MCP calls need no command parsing; longest prefix wins."""
    assert tx.label_call(tool, {})[0] == expected


# --- package managers take package NAMES, not invocations ----------------------

@pytest.mark.parametrize("cmd,expected", [
    ("uv add ruff", "pkg_manage"),          # installing ruff, not running it
    ("uv add black", "pkg_manage"),
    ("pip install pytest", "pkg_manage"),
    ("brew install shellcheck", "pkg_manage"),
])
def test_installing_a_tool_is_not_running_it(cmd, expected):
    """`uv add ruff` was labelled run_linter: a package name read as an invocation.

    Same class as a grep whose pattern mentions a governance word.
    """
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("cmd,expected", [
    ("uv run pytest -q", "run_tests"),
    ("poetry run pytest", "run_tests"),
    ("npm run build", "run_build"),
])
def test_package_managers_still_delegate(cmd, expected):
    """They are runners too, so `run`/`exec` must fall through to the real action."""
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("cmd", ["pip list", "pip show needle", "brew list",
                                 "pip freeze > requirements.txt", "npm ls"])
def test_dependency_inspection_is_package_management(cmd):
    """Tightening pkg_manage to install-only dropped these to `unmapped`, which is
    most of why the label fell under the support floor."""
    assert tx.label_bash(cmd)[0] == "pkg_manage"


# --- contract integrity --------------------------------------------------------

def test_every_rule_names_a_declared_label():
    for name, _ in tx.BASH_RULES:
        assert name in tx.LABELS_V1, name
    for name, _ in tx.PATH_RULES:
        assert name in tx.LABELS_V1, name
    for name in list(tx.NATIVE.values()) + list(tx.ARG_CONSUMERS.values()):
        assert name in tx.LABELS_V1, name
    for _, name in tx.MCP_RULES:
        assert name in tx.LABELS_V1, name


def test_coverage_gate_counts_unmapped():
    assert tx.coverage(["read_file", "unmapped", "read_file", "run_tests"]) == 0.75
    assert tx.coverage([]) == 0.0


def test_published_contract_matches_the_taxonomy():
    """oracle/labels-v1.json is generated; a stale checked-in copy is a drift bug."""
    path = os.path.join(REPO, "oracle", "labels-v1.json")
    contract = json.load(open(path))
    assert contract["label_set_version"] == tx.LABEL_SET_VERSION
    assert set(contract["labels"]) == set(tx.LABELS_V1)
    assert len(contract["schemas"]) == len(tx.LABELS_V1)


def test_support_floor_is_a_supplementation_gate_not_a_delete_gate():
    """Adjudicated 2026-09-07 — see the decision record in taxonomy.py.

    `pkg_manage` was about to be merged into `run_script` on a 60-call count that
    was an artifact of two bugs in taxonomy.py itself; fixing them took it to 111.
    This test exists so the floor cannot quietly become a pruning rule again.
    """
    assert tx.SUPPORT_FLOOR_ACTION == "supplement"
    contract = json.load(open(os.path.join(REPO, "oracle", "labels-v1.json")))
    assert contract["support_floor"]["action"] == "supplement"
    # The three governance stragglers and the abstention target stay in the contract.
    for label in ("promote_capture", "park_roadmap_row", "publish_release", "no_action"):
        assert label in tx.LABELS_V1
        assert label in contract["labels"]


def test_pkg_manage_and_run_script_are_distinct_concepts():
    """The merge that was rejected: dependency management is not ad-hoc execution."""
    assert tx.label_bash("pip install -r requirements.txt")[0] == "pkg_manage"
    assert tx.label_bash("python3 - <<'PY'\nprint(1)\nPY")[0] == "run_script"
    assert tx.LABELS_V1["pkg_manage"]["group"] == "code"
    assert "pkg_manage" in tx.LABELS_V1 and "run_script" in tx.LABELS_V1


def test_label_schemas_take_no_arguments():
    """Ponytail Output Simplification: the model predicts a name, never arguments."""
    contract = json.load(open(os.path.join(REPO, "oracle", "labels-v1.json")))
    for schema in contract["schemas"]:
        assert schema["parameters"]["properties"] == {}, schema["name"]


def test_exporter_is_reproducible(tmp_path):
    out = tmp_path / "labels.json"
    subprocess.run([sys.executable, "utils/corpus/export_label_schemas.py", "--out", str(out)],
                   cwd=REPO, check=True, capture_output=True)
    assert json.load(open(out)) == json.load(open(os.path.join(REPO, "oracle", "labels-v1.json")))


# --- #2: a rule's token in an ARGUMENT position is not an invocation ------------
#
# Third instance of this bug class. The first two were fixed with lists of specific
# programs (ARG_CONSUMERS, PKG_MANAGERS); the class is broader than any list, so
# these tests assert the POSITIONAL property, not the 14 reported commands.
#
# Every case below scored a wrong label before the fix. Governance labels are the
# loudest false positives because they outrank everything on tier, so an operand
# beats the real action.

@pytest.mark.parametrize("cmd,expected", [
    # wrappers: the intent is the wrapped child, not the wrapper
    ("timeout 5 echo pytest",              "unmapped"),
    ("nohup sleep 1 > validate.sh",        "sys_inspect"),
    ("xargs -I{} echo pytest {}",          "unmapped"),
    ("nice -n 10 make",                    "run_build"),
    ("sudo apt-get install ripgrep",       "pkg_manage"),
    ("env FOO=1 pytest -q",                "run_tests"),
    ("stdbuf -oL pytest",                  "run_tests"),
])
def test_wrapper_delegates_to_its_child(cmd, expected):
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("cmd,expected", [
    ("python3 -c \"print('ruff')\"",       "run_script"),
    ("node -e \"console.log('pytest')\"",  "run_script"),
    ("sh -c 'validate.sh'",                "run_script"),
])
def test_inline_interpreter_body_is_data_not_invocation(cmd, expected):
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("cmd,expected", [
    ("echo pytest",                        "unmapped"),
    ("touch requirements.txt",             "fs_mutate"),
    ("cp requirements.txt /tmp/",          "fs_mutate"),
    ("mv requirements.txt old.txt",        "fs_mutate"),
    ("chmod +x validate.sh",               "fs_mutate"),
    ("mv validate.sh scripts/",            "fs_mutate"),
    ("make validate.sh",                   "run_build"),
    ("make relay-drive.sh",                "run_build"),
    ("docker run --rm ruff:latest --help", "unmapped"),
    ("which ruff uv",                      "sys_inspect"),
    ("command -v ruff uv uvx pipx python3", "sys_inspect"),
])
def test_operand_is_not_an_invocation(cmd, expected):
    assert tx.label_bash(cmd)[0] == expected


def test_git_bisect_run_is_a_git_operation_not_its_probe():
    """`git bisect run echo validate.sh` was run_validate -- the loudest possible miss."""
    assert tx.label_bash("git bisect run echo validate.sh")[0] == "git_inspect"


@pytest.mark.parametrize("cmd,expected", [
    ("git checkout main -- scripts/x.sh requirements.txt", "git_sync"),
    ('ssh -i "$HOME/.ssh/id_ed25519" host "ls requirements.txt"', "net"),
])
def test_real_corpus_commands_that_were_mislabelled(cmd, expected):
    assert tx.label_bash(cmd)[0] == expected


def test_quoted_text_is_data_not_an_invocation():
    """A commit message naming a governance script is not running it."""
    assert tx.label_bash('git commit -m "run validate.sh before merging"')[0] == "commit_changes"
    assert tx.label_bash('echo "pdda.sh roadmap"')[0] == "unmapped"


@pytest.mark.parametrize("cmd,expected", [
    # THE CLASS CONTROL. None of these programs is enumerated anywhere in the fix.
    # If the fix were another special-case list, these would still be wrong.
    ("tar -czf backup.tgz validate.sh",     "sys_inspect"),
    ("shasum -a 256 pdda.sh",               "unmapped"),
    ("basename /opt/relay-drive.sh",        "unmapped"),
    ("realpath requirements.txt",           "unmapped"),
    ("stat validate.sh",                    "unmapped"),
])
def test_unenumerated_program_with_a_rule_token_as_operand(cmd, expected):
    assert tx.label_bash(cmd)[0] == expected


# --- positive controls: the fix must not silence real invocations --------------

@pytest.mark.parametrize("cmd,expected", [
    ("./validate.sh",                                        "run_validate"),
    ("bash scripts/validate.sh --fast",                      "run_validate"),
    ("pdda.sh roadmap",                                      "run_pdda_check"),
    ("xyz validate",                                         "run_validate"),
    ("relay-drive.sh --id 1",                                "start_relay"),
    ("pytest -q",                                            "run_tests"),
    ("ruff check .",                                         "run_linter"),
    ("uv run pytest",                                        "run_tests"),
    ("uv add ruff",                                          "pkg_manage"),
    ("pip install -r requirements.txt",                      "pkg_manage"),
    ("npm run build",                                        "run_build"),
    ("git -C /repo status",                                  "git_inspect"),
    ("git tag -a v1.0.0 -m release",                         "publish_release"),
    ("mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md",       "promote_capture"),
    ("sed -i 's/a/b/' f.py",                                 "apply_patch"),
    ("sed -n '1,20p' f.py",                                  "read_file"),
    ("cd /repo && pytest -q",                                "run_tests"),
])
def test_real_invocations_still_labelled(cmd, expected):
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("cmd,expected", [
    ("git commit -q -F - <<'EOF'",           "commit_changes"),
    ("gh pr create --body-file - <<'EOF'",   "open_pr"),
    ("python3 - <<'PY'",                     "run_script"),
    ("cat > notes.md <<'EOF'",               "apply_patch"),   # writes, not reads
    ("cat notes.md",                         "read_file"),
    ("cat notes.md 2>/dev/null",             "read_file"),    # stderr is not a write
    ("cat -n f.py 2>&1",                     "read_file"),
])
def test_heredoc_does_not_outrank_the_command_it_feeds(cmd, expected):
    """A heredoc supplies an argument; it does not change what is being run.

    Found by diffing a re-extraction, not by a unit test: hoisting the heredoc
    check above the ordered rules turned 44 real `git commit -F -` calls in the
    local corpus into `run_script`. Rule precedence is load-bearing, so the
    positional fix changes only the haystack each rule sees, never the order.
    """
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("cmd,expected", [
    (".venv/bin/python -m pip install -q pydantic", "pkg_manage"),
    ("python3 -m pytest tests/ -q",                 "run_tests"),
    ("python3 -m mymodule --flag",                  "run_script"),   # unknown module
    ("/usr/bin/time -p python3 utils/x.py",         "run_script"),
    ('echo "=== A ==="; python3 - <<\'PY\'',        "run_script"),
])
def test_dash_m_and_timing_wrappers_name_the_real_program(cmd, expected):
    """`-m` names the program being run; `time` is a stopwatch, not the action."""
    assert tx.label_bash(cmd)[0] == expected


def test_governance_move_survives_a_heredoc_joined_segment():
    """A heredoc stops segment splitting, so the promotion shares a segment with setup.

    Path-shaped governance rules therefore read the WHOLE segment, while name-based
    rules read only the command position. Reducing the segment before both hid a real
    `git mv PROJECT/2-WORKING -> PROJECT/3-COMPLETED` behind the `mkdir` in front of it.
    """
    cmd = ('cd "/repo" && mkdir -p PROJECT/3-COMPLETED/v0.5'
           ' && git mv PROJECT/2-WORKING/v0.5/GH-10.md PROJECT/3-COMPLETED/v0.5/GH-10.md'
           " && .venv/bin/python - <<'PY'")
    assert tx.label_bash(cmd)[0] == "complete_doc"


# --- #2 round 2: defects found by agy's adversarial review of PR #16 -------------

@pytest.mark.parametrize("cmd,expected", [
    # `--` is END OF OPTIONS; everything after it is an operand by definition.
    ("git diff -- validate.sh",              "git_inspect"),
    ("git log -- validate.sh",               "git_inspect"),
    ("git checkout -- validate.sh",          "git_sync"),
    ("git log --output=/tmp/validate.sh",    "git_inspect"),   # `=`-joined value is data
])
def test_operands_after_end_of_options_cannot_spoof_governance(cmd, expected):
    """The first fix treated `--` as a flag, so it skipped the operand break.

    That left a filename operand in command position and `git diff -- validate.sh`
    scored run_validate -- reintroducing the exact defect #2 exists to remove.
    """
    assert tx.label_bash(cmd)[0] == expected


def test_the_class_control_programs_are_genuinely_unenumerated():
    """Pins that the class control actually tests the positional default.

    The first fix added stat/realpath/shasum/basename/dirname to ARG_CONSUMERS, which
    is checked BEFORE command_region -- so the control asserting "none of these is
    enumerated anywhere" passed while the diff enumerated them. This test makes that
    mistake impossible to repeat silently.
    """
    for program in ("stat", "realpath", "shasum", "basename", "dirname", "tar", "gzip"):
        assert program not in tx.ARG_CONSUMERS, program
        assert program not in tx.SUBCOMMAND_PROGRAMS, program
        assert program not in tx.EXECUTORS, program
        assert program not in tx._CONTENT_PRODUCERS, program


@pytest.mark.parametrize("cmd,expected", [
    ('bash "scripts/validate.sh"',           "run_validate"),   # quoted script path
    ('"$P" -m pytest -q tests/',             "run_tests"),      # quoted interpreter var
    ("env -u FOO python -m pytest",          "run_tests"),
    ("bash -o errexit scripts/validate.sh",  "run_validate"),   # flag arg is not the script
])
def test_quoted_operands_survive_tokenisation(cmd, expected):
    """Blanking quotes BEFORE tokenising destroyed the operand, dropping real runs."""
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("cmd,expected", [
    ('echo "hi" > /dev/null',                "unmapped"),       # discard, not a write
    ("cat f.txt > /dev/null",                "read_file"),
    ('echo "x" | tee out.txt',               "apply_patch"),    # tee writes via operand
])
def test_discarding_output_is_not_a_write(cmd, expected):
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("cmd,expected", [
    ("sudo -u root pytest",                  "run_tests"),
    ("xargs -I {} pytest {}",                "run_tests"),
    ("/usr/bin/time --verbose ./validate.sh", "run_validate"),
    ("nice --adjustment=10 pytest",          "run_tests"),
    ("watch --interval=2 pytest",            "run_tests"),
])
def test_wrappers_accept_long_and_argument_taking_flags(cmd, expected):
    """`-\\w+` matched no `--long-flag`, so the flag stayed glued to the child."""
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("cmd,expected", [
    ("sqlite3 test.db <<'EOF'",              "db_query"),
    ("ssh server <<'EOF'",                   "net"),
    ("gh api graphql <<'EOF'",               "gh_cli"),
    ("python3 - <<'PY'",                     "run_script"),     # still the fallback
])
def test_heredoc_is_a_fallback_not_a_preemption(cmd, expected):
    """Testing the heredoc inside the ordered pass made every later rule unreachable."""
    assert tx.label_bash(cmd)[0] == expected


@pytest.mark.parametrize("cmd,expected", [
    ("make -C /repo test",                   "run_tests"),
    ("git --no-pager diff",                  "git_inspect"),
    ("git -c color.ui=always status",        "git_inspect"),
])
def test_global_options_do_not_hide_the_subcommand(cmd, expected):
    assert tx.label_bash(cmd)[0] == expected


# --- #2 round 3: escapes found by agent2 (AgentChorus #309930) -------------------
# Contrast pairs. Each REAL invocation must keep its label while an INERT copy of the
# same trigger -- quoted, or sitting in an option value -- must not acquire it. A
# suite that only asserts `unmapped` can pass by labelling nothing.

@pytest.mark.parametrize("real,inert,label", [
    # a genuine PDDA promotion vs. a printed copy of one
    ("mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md",
     'echo "mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"', "promote_capture"),
    ("git mv PROJECT/2-WORKING/a.md PROJECT/3-COMPLETED/a.md",
     'echo "git mv PROJECT/2-WORKING/a.md PROJECT/3-COMPLETED/a.md"', "complete_doc"),
    ("releases_app.py roadmap add",
     'echo "releases_app.py roadmap add"', "park_roadmap_row"),
    ("./validate.sh",
     'python3 -c "print(\'./validate.sh\')"', "run_validate"),
])
def test_an_inert_copy_of_a_trigger_does_not_acquire_its_label(real, inert, label):
    assert tx.label_bash(real)[0] == label, "the real invocation must still be caught"
    assert tx.label_bash(inert)[0] != label, "a printed copy is a display, not the act"


@pytest.mark.parametrize("cmd,expected", [
    ("git -C /tmp/validate.sh status",   "git_inspect"),
    ("make -C /tmp/validate.sh test",    "run_tests"),
    ("git -C /repo status",              "git_inspect"),   # positive control
    ("make -C /repo test",               "run_tests"),     # positive control
])
def test_an_option_value_is_data_not_command_text(cmd, expected):
    """A flag's argument was kept verbatim in the region, so a path handed to `-C`
    was searchable by the governance rules and spoofed `run_validate`."""
    assert tx.label_bash(cmd)[0] == expected


# --- MUTATION CONTROLS ----------------------------------------------------------
# A table-membership assertion shows a program is unlisted; it does NOT show that the
# positional guard is the reason a test passes. These disable the guard and require
# the controls to go red, which is the only way to prove the guard is load-bearing
# (agent2, AgentChorus #309930). Without them the suite could pass for the wrong
# reason -- exactly how the first class-level control came to be decorative.

def test_disabling_the_positional_restriction_makes_the_class_controls_fail(monkeypatch):
    """Restore whole-segment matching: every operand must spoof its rule again."""
    monkeypatch.setattr(tx, "command_region", lambda seg: seg)
    spoofed = [
        ("chmod +x validate.sh",            "run_validate"),
        ("stat validate.sh",                "run_validate"),
        ("tar -czf backup.tgz validate.sh", "run_validate"),
        ("echo pytest",                     "run_tests"),
    ]
    for cmd, wrong in spoofed:
        assert tx.label_bash(cmd)[0] == wrong, (
            f"{cmd!r} did not revert to {wrong} with the guard disabled -- the "
            "control is passing for some other reason and proves nothing")


def test_the_requirements_txt_fix_is_a_RULE_change_not_the_positional_guard(monkeypatch):
    """Attribution control, and it caught me mis-crediting a fix.

    `touch requirements.txt` was in the positional mutation list above, but it does
    NOT revert when the guard is disabled: it was fixed by deleting the bare
    `requirements.txt` alternative from the pkg_manage rule, since a real install
    already matches through its package manager. Two mechanisms landed in one PR and
    I credited the wrong one. Pinning both halves so the attribution stays honest.
    """
    monkeypatch.setattr(tx, "command_region", lambda seg: seg)
    assert tx.label_bash("touch requirements.txt")[0] == "fs_mutate", \
        "with the positional guard disabled this must STILL be right -- a rule fix"
    assert not any("requirements" in pattern for _, pattern in tx.BASH_RULES
                   if _ == "pkg_manage"), "the operand-driven alternative must stay gone"
    assert tx.label_bash("pip install -r requirements.txt")[0] == "pkg_manage", \
        "a real install must still be package management"


def test_disabling_the_invocation_gate_lets_display_text_spoof_governance(monkeypatch):
    """Remove the role gate: printed text must be able to spoof a governance move."""
    monkeypatch.setattr(tx, "ANY_POSITION_GATE",
                        {name: (lambda clause: True) for name in tx.ANY_POSITION})
    assert tx.label_bash("echo mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md")[0] == "promote_capture"
    assert tx.label_bash("echo releases_app.py roadmap add")[0] == "park_roadmap_row"


def test_the_guards_are_what_make_the_real_cases_pass():
    """Green side of the two mutations above, at the same revision."""
    assert tx.label_bash("chmod +x validate.sh")[0] == "fs_mutate"
    assert tx.label_bash("stat validate.sh")[0] == "unmapped"
    assert tx.label_bash("echo mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md")[0] == "unmapped"
    # ...while the real invocations they guard still land.
    assert tx.label_bash("mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md")[0] == "promote_capture"
    assert tx.label_bash("./validate.sh")[0] == "run_validate"


@pytest.mark.parametrize("cmd,expected", [
    ("echo mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md",   "unmapped"),
    ("echo releases_app.py roadmap add",                      "unmapped"),
    ('mv "PROJECT/1-INBOX/a.md" "PROJECT/2-WORKING/a.md"',    "promote_capture"),
    ('git mv "PROJECT/2-WORKING/a.md" "PROJECT/3-COMPLETED/a.md"', "complete_doc"),
    ("python3 .xyz/utils/py/releases_app.py roadmap add",     "park_roadmap_row"),
])
def test_role_is_established_before_operands_are_read(cmd, expected):
    """Blanket quote-blanking failed in BOTH directions: it left unquoted display data
    spoofing governance, and destroyed the operands of a real move written with quoted
    paths. The rule is role first, then operands with their values intact."""
    assert tx.label_bash(cmd)[0] == expected


# ---------------------------------------------------------------------------
# GH-17: agy's round-5 adversarial review. Every case below was REPRODUCED as a
# defect against b33b92a before this block existed (21/21 of agy's claims
# confirmed, 0 refuted). Grouped by the mechanism that produced them.
# ---------------------------------------------------------------------------


# 1. Quoted text forges a clause boundary -- the 4th instance of the bug class.
#    `_operand_clauses` split on ;/&&/|| with a plain regex, BEFORE quotes were
#    considered, so a commit message could manufacture a clause whose leading
#    program was `mv`.
def test_quoted_text_cannot_forge_a_governance_clause():
    assert tx.label_bash(
        'git commit -m "docs: add note; mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"'
    )[0] == "commit_changes"


def test_quoted_git_mv_inside_echo_is_still_display():
    assert tx.label_bash(
        'echo "test; git mv PROJECT/2-WORKING/a.md PROJECT/3-COMPLETED/a.md"'
    )[0] == "unmapped"


def test_quoted_move_inside_inline_python_is_not_a_promotion():
    assert tx.label_bash(
        'python3 -c "x = 1; mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"'
    )[0] == "run_script"


# ...and the same splitter destroyed a REAL move whose path contained a `;`.
def test_a_semicolon_inside_a_quoted_path_does_not_split_the_move():
    assert tx.label_bash(
        'mv "PROJECT/1-INBOX/note;1.md" "PROJECT/2-WORKING/note;1.md"'
    )[0] == "promote_capture"


# 2. Inline interpreter code is DATA, quoted or not. `text(tok, keep=False)`
#    returned an unquoted token intact, so `keep=False` was silently ignored.
def test_inline_code_operands_are_never_invocations():
    for cmd in ('python3 -c "import sys" validate.sh',
                'python3 -c print(ruff)',
                'python3 -c import(pytest)'):
        assert tx.label_bash(cmd)[0] == "run_script", cmd


# 3. Environment-variable prefixes. `leading_program` skips `KEY=val`;
#    `command_region` indexed tokens[0] unconditionally and read the assignment
#    as the program, dropping real invocations to `unmapped`.
def test_env_prefixes_do_not_hide_the_program():
    cases = [("CI=1 ./validate.sh", "run_validate"),
             ("PYTHONPATH=. pytest", "run_tests"),
             ("DEBUG=1 ruff check .", "run_linter"),
             ("FOO=bar bash scripts/validate.sh", "run_validate"),
             ("FOO=1 make test", "run_tests")]
    for cmd, want in cases:
        assert tx.label_bash(cmd)[0] == want, cmd


def test_env_prefixed_roadmap_tool_still_gates():
    assert tx.label_bash(
        "PYTHONPATH=. ./releases_app.py roadmap add"
    )[0] == "park_roadmap_row"


# 4. Boolean short flags. Every short flag was assumed to take an argument, so
#    a boolean one ate the subcommand.
def test_boolean_short_flags_do_not_swallow_the_subcommand():
    for cmd, want in [("git -p diff", "git_inspect"),
                      ("git -v status", "git_inspect"),
                      ("make -s test", "run_tests")]:
        assert tx.label_bash(cmd)[0] == want, cmd


def test_short_flags_that_DO_take_an_argument_still_consume_it():
    # The negative side of the same rule: -C must still eat its path, or the
    # path becomes readable as an invocation again (the #309930 defect).
    assert tx.label_bash("git -C /tmp/validate.sh status")[0] == "git_inspect"
    assert tx.label_bash("make -C /repo test")[0] == "run_tests"


# 5. Long flags whose argument is a path: _FILEISH broke the walk before the
#    subcommand was reached.
def test_long_flag_path_arguments_do_not_truncate_the_walk():
    for cmd, want in [("cargo --manifest-path /path/Cargo.toml test", "run_tests"),
                      ("uv --directory /path run pytest", "run_tests")]:
        assert tx.label_bash(cmd)[0] == want, cmd


# 6. A branch NAME may contain a slash. _FILEISH treated it as an operand and
#    truncated `git branch feat/x` to `git branch`, which no longer matches.
def test_branch_names_with_slashes_still_create_a_branch():
    assert tx.label_bash("git branch feat/new-login")[0] == "create_branch"


def test_a_branch_name_is_still_not_readable_as_an_invocation():
    # It must be consumed as DATA, not kept as matchable text.
    assert "validate.sh" not in tx.command_region("git branch feat/validate.sh")


# 7. _is_move took token 2 literally, so any git global flag broke the gate and
#    demoted a real governance move to fs_mutate.
def test_git_global_flags_do_not_break_the_move_gate():
    assert tx.label_bash(
        "git -C /repo mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"
    )[0] == "promote_capture"
    assert tx.label_bash(
        "git -C /repo mv PROJECT/2-WORKING/a.md PROJECT/3-COMPLETED/a.md"
    )[0] == "complete_doc"


# ---------------------------------------------------------------------------
# GH-17 mutation controls. agy's round-5 finding: the existing controls pinned
# `command_region` and `ANY_POSITION_GATE` as WHOLE switches, so every mechanism
# INSIDE command_region could be corrupted with the suite staying green. Each
# control below disables exactly one mechanism and requires the defect to return.
# ---------------------------------------------------------------------------


def test_control_disabling_quote_aware_splitting_restores_governance_spoofing(monkeypatch):
    """The 4th instance of the bug class returns if the splitter stops respecting quotes."""
    monkeypatch.setattr(tx, "_split_outside_quotes",
                        lambda seg: re.split(r"&&|\|\||;", seg))
    assert tx.label_bash(
        'git commit -m "docs: add note; mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md"'
    )[0] == "promote_capture"          # RED: the defect is back


def test_control_disabling_the_env_prefix_skip_drops_real_commands(monkeypatch):
    monkeypatch.setattr(tx, "_ENV_ASSIGN", re.compile(r"(?!)"))   # matches nothing
    for cmd in ("CI=1 ./validate.sh", "PYTHONPATH=. pytest"):
        assert tx.label_bash(cmd)[0] == "unmapped", cmd


def test_end_of_options_operands_are_not_invocations():
    # A pathspec need not look file-ish, so _FILEISH cannot cover this case --
    # only the `--` break can.
    assert tx.label_bash("git diff -- pytest")[0] == "git_inspect"


def test_control_disabling_end_of_options_lets_operands_into_the_command_region(monkeypatch):
    # Asserted on command_region, not on the final label: at label level
    # `git_inspect` matches `diff` and wins on rule order whether or not the
    # operand leaked, so a label assertion would pass with the mechanism removed
    # -- a decorative control, which is agy's GH-17 objection turned on itself.
    # `pytest` is deliberately NOT file-ish, so _FILEISH cannot cover this.
    assert "pytest" not in tx.command_region("git diff -- pytest")
    monkeypatch.setattr(tx, "_END_OF_OPTIONS", "\0")              # never matches
    assert "pytest" in tx.command_region("git diff -- pytest")     # RED: it leaks


def test_control_disabling_fileish_lets_operands_be_read_as_invocations(monkeypatch):
    monkeypatch.setattr(tx, "_FILEISH", re.compile(r"(?!)"))
    assert tx.label_bash("make validate.sh")[0] == "run_validate"


def test_control_claiming_every_short_flag_takes_an_argument_swallows_subcommands(monkeypatch):
    """The pre-GH-17 behaviour, restored: boolean flags eat the subcommand."""
    class _All:
        def get(self, _k, _d=None):
            class _S:
                def __contains__(self, _x): return True
            return _S()
    monkeypatch.setattr(tx, "_SHORT_TAKES_ARG", _All())
    assert tx.label_bash("git -p diff")[0] == "unmapped"


def test_control_disabling_the_branch_name_placeholder_demotes_create_branch(monkeypatch):
    monkeypatch.setattr(tx, "_BRANCH_SUBCOMMANDS", frozenset())
    assert tx.label_bash("git branch feat/new-login")[0] == "git_inspect"


def test_control_invocation_gate_covers_all_three_ANY_POSITION_labels(monkeypatch):
    """agy: the old gate control omitted complete_doc, the third member."""
    assert tx.ANY_POSITION == {"promote_capture", "complete_doc", "park_roadmap_row"}
    monkeypatch.setattr(tx, "ANY_POSITION_GATE",
                        {k: (lambda _c: True) for k in tx.ANY_POSITION})
    spoofs = [("echo mv PROJECT/1-INBOX/a.md PROJECT/2-WORKING/a.md", "promote_capture"),
              ("echo mv PROJECT/2-WORKING/a.md PROJECT/3-COMPLETED/a.md", "complete_doc"),
              ("echo releases_app.py roadmap add", "park_roadmap_row")]
    for cmd, spoofed in spoofs:
        assert tx.label_bash(cmd)[0] == spoofed, cmd


# CodeRabbit, PR #18. Two defects introduced BY the GH-17 fix, both reproduced
# before being fixed.
def test_make_j_without_a_number_still_runs_the_target():
    # GNU make reads `make -j test` as target `test`. Consuming it as -j's
    # argument produced `make -j ""` -> run_build.
    assert tx.label_bash("make -j test")[0] == "run_tests"
    assert tx.label_bash("make -j 4 test")[0] == "run_tests"   # numeric arg still eaten
    assert tx.label_bash("make -j4 test")[0] == "run_tests"


def test_a_quoted_assignment_with_spaces_stays_one_token():
    # `TITLE="fix pytest flake" git commit` scored run_tests: _TOKEN split the
    # assignment, so the quoted TEXT landed in command position -- the same bug
    # class, arriving through the tokenizer.
    assert tx.label_bash('TITLE="fix pytest flake" git commit -m "x"')[0] == "commit_changes"
    assert "pytest" not in tx.command_region('TITLE="fix pytest flake" git commit -m "x"')


# ---------------------------------------------------------------------------
# GH-17 final round (codex). The 7th and 8th routes to the same bug class.
# ---------------------------------------------------------------------------


def test_an_unlisted_long_option_does_not_truncate_the_walk():
    """codex: `git --exec-path <path> status` scored unmapped.

    The long-flag ALLOWLIST could not know `--exec-path` takes an argument, so
    _FILEISH read the path as the start of operands. A value is now recognised
    by SHAPE, which needs no table -- the allowlist was a return to the pattern
    that had already been escaped twice.
    """
    assert tx.label_bash("git --exec-path /tmp/validate.sh status")[0] == "git_inspect"
    assert tx.label_bash("cargo --manifest-path /path/Cargo.toml test")[0] == "run_tests"
    assert tx.label_bash("uv --directory /path run pytest")[0] == "run_tests"
    # ...and the value never becomes readable as an invocation.
    assert "validate.sh" not in tx.command_region("git --exec-path /tmp/validate.sh status")


def test_an_unquoted_message_is_not_an_invocation():
    """Found while probing codex's finding for the same shape elsewhere.

    `git tag -m ruff v1` scored run_linter: the message word sat in command
    position. Prose-carrying flags now consume their argument.
    """
    assert tx.label_bash("git tag -m ruff v1")[0] != "run_linter"
    assert "ruff" not in tx.command_region("git tag -m ruff v1")
    assert "pytest" not in tx.command_region("git commit -m pytest")


def test_control_disabling_the_value_shape_rule_truncates_the_walk(monkeypatch):
    monkeypatch.setattr(tx, "_VALUE_SHAPED", re.compile(r"(?!)"))   # matches nothing
    assert tx.label_bash("git --exec-path /tmp/validate.sh status")[0] == "unmapped"


def test_control_disabling_prose_flags_lets_a_message_score_a_label(monkeypatch):
    monkeypatch.setattr(tx, "_PROSE_FLAGS", frozenset())
    assert tx.label_bash("git tag -m ruff v1")[0] == "run_linter"
