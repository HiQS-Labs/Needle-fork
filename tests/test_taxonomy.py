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
