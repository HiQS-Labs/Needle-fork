"""Normalize Codex CLI session JSONL into the shared transcript contract."""
from __future__ import annotations

import json
import os
from typing import Any, Iterator

from normalized_transcript import (
    AdapterError, NormalizedStep, NormalizedTranscript, canonical_tool,
    event_id, load_jsonl, make_meta, relative_path, require_source_root,
    validate_transcript,
)


_CALL_TYPES = {
    "function_call",
    "custom_tool_call",
    "tool_search_call",
    "web_search_call",
}


def _input_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {"raw_input": value}
        if isinstance(decoded, dict):
            return decoded
        return {"raw_input": value}
    if value is None:
        return {}
    raise AdapterError(f"Codex tool input has unsupported type {type(value).__name__}")


def _user_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        value = block.get("text")
        if isinstance(value, str) and value.strip():
            parts.append(value)
    return "\n".join(parts)


def read_transcript(path: os.PathLike[str] | str,
                    source_root: os.PathLike[str] | str,
                    source_namespace: str
                    ) -> tuple[NormalizedTranscript, list[NormalizedStep]]:
    records = load_jsonl(path)
    relpath = relative_path(path, source_root)
    native_sessions = set()
    for record in records:
        if record.get("type") != "session_meta":
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        value = payload.get("id") or payload.get("session_id")
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            raise AdapterError(f"{path}: Codex session identity must be a string")
        native_sessions.add(value)
    if len(native_sessions) != 1:
        raise AdapterError(
            f"{path}: expected one Codex session identity, found {len(native_sessions)}")
    native_session_id = next(iter(native_sessions))
    meta = make_meta("codex", source_namespace, native_session_id, [relpath], records)

    steps = []
    action_ordinal = 0
    for record_index, record in enumerate(records):
        if record.get("type") != "response_item":
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            raise AdapterError(f"{path}: response_item payload must be an object")
        item_type = payload.get("type")
        if item_type == "message" and payload.get("role") == "user":
            text = _user_text(payload.get("content"))
            if text.strip():
                steps.append(NormalizedStep(
                    kind="user", text=text,
                    timestamp=record.get("timestamp") if isinstance(
                        record.get("timestamp"), str) else None,
                ))
            continue
        if item_type not in _CALL_TYPES:
            continue
        native_call_id = payload.get("call_id") or payload.get("id")
        native_event_id = (
            f"call:{native_call_id}"
            if isinstance(native_call_id, str) and native_call_id
            else f"record:{record_index}"
        )
        if item_type == "web_search_call":
            source_tool = "web_search"
            tool_input = _input_object(payload.get("action"))
        elif item_type == "tool_search_call":
            source_tool = "tool_search"
            tool_input = _input_object(payload.get("arguments"))
        else:
            source_tool = payload.get("name")
            if not isinstance(source_tool, str) or not source_tool:
                raise AdapterError(f"{path}: Codex {item_type} has no tool name")
            raw_input = payload.get("input") if item_type == "custom_tool_call" else payload.get("arguments")
            tool_input = _input_object(raw_input)
        steps.append(NormalizedStep(
            kind="action",
            source_tool=source_tool,
            canonical_tool=canonical_tool("codex", source_tool),
            tool_input=tool_input,
            action_ordinal=action_ordinal,
            source_event_id=event_id(meta, native_event_id),
            native_event_id=native_event_id,
            timestamp=record.get("timestamp") if isinstance(
                record.get("timestamp"), str) else None,
        ))
        action_ordinal += 1
    return validate_transcript(meta, steps)


def iter_transcripts(source_root: os.PathLike[str] | str,
                     source_namespace: str
                     ) -> Iterator[tuple[NormalizedTranscript, list[NormalizedStep]]]:
    root = require_source_root(source_root)
    seen_sessions = set()
    def fail_walk(exc: OSError) -> None:
        raise AdapterError(f"cannot walk Codex source {root}: {exc}") from exc

    for base, dirs, files in os.walk(root, onerror=fail_walk):
        dirs.sort()
        for name in sorted(files):
            if name.endswith(".jsonl"):
                transcript = read_transcript(
                    os.path.join(base, name), root, source_namespace)
                if transcript[0].session_id in seen_sessions:
                    raise AdapterError(
                        f"duplicate Codex session identity: {transcript[0].session_id}")
                seen_sessions.add(transcript[0].session_id)
                yield transcript
