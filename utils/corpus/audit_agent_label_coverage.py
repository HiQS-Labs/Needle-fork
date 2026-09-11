#!/usr/bin/env python3
"""Audit normalized-agent compatibility with the frozen action taxonomy.

Only aggregate counts, field names, and hashes are emitted. Prompt text, argument
values, paths, native identities, and event identities stay in memory.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
from pathlib import Path

CORPUS = Path(__file__).resolve().parent
sys.path.insert(0, str(CORPUS))

import agy_transcript_adapter as agy  # noqa: E402
import codex_transcript_adapter as codex  # noqa: E402
import taxonomy as tx  # noqa: E402
import zcode_transcript_adapter as zcode  # noqa: E402
from normalized_transcript import (  # noqa: E402
    AdapterError, EVENT_FORMAT_VERSION, TOOL_ALIAS_VERSION, digest,
    require_source_root,
)


AUDIT_FORMAT_VERSION = "agent-label-coverage-v1"
MAX_INPUT_SHAPES = 25


class AuditError(ValueError):
    """The requested audit cannot produce a complete, trustworthy result."""


def safe_reason(exc: Exception) -> str:
    message = str(exc)
    if "invalid JSON" in message:
        return "invalid_json"
    if "conflicting Agy step_index" in message:
        return "conflicting_step_identity"
    if "session identity" in message:
        return "missing_or_conflicting_session_identity"
    return "other_adapter_error"


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_independent(source: str, root: Path, namespace: str):
    if source == "codex":
        require_source_root(root)
        paths = []
        def fail_walk(exc: OSError) -> None:
            raise AdapterError(f"cannot walk Codex source: {exc}") from exc
        for base, dirs, files in os.walk(root, onerror=fail_walk):
            dirs.sort()
            paths.extend(Path(base) / name for name in sorted(files)
                         if name.endswith(".jsonl"))
        for path in paths:
            try:
                yield codex.read_transcript(path, root, namespace), None, None
            except AdapterError as exc:
                yield None, safe_reason(exc), file_digest(path)
        return
    if source in {"agy_desktop", "agy_cli"}:
        for path in agy.iter_transcript_paths(root):
            try:
                yield agy.read_transcript(path, root, namespace), None, None
            except AdapterError as exc:
                yield None, safe_reason(exc), file_digest(Path(path))
        return
    if source == "zcode":
        try:
            # Materialize before yielding so a malformed later session cannot
            # leave a plausible-looking partial source receipt.
            transcripts = list(zcode.iter_transcripts(root, namespace))
        except AdapterError as exc:
            raise AuditError(f"zcode source rejected: {safe_reason(exc)}") from exc
        for transcript in transcripts:
            yield transcript, None, None
        return
    raise ValueError(source)


def audit(source: str, root: Path, namespace: str) -> dict:
    labels = collections.Counter()
    source_tools = collections.Counter()
    canonical_tools = collections.Counter()
    input_shapes = collections.Counter()
    rejections = collections.Counter()
    accepted = actions = aliased = eligible_pairs = 0
    inventory = []
    seen_sessions = set()
    rejected_material = []
    for transcript, rejection, rejection_digest in read_independent(
            source, root, namespace):
        if rejection:
            rejections[rejection] += 1
            rejected_material.append((rejection, rejection_digest))
            continue
        accepted += 1
        meta, steps = transcript
        if meta.session_id in seen_sessions:
            raise AuditError(f"{source}: duplicate normalized session identity")
        seen_sessions.add(meta.session_id)
        inventory.append((meta.session_id, meta.transcript_sha256))
        prior_actions = 0
        for step in steps:
            if step.kind != "action":
                continue
            actions += 1
            if prior_actions:
                eligible_pairs += 1
            prior_actions += 1
            source_tools[step.source_tool] += 1
            canonical = step.canonical_tool
            canonical_tools[canonical or "<unaliased>"] += 1
            input_shapes[(step.source_tool, tuple(sorted(step.tool_input or {})))] += 1
            if canonical is None:
                labels["unmapped"] += 1
                continue
            aliased += 1
            label, _evidence = tx.label_call(canonical, step.tool_input)
            labels[label] += 1
    if actions == 0:
        raise AuditError(f"{source}: audit produced zero actions")
    mapped = actions - labels["unmapped"]
    ranked_shapes = input_shapes.most_common()
    retained_shapes = ranked_shapes[:MAX_INPUT_SHAPES]
    omitted_shapes = ranked_shapes[MAX_INPUT_SHAPES:]
    result = {
        "audit_format_version": AUDIT_FORMAT_VERSION,
        "event_format_version": EVENT_FORMAT_VERSION,
        "tool_alias_version": TOOL_ALIAS_VERSION,
        "label_set_version": tx.LABEL_SET_VERSION,
        "source": source,
        "source_namespace": namespace,
        "inventory_digest": digest([
            AUDIT_FORMAT_VERSION, source, namespace, sorted(inventory),
            sorted(rejected_material),
        ]),
        "sessions_accepted": accepted,
        "sessions_rejected": sum(rejections.values()),
        "rejections": dict(sorted(rejections.items())),
        "actions": actions,
        "eligible_pairs": eligible_pairs,
        "aliased_actions": aliased,
        "alias_coverage": round(aliased / actions, 6),
        "mapped_actions": mapped,
        "mapping_coverage": round(mapped / actions, 6),
        "distinct_mapped_labels": len([name for name in labels if name != "unmapped"]),
        "labels": dict(labels.most_common()),
        "source_tools": dict(source_tools.most_common()),
        "canonical_tools": dict(canonical_tools.most_common()),
        "input_shapes_total": len(ranked_shapes),
        "input_shapes_omitted": len(omitted_shapes),
        "input_shapes_omitted_actions": sum(
            count for _shape, count in omitted_shapes),
        "input_shapes": [
            {"source_tool": tool, "keys": list(keys), "count": count}
            for (tool, keys), count in retained_shapes
        ],
    }
    validate_result(result)
    return result


def validate_result(result: dict) -> None:
    actions = result["actions"]
    if actions <= 0:
        raise AuditError("audit result has no actions")
    label_total = sum(result["labels"].values())
    if label_total != actions:
        raise AuditError(
            f"label conservation failed: {label_total} labels for {actions} actions")
    if result["mapped_actions"] + result["labels"].get("unmapped", 0) != actions:
        raise AuditError("mapped/unmapped conservation failed")
    if not 0 <= result["aliased_actions"] <= actions:
        raise AuditError("aliased action count is outside action count")
    if not 0 <= result["eligible_pairs"] <= actions:
        raise AuditError("eligible pair count is outside action count")
    if sum(result["source_tools"].values()) != actions:
        raise AuditError("source-tool conservation failed")
    if sum(result["canonical_tools"].values()) != actions:
        raise AuditError("canonical-tool conservation failed")
    represented_shapes = (
        sum(shape["count"] for shape in result["input_shapes"])
        + result["input_shapes_omitted_actions"]
    )
    if represented_shapes != actions:
        raise AuditError("input-shape conservation failed")
    if len(result["input_shapes"]) + result["input_shapes_omitted"] != result[
            "input_shapes_total"]:
        raise AuditError("input-shape cardinality failed")


def encode_result(result: dict) -> str:
    validate_result(result)
    return json.dumps(result, indent=2, sort_keys=True) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True,
                    choices=["codex", "agy_desktop", "agy_cli", "zcode"])
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--namespace", required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    try:
        result = audit(args.source, args.root, args.namespace)
    except (AdapterError, AuditError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    encoded = encode_result(result)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.out.with_name(args.out.name + ".tmp")
        tmp.write_text(encoded)
        os.replace(tmp, args.out)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
