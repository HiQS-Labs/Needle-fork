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


# --- contract integrity --------------------------------------------------------

def test_every_rule_names_a_declared_label():
    for name, _ in tx.BASH_RULES:
        assert name in tx.LABELS_V1, name
    for name, _ in tx.PATH_RULES:
        assert name in tx.LABELS_V1, name
    for name in list(tx.NATIVE.values()) + list(tx.ARG_CONSUMERS.values()):
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
