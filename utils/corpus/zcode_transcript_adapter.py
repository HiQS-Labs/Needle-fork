"""Normalize ZCode CLI logs into one transcript per native session."""
from __future__ import annotations

import collections
import os
from typing import Any, Iterator

from normalized_transcript import (
    AdapterError, NormalizedStep, NormalizedTranscript, canonical_tool,
    event_id, load_jsonl, make_meta, relative_path, require_source_root,
    validate_namespace, validate_transcript,
)


_SELECTED_TYPES = {"turn_started", "tool_call_scheduled"}


def _sort_key(item: tuple[dict[str, Any], str, int]) -> tuple[str, int, str]:
    record, _relpath, _lineno = item
    timestamp = record.get("timestamp")
    sequence = record.get("sequenceNumber")
    native_id = record.get("id")
    if not isinstance(timestamp, str) or not timestamp:
        raise AdapterError("selected ZCode event has no timestamp")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise AdapterError("selected ZCode event has invalid sequenceNumber")
    if not isinstance(native_id, str) or not native_id:
        raise AdapterError("selected ZCode event has no native record identity")
    return timestamp, sequence, native_id


def iter_transcripts(source_root: os.PathLike[str] | str,
                     source_namespace: str
                     ) -> Iterator[tuple[NormalizedTranscript, list[NormalizedStep]]]:
    validate_namespace(source_namespace)
    root = require_source_root(source_root)
    grouped = collections.defaultdict(list)
    def fail_walk(exc: OSError) -> None:
        raise AdapterError(f"cannot walk ZCode source {root}: {exc}") from exc

    for base, dirs, files in os.walk(root, onerror=fail_walk):
        dirs.sort()
        for name in sorted(files):
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(base, name)
            relpath = relative_path(path, root)
            for lineno, record in enumerate(load_jsonl(path), 1):
                if record.get("type") not in _SELECTED_TYPES:
                    continue
                native_session_id = record.get("sessionId")
                if not isinstance(native_session_id, str) or not native_session_id:
                    raise AdapterError(
                        f"{path}:{lineno}: selected ZCode event has no sessionId")
                grouped[native_session_id].append((record, relpath, lineno))

    for native_session_id in sorted(grouped):
        selected = sorted(grouped[native_session_id], key=_sort_key)
        records = [record for record, _, _ in selected]
        relpaths = [relpath for _, relpath, _ in selected]
        meta = make_meta(
            "zcode", source_namespace, native_session_id, relpaths, records)
        steps = []
        action_ordinal = 0
        for record, relpath, lineno in selected:
            payload = record.get("payload")
            if not isinstance(payload, dict):
                raise AdapterError(
                    f"{relpath}:{lineno}: selected ZCode payload must be an object")
            timestamp = record["timestamp"]
            if record["type"] == "turn_started":
                text = payload.get("input")
                if not isinstance(text, str):
                    raise AdapterError(
                        f"{relpath}:{lineno}: ZCode turn input must be a string")
                if text.strip():
                    steps.append(NormalizedStep(
                        kind="user", text=text, timestamp=timestamp))
                continue
            native_event_id = payload.get("toolCallId")
            source_tool = payload.get("toolName")
            tool_input = payload.get("input")
            if not isinstance(native_event_id, str) or not native_event_id:
                raise AdapterError(
                    f"{relpath}:{lineno}: ZCode tool call has no toolCallId")
            if not isinstance(source_tool, str) or not source_tool:
                raise AdapterError(
                    f"{relpath}:{lineno}: ZCode tool call has no toolName")
            if not isinstance(tool_input, dict):
                raise AdapterError(
                    f"{relpath}:{lineno}: ZCode tool input must be an object")
            steps.append(NormalizedStep(
                kind="action",
                source_tool=source_tool,
                canonical_tool=canonical_tool("zcode", source_tool),
                tool_input=tool_input,
                action_ordinal=action_ordinal,
                source_event_id=event_id(meta, native_event_id),
                native_event_id=native_event_id,
                timestamp=timestamp,
            ))
            action_ordinal += 1
        yield validate_transcript(meta, steps)
