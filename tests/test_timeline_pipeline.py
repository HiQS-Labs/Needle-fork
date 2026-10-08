"""Synthetic-data tests for spike/timeline (no real prompts, repos or transcripts)."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike/timeline"))
import build_sessions as bs  # noqa: E402
import build_episodes as be  # noqa: E402
import segment_episodes as se  # noqa: E402
import validate_links as vl  # noqa: E402

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


# ------------------------------------------------------------------ segmentation
def _sess(sid="s1", prompts=(), links=(), replies=(), repo="example-org/demo-repo"):
    """A minimal sessions.jsonl-shaped record for segmentation tests."""
    return {"session_id": sid, "project": "DEMO-REPO", "repo": repo, "repo_source": "test",
            "machines": ["laptop"], "tool": "claude-code", "tool_source": "test", "branches": [],
            "transcript": None, "start_ts": prompts[0]["ts"], "end_ts": prompts[-1]["ts"],
            "n_prompts": len(prompts), "prompts": list(prompts), "replies": list(replies),
            "n_replies": len(replies), "links": list(links)}


def _p(ts, text):
    return {"ts": ts, "text": text}


def test_segment_idle_gap_splits():
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "start on GH-12"),
                       _p("2026-01-02T10:30:00Z", "continue"),
                       _p("2026-01-02T15:00:00Z", "and then finalize")])  # 4.5h gap
    eps = se.segment_session(s, min_gap_h=2.0, anchor_conf=0.5)
    assert len(eps) == 2
    assert eps[0]["prompts"][-1]["text"] == "continue"
    assert any(r.startswith("idle_gap") for r in eps[1]["start_reasons"])


def test_segment_new_task_phrase_splits_but_weak_phrases_do_not():
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "work on GH-12"),
                       _p("2026-01-02T10:05:00Z", "now do the same for the tests"),
                       _p("2026-01-02T10:10:00Z", "Next task please")])
    eps = se.segment_session(s, 2.0, 0.5)
    assert len(eps) == 2
    assert "new_task" in eps[1]["start_reasons"]


def test_segment_first_anchor_attaches_second_anchor_splits():
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "look at GH-12 first"),
                       _p("2026-01-02T10:05:00Z", "still on GH-12, check the logs"),
                       _p("2026-01-02T10:09:00Z", "GH-34 has the same bug, start there"),
                       _p("2026-01-02T10:12:00Z", "meanwhile #99 might relate")])  # bare #N: weak
    eps = se.segment_session(s, 2.0, 0.5)
    assert len(eps) == 2  # first anchor attaches; GH-34 splits; bare #99 never splits
    assert eps[0]["n_prompts"] == 2 and eps[1]["n_prompts"] == 2
    assert any(r.startswith("new_anchor:example-org/demo-repo#34") for r in eps[1]["start_reasons"])


def test_segment_first_anchor_of_an_episode_never_splits():
    # episode starts unanchored: the first strong mention attaches without a boundary
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "hello, what is going on here?"),
                       _p("2026-01-02T10:05:00Z", "let's work on GH-12 then")])
    eps = se.segment_session(s, 2.0, 0.5)
    assert len(eps) == 1 and eps[0]["n_prompts"] == 2


def test_segment_url_mention_of_other_repo_splits():
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "fix GH-12"),
                       _p("2026-01-02T10:05:00Z",
                          "then https://github.com/other-org/other-repo/pull/5 needs a look")])
    eps = se.segment_session(s, 2.0, 0.5)
    assert len(eps) == 2
    assert "other-org/other-repo#5" in eps[1]["start_reasons"][0]


def test_segment_links_assigned_by_first_ts_and_no_ts_links_flagged():
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "GH-12 work"),
                       _p("2026-01-02T12:00:00Z", "GH-34 work")],  # new anchor -> split
              links=[{"repo": "example-org/demo-repo", "number": 12, "kind": None,
                      "sources": ["prompt:GH-N"], "confidence": 0.5,
                      "first_ts": "2026-01-02T10:00:00Z", "mentions": 1},
                     {"repo": "example-org/demo-repo", "number": 34, "kind": None,
                      "sources": ["prompt:GH-N"], "confidence": 0.5,
                      "first_ts": "2026-01-02T12:00:00Z", "mentions": 1},
                     {"repo": "example-org/demo-repo", "number": 7, "kind": "pr",
                      "sources": ["claude_pr_link"], "confidence": 0.9,
                      "first_ts": None, "mentions": 1}])
    eps = se.segment_session(s, 2.0, 0.5)
    assert [(l["number"]) for l in eps[0]["links"]] == [12, 7]
    assert [l["number"] for l in eps[1]["links"]] == [34]
    assert eps[0]["links"][1].get("assignment_reason") == "no_first_ts"


def test_segment_replies_by_window_unaligned_to_first_episode():
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "GH-12"),
                       _p("2026-01-02T10:30:00Z", "GH-34"),
                       _p("2026-01-02T10:40:00Z", "more")],
              replies=[{"ts": "2026-01-02T10:10:00Z", "kind": "text", "text": "a"},
                       {"ts": "2026-01-02T10:35:00Z", "kind": "tool", "tool": "Bash"},
                       {"ts": None, "kind": "tool", "tool": "agy_step"},
                       {"ts": "2026-01-02T10:55:00Z", "kind": "text", "text": "trailing"}])
    eps = se.segment_session(s, 2.0, 0.5)
    # ep1: 10:00-10:29 -> reply a + unaligned agy step; ep2: 10:30+ -> rest (trailing clamps to last)
    assert [r.get("text") or r.get("tool") for r in eps[0]["replies"]] == ["a", "agy_step"]
    assert eps[0].get("replies_unaligned") is True
    assert [r.get("tool") for r in eps[1]["replies"]] == ["Bash", None]  # trailing text has no tool


def test_segment_episode_ids_unique_and_report_counts():
    rows = [_sess(sid="aa", prompts=[_p("2026-01-02T10:00:00Z", "GH-12"),
                                     _p("2026-01-02T14:00:00Z", "GH-34")]),
            _sess(sid="bb", prompts=[_p("2026-01-02T11:00:00Z", "hello")])]
    eps = [e for r in rows for e in se.segment_session(r, 2.0, 0.5)]
    ids = [e["session_id"] for e in eps]
    assert ids == ["aa#1", "aa#2", "bb#1"] and len(set(ids)) == 3
    assert eps[0]["n_episodes"] == 2 and eps[2]["start_reasons"] == ["session_start"]


def test_segment_accepts_fractional_timestamps():
    # transcript replies carry millisecond timestamps; prompts do not
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "GH-12"),
                       _p("2026-01-02T10:30:00Z", "GH-34")],
              replies=[{"ts": "2026-01-02T10:00:01.550Z", "kind": "text", "text": "x"}])
    eps = se.segment_session(s, 2.0, 0.5)
    assert len(eps) == 2 and eps[0]["n_replies"] == 1 and eps[1]["n_replies"] == 0


def test_segment_response_opener_demotes_gap_boundary():
    # "Yes. apply them" after a long gap answers the previous prompt: same task, no split
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "should we re-dispatch the boundary?"),
                       _p("2026-01-02T23:00:00Z", "Yes. apply them and re-dispatch."),
                       _p("2026-01-02T23:30:00Z", "did it pass?")])
    eps = se.segment_session(s, 2.0, 0.5)
    assert len(eps) == 1
    # but a strong anchor still fires through a response opener
    s2 = _sess(prompts=[_p("2026-01-02T10:00:00Z", "work on GH-12"),
                        _p("2026-01-02T23:00:00Z", "Ok, now start GH-34 instead.")])
    eps2 = se.segment_session(s2, 2.0, 0.5)
    assert len(eps2) == 2


def test_segment_cross_session_message_does_not_anchor():
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "check GH-12 status"),
                       _p("2026-01-02T10:05:00Z",
                          '<cross-session-message from="uds:/tmp/x.sock"> '
                          "see https://github.com/example-org/demo-repo/issues/99 </cross-session-message>")])
    eps = se.segment_session(s, 2.0, 0.5)
    assert len(eps) == 1


def test_segment_weak_mention_reserves_item_against_later_strong_split():
    # bare "#126" earlier + strong URL of the SAME item later: same task, no split
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "keep 126 as canonical, do not reopen 125."),
                       _p("2026-01-02T10:05:00Z",
                          "please review https://github.com/example-org/demo-repo/issues/126#issuecomment-1")])
    eps = se.segment_session(s, 2.0, 0.5)
    assert len(eps) == 1


def test_segment_qa_opener_and_prev_ref_question_demote_gap():
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "ask me some questions to align"),
                       _p("2026-01-02T14:00:00Z", "Q1: daily use. Q2: yes if shippable."),
                       _p("2026-01-02T18:00:00Z", "Is above in a worktree or already merged?")])
    eps = se.segment_session(s, 2.0, 0.5)
    assert len(eps) == 1


def test_segment_relay_paste_does_not_anchor():
    s = _sess(prompts=[_p("2026-01-02T10:00:00Z", "work on GH-12"),
                       _p("2026-01-02T10:05:00Z",
                          "From Agy: Ran command: `git remote set-url ...` and see GH-99 for context")])
    eps = se.segment_session(s, 2.0, 0.5)
    assert len(eps) == 1


# ------------------------------------------------------------------ link validation
def _episode(links=(), end="2026-01-02T11:00:00Z"):
    return {"session_id": "aa#1", "parent_session_id": "aa", "episode_index": 1, "n_episodes": 1,
            "start_reasons": ["session_start"], "project": "DEMO", "repo": "example-org/demo-repo",
            "repo_source": "t", "start_ts": "2026-01-02T10:00:00Z", "end_ts": end,
            "machines": ["laptop"], "tool": "claude-code", "tool_source": "t", "branches": [],
            "transcript": None, "prompts": [{"ts": "2026-01-02T10:00:00Z", "text": "x"}],
            "n_prompts": 1, "replies": [], "n_replies": 0, "links": list(links)}


def _link(n, sources=("prompt:#N",), conf=0.3, first_ts="2026-01-02T10:00:00Z"):
    return {"repo": "example-org/demo-repo", "number": n, "kind": None, "sources": list(sources),
            "confidence": conf, "first_ts": first_ts, "mentions": 1}


class _FakeGH:
    """items: {'owner/repo#n': {...} | 'missing'}; repos: {'owner/repo': visibility | 'missing'}"""
    def __init__(self, items, repos):
        self.items, self.repos = items, repos
        self.item_calls, self.repo_calls = [], []

    def item(self, repo, number):
        self.item_calls.append((repo, number))
        it = self.items.get(f"{repo}#{number}", "missing")
        if it == "missing":
            return {"status": "not_found"}
        return {"status": "ok", "created_at": it["created_at"], "kind": it.get("kind", "issue"),
                "title": it.get("title", "t")}

    def repo_info(self, repo):
        self.repo_calls.append(repo)
        v = self.repos.get(repo, "missing")
        if v == "missing":
            return {"status": "not_found"}
        return {"status": "ok", "visibility": v}


def test_validate_drops_404_and_keeps_existing(tmp_path):
    fake = _FakeGH(items={"example-org/demo-repo#5": {"created_at": "2026-01-01T00:00:00Z"}},
                   repos={"example-org/demo-repo": "public"})
    eps = vl.validate_episodes([_episode(links=[_link(5), _link(404)])], fake, {})
    kept = eps[0]["links"]
    assert [l["number"] for l in kept] == [5]
    assert kept[0]["repo_visibility"] == "public"
    assert [(d["number"], d["reason"]) for d in eps[0]["links_dropped"]] == [(404, "not_found")]


def test_validate_weak_link_created_after_episode_end_dropped():
    # episode ends 2026-01-02T11:00Z; +1 day slack -> item created 2026-01-04 is too late
    fake = _FakeGH(items={"example-org/demo-repo#7": {"created_at": "2026-01-04T00:00:00Z"}},
                   repos={"example-org/demo-repo": "public"})
    eps = vl.validate_episodes([_episode(links=[_link(7)])], fake, {})
    assert eps[0]["links"] == [] and eps[0]["links_dropped"][0]["reason"] == "created_after_episode_end"
    # created inside the +1d slack -> kept
    fake2 = _FakeGH(items={"example-org/demo-repo#7": {"created_at": "2026-01-03T10:59:00Z"}},
                    repos={"example-org/demo-repo": "public"})
    assert vl.validate_episodes([_episode(links=[_link(7)])], fake2, {})[0]["links"]


def test_validate_preferred_sources_skip_created_at_check():
    fake = _FakeGH(items={"example-org/demo-repo#9": {"created_at": "2026-06-01T00:00:00Z"}},
                   repos={"example-org/demo-repo": "public"})
    url_link = _link(9, sources=("prompt:url",), conf=0.7)
    mixed_link = _link(9, sources=("prompt:#N", "prompt:url"))
    nos_ts_link = _link(9, sources=("claude_pr_link",), conf=0.9, first_ts=None)
    eps = vl.validate_episodes([_episode(links=[url_link, mixed_link, nos_ts_link])], fake, {})
    assert len(eps[0]["links"]) == 3 and not eps[0].get("links_dropped")


def test_validate_public_only_filters_private_repos():
    fake = _FakeGH(items={"example-org/demo-repo#1": {"created_at": "2026-01-01T00:00:00Z"},
                          "other-org/priv#2": {"created_at": "2026-01-01T00:00:00Z"}},
                   repos={"example-org/demo-repo": "public", "other-org/priv": "private"})
    priv = _link(2); priv["repo"] = "other-org/priv"
    eps = vl.validate_episodes([_episode(links=[_link(1), priv])], fake, {})
    pub = vl.public_only(eps)
    assert [l["number"] for l in pub[0]["links"]] == [1]
    assert all(l["repo_visibility"] == "public" for e in pub for l in e["links"])


def test_validate_unresolved_and_resumability():
    class Flaky(_FakeGH):
        def item(self, repo, number):
            if number == 8:
                return {"status": "error", "detail": "HTTP 502"}
            return super().item(repo, number)

    fake = Flaky(items={"example-org/demo-repo#5": {"created_at": "2026-01-01T00:00:00Z"}},
                 repos={"example-org/demo-repo": "public"})
    eps = vl.validate_episodes([_episode(links=[_link(5), _link(8)])], fake, {})
    # an errored lookup is unresolved: link kept aside, not silently dropped
    assert [l["number"] for l in eps[0]["links"]] == [5]
    assert eps[0]["links_unresolved"][0]["number"] == 8


def test_validate_reuses_meta_cache_without_api():
    fake = _FakeGH(items={}, repos={"example-org/demo-repo": "public"})
    meta = {"example-org/demo-repo#5": {"created_at": "2026-01-01T00:00:00Z", "kind": "issue"}}
    vl.validate_episodes([_episode(links=[_link(5)])], fake, meta)
    assert fake.item_calls == []  # served from gh_meta, no API call


def test_build_episodes_flag_overrides(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    ep = {"session_id": "aa#1", "parent_session_id": "aa", "episode_index": 1, "n_episodes": 2,
          "start_reasons": ["session_start"], "project": "DEMO", "repo": "example-org/demo-repo",
          "repo_source": "t", "start_ts": "2026-01-02T10:00:00Z", "end_ts": "2026-01-02T11:00:00Z",
          "machines": ["laptop"], "tool": "claude-code", "tool_source": "t", "branches": [],
          "transcript": None, "prompts": [{"ts": "2026-01-02T10:00:00Z", "text": "fix GH-12"}],
          "n_prompts": 1, "replies": [], "n_replies": 0, "links": [], "anchor_repos": []}
    (out / "sessions_segmented.jsonl").write_text(json.dumps(ep) + "\n")
    (out / "gh_request_segmented.json").write_text(json.dumps(
        {"sessions": [{"session_id": "aa#1", "links": []}], "items": []}))
    be.main(["--all", "--out", str(out), "--sessions-file", "sessions_segmented.jsonl",
             "--request-file", "gh_request_segmented.json", "--out-name", "episodes_segmented.jsonl"])
    rows = [json.loads(l) for l in (out / "episodes_segmented.jsonl").open()]
    assert len(rows) == 1 and rows[0]["session_id"] == "aa#1"
    assert rows[0]["github_enriched"] is True
    stats = json.loads((out / "episodes_segmented_stats.json").read_text())
    assert stats["episodes"] == 1
