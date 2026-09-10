"""Shared contract for deterministic, source-specific agent transcript adapters.

The adapters preserve private prompt and tool-input data in memory. Callers that
serialize these objects must write below the repository's ignored ``data/`` tree.
Nothing in this module adds non-Claude sessions to the frozen Oracle evaluation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional


EVENT_FORMAT_VERSION = "normalized-agent-transcript-v1"
TOOL_ALIAS_VERSION = "agent-tool-alias-v1"
_NAMESPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class AdapterError(ValueError):
    """A source cannot be normalized without guessing or losing identity."""


@dataclass(frozen=True)
class NormalizedTranscript:
    event_format_version: str
    tool_alias_version: str
    source_agent: str
    source_namespace: str
    source_relpaths: tuple[str, ...]
    session_id: str
    transcript_sha256: str
    native_session_id: str


@dataclass(frozen=True)
class NormalizedStep:
    kind: str
    text: str = ""
    source_tool: str = ""
    canonical_tool: Optional[str] = None
    tool_input: Optional[dict[str, Any]] = None
    action_ordinal: Optional[int] = None
    source_event_id: Optional[str] = None
    native_event_id: Optional[str] = None
    timestamp: Optional[str] = None


_TOOL_ALIASES = {
    "codex": {
        "exec_command": "Bash",
        "apply_patch": "Edit",
        "update_plan": "TodoWrite",
        "web_search": "WebSearch",
    },
    "agy": {
        "run_command": "Bash",
        "view_file": "Read",
        "grep_search": "Grep",
        "find_by_name": "Glob",
        "list_dir": "Glob",
        "replace_file_content": "Edit",
        "multi_replace_file_content": "Edit",
        "write_to_file": "Write",
        "manage_task": "TodoWrite",
        "search_web": "WebSearch",
        "read_url_content": "WebFetch",
    },
    "zcode": {
        "Bash": "Bash",
        "Read": "Read",
        "Edit": "Edit",
        "Write": "Write",
        "TodoWrite": "TodoWrite",
        "TaskOutput": "TaskOutput",
        "TaskStop": "TaskStop",
        "RespondToCoordinator": "SendMessage",
    },
}


def validate_namespace(value: str) -> str:
    if not isinstance(value, str) or not _NAMESPACE_RE.fullmatch(value):
        raise AdapterError(
            "source namespace must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    return value


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value, allow_nan=False, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise AdapterError(f"value is not canonical JSON: {exc}") from exc


def digest(parts: Any) -> str:
    return hashlib.sha256(canonical_json(parts).encode()).hexdigest()


def relative_path(path: os.PathLike[str] | str,
                  source_root: os.PathLike[str] | str) -> str:
    root = os.path.realpath(source_root)
    resolved = os.path.realpath(path)
    try:
        inside = os.path.commonpath([root, resolved]) == root
    except ValueError:
        inside = False
    if not inside or resolved == root:
        raise AdapterError(f"transcript is outside source root: {path}")
    return os.path.relpath(resolved, root).replace(os.sep, "/")


def require_source_root(source_root: os.PathLike[str] | str) -> str:
    root = os.path.realpath(source_root)
    if not os.path.isdir(root):
        raise AdapterError(f"source root is not a readable directory: {source_root}")
    try:
        with os.scandir(root):
            pass
    except OSError as exc:
        raise AdapterError(f"cannot read source root {source_root}: {exc}") from exc
    return root


def load_jsonl(path: os.PathLike[str] | str) -> list[dict[str, Any]]:
    records = []
    try:
        fh = open(path, encoding="utf-8", errors="strict")
    except OSError as exc:
        raise AdapterError(f"cannot read {path}: {exc}") from exc
    with fh:
        try:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise AdapterError(
                        f"{path}:{lineno}: invalid JSON: {exc.msg}") from exc
                if not isinstance(record, dict):
                    raise AdapterError(f"{path}:{lineno}: row must be an object")
                records.append(record)
        except UnicodeDecodeError as exc:
            raise AdapterError(f"{path}: invalid UTF-8: {exc}") from exc
    if not records:
        raise AdapterError(f"{path}: no records")
    return records


def make_meta(source_agent: str, source_namespace: str,
              native_session_id: str, source_relpaths: Iterable[str],
              records: Iterable[dict[str, Any]]) -> NormalizedTranscript:
    namespace = validate_namespace(source_namespace)
    if source_agent not in _TOOL_ALIASES:
        raise AdapterError(f"unsupported source agent: {source_agent!r}")
    if not isinstance(native_session_id, str) or not native_session_id:
        raise AdapterError("native session identity is missing")
    relpaths = tuple(sorted(set(source_relpaths)))
    if not relpaths or any(not isinstance(path, str) or not path for path in relpaths):
        raise AdapterError("source transcript paths are missing")
    material = list(records)
    if not material:
        raise AdapterError("source transcript has no selected records")
    return NormalizedTranscript(
        event_format_version=EVENT_FORMAT_VERSION,
        tool_alias_version=TOOL_ALIAS_VERSION,
        source_agent=source_agent,
        source_namespace=namespace,
        source_relpaths=relpaths,
        session_id=digest([
            EVENT_FORMAT_VERSION, "session", source_agent, namespace,
            native_session_id,
        ]),
        transcript_sha256=digest([
            EVENT_FORMAT_VERSION, "transcript", source_agent, material,
        ]),
        native_session_id=native_session_id,
    )


def canonical_tool(source_agent: str, source_tool: str) -> Optional[str]:
    return _TOOL_ALIASES[source_agent].get(source_tool)


def event_id(meta: NormalizedTranscript, native_event_id: str) -> str:
    if not isinstance(native_event_id, str) or not native_event_id:
        raise AdapterError("native action identity is missing")
    return digest([
        EVENT_FORMAT_VERSION, "event", meta.source_agent,
        meta.source_namespace, meta.native_session_id, native_event_id,
    ])


def validate_transcript(meta: NormalizedTranscript,
                        steps: list[NormalizedStep]
                        ) -> tuple[NormalizedTranscript, list[NormalizedStep]]:
    action_ordinals = []
    event_ids = set()
    native_ids = set()
    for step in steps:
        if step.kind not in {"user", "action"}:
            raise AdapterError(f"unsupported normalized step kind: {step.kind!r}")
        if step.kind == "user":
            if not isinstance(step.text, str) or not step.text.strip():
                raise AdapterError("normalized user step is empty")
            continue
        if not step.source_tool:
            raise AdapterError("normalized action has no source tool")
        if not isinstance(step.tool_input, dict):
            raise AdapterError("normalized action input must be an object")
        if step.source_event_id in event_ids:
            raise AdapterError(
                f"duplicate source event identity: {step.source_event_id}")
        if step.native_event_id in native_ids:
            raise AdapterError(
                f"duplicate native action identity: {step.native_event_id}")
        event_ids.add(step.source_event_id)
        native_ids.add(step.native_event_id)
        action_ordinals.append(step.action_ordinal)
    if action_ordinals != list(range(len(action_ordinals))):
        raise AdapterError("action ordinals are not contiguous in source order")
    return meta, steps
