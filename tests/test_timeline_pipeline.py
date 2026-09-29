"""Synthetic-data tests for spike/timeline (no real prompts, repos or transcripts)."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike/timeline"))
import build_sessions as bs  # noqa: E402
import build_episodes as be  # noqa: E402

LOG = """# Agent Prompt Log
<!-- CLIO:ENTRIES -->
<!-- clio:id:aaaa:2026-01-02T10:00:00Z -->
## DEMO-REPO
2026-01-02 02:00
laptop · gh-12-fix · claude-code
> fix the parser, see https://github.com/example-org/demo-repo/issues/12

<!-- clio:id:bbbb:2026-01-02T09:00:00Z -->
## DEMO-REPO
2026-01-02 01:00
laptop · codex
> why does GH-7 fail?
# Agent Prompt Log
<!-- CLIO:ENTRIES -->
<!-- clio:id:aaaa:2026-01-02T09:30:00Z -->
## DEMO-REPO
2026-01-02 01:30
laptop · main
> "plan it first"
<!-- clio:id:aaaa:2026-01-02T10:00:00Z -->
## DEMO-REPO
2026-01-02 02:00
laptop · gh-12-fix · claude-code
> fix the parser, see https://github.com/example-org/demo-repo/issues/12
"""


def test_parse_clio_headers_meta_and_duplicates(tmp_path):
    p = tmp_path / "log.md"
    p.write_text(LOG)
    entries, raw = bs.parse_clio(str(p))
    assert raw == 4 and len(entries) == 4
    first = entries[0]
    assert (first["session_id"], first["project"], first["machine"], first["branch"], first["tool"]) == (
        "aaaa", "DEMO-REPO", "laptop", "gh-12-fix", "claude-code")
    assert first["prompt"].startswith("fix the parser")
    # 2-part meta: known tool -> tool, otherwise branch
    assert entries[1]["tool"] == "codex" and entries[1]["branch"] is None
    assert entries[2]["branch"] == "main" and entries[2]["tool"] is None
    # surrounding quotes stripped; repeated file headers are not part of any prompt
    assert entries[2]["prompt"] == "plan it first"
    assert all("Agent Prompt Log" not in e["prompt"] for e in entries)


def test_main_dedupes_sorts_and_links(tmp_path, monkeypatch):
    log = tmp_path / "log.md"
    log.write_text(LOG)
    empty = tmp_path / "none"
    empty.mkdir()
    out = tmp_path / "out"
    bs.main(["--clio-log", str(log), "--out", str(out), "--claude-dir", str(empty),
             "--codex-dir", str(empty), "--agy-dir", str(empty)])
    stats = json.loads((out / "stage1_stats.json").read_text())
    assert stats["entries_unique"] == 3 and len(stats["duplicates"]) == 1
    assert stats["duplicates"][0]["same_prompt"] is True
    rows = {json.loads(l)["session_id"]: json.loads(l) for l in (out / "sessions.jsonl").open()}
    a = rows["aaaa"]
    assert [p["ts"] for p in a["prompts"]] == sorted(p["ts"] for p in a["prompts"])  # out-of-order fixed
    assert a["repo"] == "example-org/demo-repo"
    link = next(l for l in a["links"] if l["number"] == 12)
    assert link["confidence"] == 0.8 and "clio_branch" in link["sources"] and "prompt:url" in link["sources"]


def test_codex_exec_js_wrapper_extracts_command():
    inp = 'const r = await tools.exec_command({"cmd": "git status --short", "yield_time_ms": 1000});'
    assert bs.summarize_tool("exec", inp) == {"tool": "exec", "cmd": "git status --short"}


def test_weak_labels_purpose_area_completion():
    item = {"kind": "pr", "title": "fix(parser): handle headers", "labels": ["bug"], "merged": True,
            "state": "closed", "number": 3, "resolved_repo": "example-org/demo-repo",
            "files": [".github/workflows/ci.yml", ".github/workflows/rel.yml", "src/x.py"],
            "commit_subjects": ["fix: a", "docs: b"], "_link_conf": 1.0}
    purpose = be.vote(be.purpose_votes(item, 1.0))
    assert purpose["value"] == "bug_fix" and purpose["confidence"] > 0
    assert be.area_label([item])["value"] == "ci_cd"
    assert be.completion_label([item])["value"] == "merged"
    assert be.tool_stage({"tool": "Bash", "cmd": "gh pr create --fill"}) == "pr"
