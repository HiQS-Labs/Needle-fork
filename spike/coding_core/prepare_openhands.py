#!/usr/bin/env python3
"""Stream a bounded OpenHands shard into the six-label coding-core pilot."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Iterable
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "utils" / "corpus"))
import taxonomy  # noqa: E402

DATASET = "nebius/SWE-rebench-openhands-trajectories"
REVISION = "35455389ab51bf5e2306bfd436ef72d0f98bf882"
FORMAT_VERSION = "coding-core-q1"
LABELS = ("edit", "git", "read", "run_command", "run_tests", "search")
SYSTEM = "Given the issue and recent coding actions, predict the single best next broad action."


class InputError(ValueError):
    pass


def _json_value(value, field):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise InputError(f"{field} is invalid serialized JSON") from exc
    return value


def project_bash(command: str) -> str:
    if not isinstance(command, str) or not command.strip():
        raise InputError("execute_bash.command must be a nonempty string")
    canonical, _ = taxonomy.label_bash(command)
    if canonical in {"read_file"}:
        return "read"
    if canonical in {"search_code", "find_files"}:
        return "search"
    if canonical == "apply_patch":
        return "edit"
    if canonical in {"run_tests", "run_linter", "run_build"}:
        return "run_tests"
    if canonical != "unmapped" and taxonomy.LABELS_V1[canonical]["group"] == "git":
        return "git"
    return "run_command"


def project_call(call: dict) -> str | None:
    if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
        raise InputError("tool call must contain a function object")
    fn = call["function"]
    name = fn.get("name")
    args = _json_value(fn.get("arguments", "{}"), "tool arguments")
    if not isinstance(args, dict):
        raise InputError("tool arguments must decode to an object")
    if name == "execute_bash":
        return project_bash(args.get("command"))
    if name == "str_replace_editor":
        command = args.get("command")
        if command == "view":
            return "read"
        if command in {"create", "str_replace", "insert", "undo_edit"}:
            return "edit"
        raise InputError(f"unknown str_replace_editor command: {command!r}")
    if name in {"think", "task_tracker", "finish"}:
        return None
    raise InputError(f"unknown OpenHands tool: {name!r}")


def split_for(instance_id: str, holdout_pct: int) -> str:
    if not isinstance(instance_id, str) or not instance_id:
        raise InputError("instance_id must be a nonempty string")
    bucket = int(hashlib.sha256(instance_id.encode()).hexdigest()[:8], 16) % 100
    return "holdout" if bucket < holdout_pct else "train"


def _clean(text: str, cap: int = 600) -> str:
    return " ".join(text.split())[:cap]


def _query(request: str, prior: list[str]) -> str:
    window = prior[-12:]
    return (f"[{FORMAT_VERSION}]\nISSUE: {_clean(request)}\n"
            f"RECENT ACTIONS (oldest->newest): {', '.join(window)}\nLAST: {window[-1]}")


def trajectory_rows(source: dict, schemas: list[dict], *, context=False, audit=None) -> list[dict]:
    if context:
        return _context_rows(source, audit if audit is not None else collections.Counter())
    trajectory = _json_value(source.get("trajectory"), "trajectory")
    if not isinstance(trajectory, list) or not trajectory:
        raise InputError("trajectory must be a nonempty list")
    request = next((m.get("content") for m in trajectory
                    if isinstance(m, dict) and m.get("role") == "user"
                    and isinstance(m.get("content"), str) and m["content"].strip()), None)
    if request is None:
        raise InputError("trajectory has no nonempty user request")
    prior: list[str] = []
    rows = []
    for message in trajectory:
        if not isinstance(message, dict):
            raise InputError("trajectory message must be an object")
        if message.get("role") != "assistant":
            continue
        calls = _json_value(message.get("tool_calls"), "tool_calls")
        if calls is None:
            continue
        if not isinstance(calls, list):
            raise InputError("tool_calls must be a list")
        for call in calls:
            label = project_call(call)
            if label is None:
                prior.clear()
                continue
            if prior:
                rows.append({
                    "query": _query(request, prior), "tools": schemas,
                    "answers": [{"name": label}],
                    "reasoning": f"LAST: {prior[-1]} -> {label}", "system": SYSTEM,
                })
            prior.append(label)
    return rows


def _context_rows(source, audit):
    """Opt-in q2: emit before the target call, after a matched prior response.

    No assistant prose/target arguments/outcome metadata enters the feature object.
    Parallel calls and missing responses reset the observed prefix rather than guessing order.
    """
    messages = _json_value(source.get("trajectory"), "trajectory")
    if not isinstance(messages, list) or not messages:
        raise InputError("trajectory must be a nonempty list")
    task, observation, prior, pending, rows = "", "", [], None, []
    seen_ids = set()
    for msg in messages:
        if not isinstance(msg, dict):
            raise InputError("trajectory message must be an object")
        role = msg.get("role")
        if role == "user":
            content = msg.get("content")
            if not isinstance(content, str) or not content.strip():
                raise InputError("user content must be nonempty text")
            task = _clean(content, 600)
            prior, observation, pending = [], "", None
        elif role == "tool":
            content = msg.get("content")
            if (pending is None or msg.get("tool_call_id") != pending[0]
                    or msg.get("name") not in (None, pending[2])
                    or not isinstance(content, str) or not content.strip()):
                audit["unmatched_or_empty_results"] += 1
                prior, observation, pending = [], "", None
                continue
            prior = (prior + [pending[1]])[-12:]
            observation = " ".join(content[-2000:].split())
            pending = None
        elif role == "assistant":
            calls = _json_value(msg.get("tool_calls"), "tool_calls")
            if calls is None or calls == []:
                continue
            if not isinstance(calls, list):
                raise InputError("tool_calls must be a list")
            if len(calls) != 1:
                audit["parallel_messages_skipped"] += 1
                prior, observation, pending = [], "", None
                continue
            if pending is not None:
                audit["missing_results"] += 1
                prior, observation, pending = [], "", None
            call = calls[0]
            try:
                label = project_call(call)
            except InputError:
                audit["unlabelable_calls_skipped"] += 1
                prior, observation, pending = [], "", None
                continue
            if label is None:
                audit["control_resets"] += 1
                prior, observation, pending = [], "", None
                continue
            audit["coding_calls"] += 1
            call_id = call.get("id")
            if not isinstance(call_id, str) or not call_id or call_id in seen_ids:
                audit["invalid_call_ids"] += 1
                prior, observation, pending = [], "", None
                continue
            seen_ids.add(call_id)
            if task and prior and observation:
                rows.append({"task": task, "observation": observation,
                             "history": list(prior), "target": label})
                audit["eligible_rows"] += 1
            pending = call_id, label, call["function"]["name"]
    return rows


def _iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise InputError(f"{path}:{lineno}: invalid JSON") from exc
            if not isinstance(row, dict):
                raise InputError(f"{path}:{lineno}: row must be an object")
            yield row


def _remote_rows(offset: int = 0) -> Iterable[dict]:
    api = f"https://huggingface.co/api/datasets/{DATASET}"
    try:
        with urllib.request.urlopen(api, timeout=30) as response:
            current = json.load(response).get("sha")
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot verify dataset revision: {exc}") from exc
    if current != REVISION:
        raise InputError(f"dataset revision changed: expected {REVISION}, got {current}")
    total = None
    while total is None or offset < total:
        query = urllib.parse.urlencode({
            "dataset": DATASET, "config": "default", "split": "train",
            "offset": offset, "length": 100,
        })
        try:
            with urllib.request.urlopen(
                    "https://datasets-server.huggingface.co/rows?" + query,
                    timeout=60) as response:
                page = json.load(response)
        except (OSError, ValueError) as exc:
            raise InputError(f"cannot fetch dataset rows at offset {offset}: {exc}") from exc
        total = page.get("num_rows_total")
        material = page.get("rows")
        if not isinstance(total, int) or not isinstance(material, list):
            raise InputError("datasets-server returned an invalid page")
        if not material:
            raise InputError(f"datasets-server returned an empty page before row {total}")
        for wrapped in material:
            if not isinstance(wrapped, dict) or not isinstance(wrapped.get("row"), dict):
                raise InputError("datasets-server row wrapper is invalid")
            if wrapped.get("truncated_cells"):
                raise InputError("datasets-server truncated a source row")
            yield wrapped["row"]
        offset += len(material)


def source_rows(input_jsonl: Path | None, offset: int = 0) -> Iterable[dict]:
    if input_jsonl:
        return _iter_jsonl(input_jsonl)
    return _remote_rows(offset)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare(rows: Iterable[dict], outdir: Path, max_train: int, max_holdout: int,
            holdout_pct: int, resolved_only: bool, max_trajectories: int | None = None,
            source_info: dict | None = None) -> dict:
    if outdir.exists():
        raise InputError(f"output directory already exists: {outdir}")
    if not 1 <= holdout_pct <= 99 or max_train < 1 or max_holdout < 1:
        raise InputError("caps must be positive and holdout-pct must be 1..99")
    schema_doc = json.loads((Path(__file__).with_name("labels.json")).read_text())
    if tuple(sorted(schema_doc["labels"])) != LABELS:
        raise InputError("labels.json disagrees with the mapper")
    if max_trajectories is not None and max_trajectories < 1:
        raise InputError("max-trajectories must be positive")
    outdir.parent.mkdir(parents=True, exist_ok=True)
    staging = outdir.with_name(outdir.name + ".tmp")
    if staging.exists():
        raise InputError(f"staging directory already exists: {staging}")
    staging.mkdir()
    paths = {s: staging / f"pilot-{s}.jsonl" for s in ("train", "holdout")}
    handles = {s: path.open("w", encoding="utf-8") for s, path in paths.items()}
    counts = collections.Counter()
    labels = {s: collections.Counter() for s in paths}
    instances = {s: set() for s in paths}
    try:
        for source in rows:
            counts["trajectories_seen"] += 1
            if (max_trajectories is not None
                    and counts["trajectories_seen"] > max_trajectories):
                counts["trajectories_seen"] -= 1
                break
            if resolved_only and source.get("resolved") != 1:
                counts["unresolved_skipped"] += 1
                continue
            split = split_for(source.get("instance_id"), holdout_pct)
            cap = max_train if split == "train" else max_holdout
            if counts[f"rows_{split}"] >= cap:
                if counts["rows_train"] >= max_train and counts["rows_holdout"] >= max_holdout:
                    break
                continue
            made = trajectory_rows(source, schema_doc["schemas"])
            room = cap - counts[f"rows_{split}"]
            for row in made[:room]:
                handles[split].write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                labels[split][row["answers"][0]["name"]] += 1
                counts[f"rows_{split}"] += 1
            if made[:room]:
                instances[split].add(source["instance_id"])
        if counts["rows_train"] == 0 or counts["rows_holdout"] == 0:
            raise InputError("both splits must contain at least one example")
        if instances["train"] & instances["holdout"]:
            raise InputError("instance leakage between train and holdout")
    except BaseException:
        for fh in handles.values():
            fh.close()
        shutil.rmtree(staging)
        raise
    else:
        for fh in handles.values():
            fh.close()
    receipt = {
        "format_version": FORMAT_VERSION,
        "source": source_info or {"mode": "provided_iterable"},
        "selection": {
            "resolved_only": resolved_only,
            "max_trajectories": max_trajectories,
            "max_train": max_train,
            "max_holdout": max_holdout,
            "holdout_pct": holdout_pct,
        },
        "split": f"sha256(instance_id) bucket; {holdout_pct}% holdout; split before caps",
        "counts": dict(counts),
        "instances": {s: len(v) for s, v in instances.items()},
        "labels": {s: dict(sorted(v.items())) for s, v in labels.items()},
        "outputs": {s: {"path": path.name, "sha256": digest(path)} for s, path in paths.items()},
    }
    (staging / "provenance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    os.replace(staging, outdir)
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, help="offline fixture/export instead of HF streaming")
    ap.add_argument("--outdir", type=Path, default=Path("data/coding-core/pilot"))
    ap.add_argument("--max-train", type=int, default=2000)
    ap.add_argument("--max-holdout", type=int, default=300)
    ap.add_argument("--max-trajectories", type=int, default=100,
                    help="maximum source trajectories to scan (default: 100)")
    ap.add_argument("--holdout-pct", type=int, default=20)
    ap.add_argument("--offset", type=int, default=0,
                    help="starting datasets-server row (split still uses instance identity)")
    ap.add_argument("--include-unresolved", action="store_true")
    args = ap.parse_args()
    try:
        if args.input_jsonl:
            source_info = {"mode": "offline_jsonl", "input_sha256": digest(args.input_jsonl)}
        else:
            source_info = {
                "mode": "huggingface_rows_api", "dataset": DATASET,
                "dataset_revision": REVISION, "offset": args.offset,
            }
        result = prepare(source_rows(args.input_jsonl, args.offset), args.outdir, args.max_train,
                         args.max_holdout, args.holdout_pct, not args.include_unresolved,
                         args.max_trajectories, source_info)
    except (InputError, OSError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
