"""Regression tests for the Phase 2 Oracle label taxonomy (issue #1 §1, §2).

Both defects found while building this were visible only in the matched EVIDENCE,
never in the label counts -- a wrong label and a right label are the same integer.
So these tests assert on what a command resolves to and why, not on totals.
"""
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
