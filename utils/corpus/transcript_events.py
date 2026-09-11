"""Shared Claude transcript reader with opt-in, mount-invariant identities.

Legacy corpus callers may continue to use path-based identities. New experiments
pass an explicit source namespace and root so a copied transcript has the same
session/event IDs without leaking an absolute path into the identity material.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Iterator, Optional


IDENTITY_FORMAT_VERSION = "transcript-event-v1"
_NAMESPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@dataclass(frozen=True)
class TranscriptMeta:
    source_namespace: str
    source_relpath: str
    session_id: str
    transcript_sha256: str
    transcript_session_id: Optional[str]


@dataclass(frozen=True)
class TranscriptStep:
    kind: str
    text: str = ""
    tool: str = ""
    tool_input: Optional[dict[str, Any]] = None
    action_ordinal: Optional[int] = None
    source_event_id: Optional[str] = None
    tool_use_id: Optional[str] = None
    record_uuid: Optional[str] = None


def validate_namespace(value: str) -> str:
    if not isinstance(value, str) or not _NAMESPACE_RE.fullmatch(value):
        raise ValueError(
            "source namespace must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    return value


def _digest(parts: list[Any]) -> str:
    material = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(material.encode()).hexdigest()


def _relative_path(path: str, source_root: str) -> str:
    root = os.path.realpath(source_root)
    resolved = os.path.realpath(path)
    try:
        inside = os.path.commonpath([root, resolved]) == root
    except ValueError:
        inside = False
    if not inside or resolved == root:
        raise ValueError(f"transcript is outside source root: {path}")
    return os.path.relpath(resolved, root).replace(os.sep, "/")


def read_transcript(path: str, source_root: str, source_namespace: str
                    ) -> tuple[TranscriptMeta, list[TranscriptStep]]:
    """Read one transcript and derive stable identities for every tool action."""
    namespace = validate_namespace(source_namespace)
    relpath = _relative_path(path, source_root)
    with open(path, "rb") as fh:
        raw = fh.read()
    transcript_sha256 = hashlib.sha256(raw).hexdigest()

    records = []
    transcript_session_ids = set()
    for raw_line in raw.splitlines():
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line.decode(errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        records.append(record)
        session_id = record.get("sessionId")
        if isinstance(session_id, str) and session_id:
            transcript_session_ids.add(session_id)
    if len(transcript_session_ids) > 1:
        raise ValueError(
            f"transcript contains multiple sessionId values: {relpath}")
    transcript_session_id = next(iter(transcript_session_ids), None)
    # Claude subagent transcripts reuse the parent's sessionId, so the stable
    # source-relative path is part of the session identity as well. The mount
    # prefix is deliberately absent.
    session_key = [transcript_session_id or "missing-sessionId", relpath]
    session_id = _digest([IDENTITY_FORMAT_VERSION, "session", namespace, session_key])
    meta = TranscriptMeta(
        source_namespace=namespace,
        source_relpath=relpath,
        session_id=session_id,
        transcript_sha256=transcript_sha256,
        transcript_session_id=transcript_session_id,
    )

    steps = []
    action_ordinal = 0
    for record in records:
        message = record.get("message") or {}
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            if message.get("role") == "user" and content.strip():
                steps.append(TranscriptStep(kind="user", text=content))
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and message.get("role") == "user":
                text = block.get("text", "")
                if isinstance(text, str) and text.strip():
                    steps.append(TranscriptStep(kind="user", text=text))
                continue
            if block.get("type") != "tool_use" or not block.get("name"):
                continue
            tool_use_id = block.get("id")
            record_uuid = record.get("uuid")
            event_key = (tool_use_id if isinstance(tool_use_id, str) and tool_use_id
                         else record_uuid if isinstance(record_uuid, str) and record_uuid
                         else "missing-native-id")
            # Native tool-use IDs survive a mount/copy and expose an exact duplicate
            # transcript even when it appears at a second relative path. Fall back to
            # the namespaced session identity when no native record identity exists.
            has_native_id = ((isinstance(tool_use_id, str) and bool(tool_use_id)) or
                             (isinstance(record_uuid, str) and bool(record_uuid)))
            event_scope = ((transcript_session_id or session_id)
                           if has_native_id else session_id)
            source_event_id = _digest([
                IDENTITY_FORMAT_VERSION, "event", namespace, event_scope,
                event_key, action_ordinal,
            ])
            steps.append(TranscriptStep(
                kind="action",
                tool=str(block["name"]),
                tool_input=block.get("input") if isinstance(block.get("input"), dict) else {},
                action_ordinal=action_ordinal,
                source_event_id=source_event_id,
                tool_use_id=tool_use_id if isinstance(tool_use_id, str) else None,
                record_uuid=record_uuid if isinstance(record_uuid, str) else None,
            ))
            action_ordinal += 1
    return meta, steps


def iter_transcript_paths(source_root: str) -> Iterator[str]:
    for base, dirs, files in os.walk(source_root):
        dirs.sort()
        for name in sorted(files):
            if name.endswith(".jsonl"):
                yield os.path.join(base, name)
