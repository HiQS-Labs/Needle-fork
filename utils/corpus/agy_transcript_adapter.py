"""Normalize canonical Agy/Antigravity transcripts into the shared contract."""
from __future__ import annotations

import os
from typing import Iterator

from normalized_transcript import (
    AdapterError, NormalizedStep, NormalizedTranscript, canonical_tool,
    canonical_json, event_id, load_jsonl, make_meta, relative_path,
    validate_transcript,
)


_CANONICAL_SUFFIX = (".system_generated", "logs", "transcript.jsonl")


def iter_transcript_paths(source_root: os.PathLike[str] | str) -> Iterator[str]:
    root = os.path.realpath(source_root)
    try:
        entries = sorted(os.scandir(root), key=lambda entry: entry.name)
    except OSError as exc:
        raise AdapterError(f"cannot list Agy source {source_root}: {exc}") from exc
    for entry in entries:
        if not entry.is_dir(follow_symlinks=False):
            continue
        path = os.path.join(entry.path, *_CANONICAL_SUFFIX)
        if os.path.isfile(path):
            yield path


def read_transcript(path: os.PathLike[str] | str,
                    source_root: os.PathLike[str] | str,
                    source_namespace: str
                    ) -> tuple[NormalizedTranscript, list[NormalizedStep]]:
    relpath = relative_path(path, source_root)
    parts = tuple(relpath.split("/"))
    if len(parts) != 4 or tuple(parts[1:]) != _CANONICAL_SUFFIX:
        raise AdapterError(f"{path}: not a canonical Agy transcript")
    native_session_id = parts[0]
    raw_records = load_jsonl(path)
    records = []
    seen_steps = {}
    for record in raw_records:
        index = record.get("step_index")
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise AdapterError(f"{path}: invalid Agy step_index {index!r}")
        encoded = canonical_json(record)
        if index in seen_steps:
            if seen_steps[index] == encoded:
                continue
            raise AdapterError(f"{path}: conflicting Agy step_index {index}")
        seen_steps[index] = encoded
        records.append(record)

    meta = make_meta(
        "agy", source_namespace, native_session_id, [relpath], records)
    steps = []
    action_ordinal = 0
    for record in records:
        timestamp = record.get("created_at") if isinstance(
            record.get("created_at"), str) else None
        if record.get("type") == "USER_INPUT":
            text = record.get("content")
            if not isinstance(text, str):
                raise AdapterError(f"{path}: Agy USER_INPUT content must be a string")
            if text.strip():
                steps.append(NormalizedStep(
                    kind="user", text=text, timestamp=timestamp))
        calls = record.get("tool_calls")
        if calls is None:
            continue
        if not isinstance(calls, list):
            raise AdapterError(f"{path}: Agy tool_calls must be a list")
        for position, call in enumerate(calls):
            if not isinstance(call, dict):
                raise AdapterError(f"{path}: Agy tool call must be an object")
            source_tool = call.get("name")
            tool_input = call.get("args")
            if not isinstance(source_tool, str) or not source_tool:
                raise AdapterError(f"{path}: Agy tool call has no name")
            if not isinstance(tool_input, dict):
                raise AdapterError(f"{path}: Agy tool args must be an object")
            native_event_id = f"{record['step_index']}:{position}"
            steps.append(NormalizedStep(
                kind="action",
                source_tool=source_tool,
                canonical_tool=canonical_tool("agy", source_tool),
                tool_input=tool_input,
                action_ordinal=action_ordinal,
                source_event_id=event_id(meta, native_event_id),
                native_event_id=native_event_id,
                timestamp=timestamp,
            ))
            action_ordinal += 1
    return validate_transcript(meta, steps)


def iter_transcripts(source_root: os.PathLike[str] | str,
                     source_namespace: str
                     ) -> Iterator[tuple[NormalizedTranscript, list[NormalizedStep]]]:
    for path in iter_transcript_paths(source_root):
        yield read_transcript(path, source_root, source_namespace)
