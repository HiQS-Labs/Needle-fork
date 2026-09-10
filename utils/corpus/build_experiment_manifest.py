#!/usr/bin/env python3
"""Freeze two private pair sets and prove their source identity and separation.

The private manifest contains only identities and hashes, but it still lives under
``data/``. An optional public receipt contains aggregate counts and hashes only.
Raw prompts, rendered rows, commands, source paths, and row-level labels never enter
the receipt.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serialize as ser  # noqa: E402
import taxonomy as tx  # noqa: E402
from transcript_events import (IDENTITY_FORMAT_VERSION, read_transcript,
                               validate_namespace)  # noqa: E402


MANIFEST_FORMAT_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SECRET_RE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    r"Bearer\s+[A-Za-z0-9._-]{16,})")


class ManifestError(ValueError):
    """The requested manifest does not satisfy the experiment contract."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(value: Any) -> str:
    text = value if isinstance(value, str) else _canonical(value)
    return _sha256_bytes(text.encode())


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_pairs(path: str) -> list[dict]:
    rows = []
    try:
        fh = open(path)
    except OSError as exc:
        raise ManifestError(f"cannot read pair input {path}: {exc}") from exc
    with fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ManifestError(f"{path}:{lineno}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ManifestError(f"{path}:{lineno}: row must be an object")
            rows.append(row)
    if not rows:
        raise ManifestError(f"{path}: no pair rows")
    return rows


def _parse_source_roots(values: list[str]) -> dict[str, str]:
    roots = {}
    for value in values:
        if "=" not in value:
            raise ManifestError("--source-root must be NAMESPACE=PATH")
        namespace, path = value.split("=", 1)
        try:
            validate_namespace(namespace)
        except ValueError as exc:
            raise ManifestError(str(exc)) from exc
        if namespace in roots:
            raise ManifestError(f"duplicate source namespace {namespace!r}")
        root = os.path.realpath(os.path.expanduser(path))
        if not os.path.isdir(root):
            raise ManifestError(f"source root for {namespace!r} is not a directory")
        roots[namespace] = root
    if not roots:
        raise ManifestError("at least one --source-root is required")
    return roots


def _resolved_source_path(root: str, relpath: str) -> str:
    if not isinstance(relpath, str) or not relpath or os.path.isabs(relpath):
        raise ManifestError("source_relpath must be a non-empty relative path")
    path = os.path.realpath(os.path.join(root, relpath))
    try:
        inside = os.path.commonpath([root, path]) == root
    except ValueError:
        inside = False
    if not inside or path == root:
        raise ManifestError(f"source_relpath escapes its declared root: {relpath!r}")
    return path


class SourceVerifier:
    def __init__(self, roots: dict[str, str]):
        self.roots = roots
        self.cache = {}
        self.event_locations = {}
        self.session_locations = {}

    def _load(self, namespace: str, relpath: str):
        key = (namespace, relpath)
        if key in self.cache:
            return self.cache[key]
        if namespace not in self.roots:
            raise ManifestError(f"no --source-root declared for {namespace!r}")
        path = _resolved_source_path(self.roots[namespace], relpath)
        try:
            meta, steps = read_transcript(path, self.roots[namespace], namespace)
        except (OSError, ValueError) as exc:
            raise ManifestError(f"cannot verify {namespace}:{relpath}: {exc}") from exc
        other_session = self.session_locations.get(meta.session_id)
        if other_session is not None and other_session != key:
            raise ManifestError(
                f"ambiguous source session across {other_session[0]}:{other_session[1]} and "
                f"{namespace}:{relpath}")
        self.session_locations[meta.session_id] = key
        events = {}
        for step in steps:
            if step.kind != "action":
                continue
            if step.source_event_id in events:
                raise ManifestError(
                    f"ambiguous source event within {namespace}:{relpath}")
            other = self.event_locations.get(step.source_event_id)
            if other is not None and other != key:
                raise ManifestError(
                    f"ambiguous source event across {other[0]}:{other[1]} and "
                    f"{namespace}:{relpath}")
            self.event_locations[step.source_event_id] = key
            events[step.source_event_id] = step
        self.cache[key] = (meta, events)
        return self.cache[key]

    def verify(self, pair: dict):
        required = (
            "identity_format", "source_namespace", "source_relpath", "session",
            "transcript_sha256", "source_event_id", "source_event_ordinal", "tool_name",
            "label", "label_set_version", "query_format_version", "prior_actions",
        )
        missing = [key for key in required if key not in pair]
        if missing:
            raise ManifestError(f"pair is missing fields: {', '.join(missing)}")
        if pair["identity_format"] != IDENTITY_FORMAT_VERSION:
            raise ManifestError("identity_format drift")
        if pair["label_set_version"] != tx.LABEL_SET_VERSION:
            raise ManifestError("label_set_version drift")
        if pair["query_format_version"] != ser.QUERY_FORMAT_VERSION:
            raise ManifestError("query_format_version drift")
        if pair["label"] not in tx.LABELS_V1:
            raise ManifestError(f"unknown label {pair['label']!r}")
        for field in ("session", "transcript_sha256", "source_event_id"):
            value = pair[field]
            if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
                raise ManifestError(f"invalid {field}")
        ordinal = pair["source_event_ordinal"]
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            raise ManifestError("invalid source_event_ordinal")
        if not isinstance(pair["tool_name"], str) or not pair["tool_name"]:
            raise ManifestError("invalid tool_name")
        if not isinstance(pair["prior_actions"], list) or not pair["prior_actions"]:
            raise ManifestError("prior_actions must be a non-empty list")
        if not isinstance(pair.get("recent_user_request", ""), str):
            raise ManifestError("recent_user_request must be a string")
        namespace = pair["source_namespace"]
        try:
            validate_namespace(namespace)
        except ValueError as exc:
            raise ManifestError(str(exc)) from exc
        meta, events = self._load(namespace, pair["source_relpath"])
        if pair["transcript_sha256"] != meta.transcript_sha256:
            raise ManifestError(
                f"transcript hash drift for {namespace}:{pair['source_relpath']}")
        if pair["session"] != meta.session_id:
            raise ManifestError(
                f"session identity drift for {namespace}:{pair['source_relpath']}")
        event = events.get(pair["source_event_id"])
        if event is None:
            raise ManifestError(f"source event is missing: {pair['source_event_id']}")
        if pair["source_event_ordinal"] != event.action_ordinal:
            raise ManifestError(f"source event ordinal drift: {pair['source_event_id']}")
        if pair["tool_name"] != event.tool:
            raise ManifestError(f"source event tool drift: {pair['source_event_id']}")
        observed_label, _ = tx.label_call(event.tool, event.tool_input or {})
        if pair["label"] != observed_label:
            raise ManifestError(f"source event label drift: {pair['source_event_id']}")


def _duplicate_summary(values: list[str]) -> dict[str, int]:
    counts = collections.Counter(values)
    groups = [count for count in counts.values() if count > 1]
    return {"groups": len(groups), "extra_occurrences": sum(count - 1 for count in groups)}


def _build_side(name: str, path: str, schemas: list[dict], verifier: SourceVerifier,
                context_steps: int, user_chars: int, pairs=None,
                selection=None) -> dict:
    pairs = _load_pairs(path) if pairs is None else pairs
    if not pairs:
        raise ManifestError(f"{name}: selection produced no pair rows")
    rows, event_ids = [], set()
    labels = collections.Counter()
    for pair in pairs:
        verifier.verify(pair)
        event_id = pair["source_event_id"]
        if event_id in event_ids:
            raise ManifestError(f"{name}: duplicate source_event_id {event_id}")
        event_ids.add(event_id)
        try:
            rendered = ser.to_finetune_row(pair, schemas, context_steps, user_chars)
        except (KeyError, TypeError, ValueError) as exc:
            raise ManifestError(f"{name}: cannot serialize {event_id}: {exc}") from exc
        q1_hash = _sha256(rendered["query"])
        content_hash = _sha256([
            pair.get("recent_user_request", ""), pair["prior_actions"],
        ])
        labels[pair["label"]] += 1
        rows.append({
            "source_namespace": pair["source_namespace"],
            "source_relpath": pair["source_relpath"],
            "session": pair["session"],
            "source_event_id": event_id,
            "source_event_ordinal": pair["source_event_ordinal"],
            "transcript_sha256": pair["transcript_sha256"],
            "q1_sha256": q1_hash,
            "content_sha256": content_hash,
            "full_row_sha256": _sha256(rendered),
            "label": pair["label"],
        })
    rows.sort(key=lambda row: row["source_event_id"])
    sessions = {row["session"] for row in rows}
    transcript_keys = {
        (row["source_namespace"], row["transcript_sha256"]) for row in rows
    }
    side = {
        "name": name,
        "input_sha256": _file_sha256(path),
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "sessions": len(sessions),
            "source_namespaces": sorted({row["source_namespace"] for row in rows}),
            "source_transcripts": len(transcript_keys),
            "source_digest": _sha256(sorted(transcript_keys)),
            "labels_present": len(labels),
            "distribution": dict(sorted(labels.items())),
            "q1_duplicates": _duplicate_summary([row["q1_sha256"] for row in rows]),
            "content_duplicates": _duplicate_summary(
                [row["content_sha256"] for row in rows]),
        },
    }
    if selection is not None:
        side["selection"] = selection
    return side


def _overlap(left: dict, right: dict) -> dict[str, Optional[int]]:
    fields = ("session", "source_event_id", "q1_sha256", "content_sha256")
    result = {}
    for field in fields:
        if (all(field in row for row in left["rows"]) and
                all(field in row for row in right["rows"])):
            result[field] = len({row[field] for row in left["rows"]} &
                                {row[field] for row in right["rows"]})
        else:
            result[field] = None
    return result


def _build_legacy_exclusion(name: str, path: str, schemas: list[dict],
                            context_steps: int, user_chars: int) -> dict:
    """Hash a frozen pre-identity pair file without pretending source joins exist."""
    pairs = _load_pairs(path)
    rows, labels = [], collections.Counter()
    for lineno, pair in enumerate(pairs, 1):
        if pair.get("label") not in tx.LABELS_V1:
            raise ManifestError(f"legacy exclusion {name}:{lineno}: invalid label")
        if not isinstance(pair.get("prior_actions"), list) or not pair["prior_actions"]:
            raise ManifestError(f"legacy exclusion {name}:{lineno}: invalid prior_actions")
        try:
            rendered = ser.to_finetune_row(pair, schemas, context_steps, user_chars)
        except (KeyError, TypeError, ValueError) as exc:
            raise ManifestError(
                f"legacy exclusion {name}:{lineno}: cannot serialize: {exc}") from exc
        labels[pair["label"]] += 1
        rows.append({
            "q1_sha256": _sha256(rendered["query"]),
            "content_sha256": _sha256([
                pair.get("recent_user_request", ""), pair["prior_actions"],
            ]),
            "full_row_sha256": _sha256(rendered),
            "label": pair["label"],
        })
    sessions = {
        pair.get("session") for pair in pairs
        if isinstance(pair.get("session"), str) and pair["session"]
    }
    return {
        "name": f"legacy-exclusion:{name}",
        "kind": "legacy-pairs-without-source-event-identity",
        "input_sha256": _file_sha256(path),
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "sessions": len(sessions),
            "labels_present": len(labels),
            "distribution": dict(sorted(labels.items())),
            "q1_duplicates": _duplicate_summary([row["q1_sha256"] for row in rows]),
            "content_duplicates": _duplicate_summary(
                [row["content_sha256"] for row in rows]),
            "source_identity": "unavailable in frozen legacy pairs",
        },
    }


def _legacy_membership(
        args, pairs: list[dict]) -> tuple[Optional[list[dict]], Optional[dict]]:
    values = (args.correction_membership_pairs, args.correction_legacy_source_prefix)
    if not any(values):
        return None, None
    if not all(values):
        raise ManifestError(
            "--correction-membership-pairs and --correction-legacy-source-prefix "
            "must be used together")
    prefix = args.correction_legacy_source_prefix.rstrip("/")
    if not prefix.startswith("/"):
        raise ManifestError("--correction-legacy-source-prefix must be absolute")
    membership_rows = _load_pairs(args.correction_membership_pairs)
    allowed = {
        row.get("session") for row in membership_rows
        if row.get("split") == args.correction_membership_split
        and isinstance(row.get("session"), str) and row["session"]
    }
    if not allowed:
        raise ManifestError("correction membership selection has no allowed sessions")
    selected, recovered = [], set()
    for pair in pairs:
        relpath = pair.get("source_relpath")
        if not isinstance(relpath, str) or not relpath:
            raise ManifestError("correction pair lacks source_relpath for legacy membership")
        legacy_path = prefix + "/" + relpath
        legacy_session = hashlib.sha256(legacy_path.encode()).hexdigest()[:16]
        if legacy_session in allowed:
            selected.append(pair)
            recovered.add(legacy_session)
    selection = {
        "method": "legacy absolute-path session hash matched from source_relpath",
        "membership_input_sha256": _file_sha256(args.correction_membership_pairs),
        "membership_split": args.correction_membership_split,
        "membership_sessions": len(allowed),
        "recovered_sessions": len(recovered),
        "selected_rows": len(selected),
    }
    return selected, selection


def _parse_named_paths(values: list[str], flag: str) -> list[tuple[str, str]]:
    parsed, seen = [], set()
    for value in values:
        if "=" not in value:
            raise ManifestError(f"{flag} must be NAME=PATH")
        name, path = value.split("=", 1)
        try:
            validate_namespace(name)
        except ValueError as exc:
            raise ManifestError(f"invalid {flag} name: {exc}") from exc
        if name in seen:
            raise ManifestError(f"duplicate {flag} name {name!r}")
        seen.add(name)
        parsed.append((name, path))
    return parsed


def _ensure_private_output(path: str) -> str:
    data_root = os.path.realpath("data")
    output = os.path.realpath(path)
    try:
        inside = os.path.commonpath([data_root, output]) == data_root
    except ValueError:
        inside = False
    if not inside or output == data_root:
        raise ManifestError("private manifest --out must be a file under data/")
    return output


def _assert_public_safe(receipt_text: str, source_roots: dict[str, str]) -> None:
    if _SECRET_RE.search(receipt_text):
        raise ManifestError("public receipt matched a credential pattern")
    forbidden = {os.path.realpath(os.path.expanduser("~")), *source_roots.values()}
    if any(path and path in receipt_text for path in forbidden):
        raise ManifestError("public receipt contains a local path")


def _write_new(path: str, text: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        with open(path, "x") as fh:
            fh.write(text)
    except FileExistsError as exc:
        raise ManifestError(f"refusing to overwrite {path}") from exc


def build(args) -> tuple[dict, dict]:
    roots = _parse_source_roots(args.source_root)
    schemas = ser.load_schemas(args.schemas)
    verifier = SourceVerifier(roots)
    correction_pairs = _load_pairs(args.correction)
    selected_pairs, selection = _legacy_membership(args, correction_pairs)
    correction = _build_side(
        "correction", args.correction, schemas, verifier,
        args.context_steps, args.user_chars,
        pairs=selected_pairs if selected_pairs is not None else correction_pairs,
        selection=selection)
    evaluation = _build_side(
        "evaluation", args.evaluation, schemas, verifier,
        args.context_steps, args.user_chars)
    exclusions = {
        name: _build_side(
            f"exclusion:{name}", path, schemas, verifier,
            args.context_steps, args.user_chars)
        for name, path in _parse_named_paths(args.exclude, "--exclude")
    }
    for name, path in _parse_named_paths(args.exclude_legacy, "--exclude-legacy"):
        if name in exclusions:
            raise ManifestError(f"duplicate exclusion name {name!r}")
        exclusions[name] = _build_legacy_exclusion(
            name, path, schemas, args.context_steps, args.user_chars)
    separation = {
        "correction_vs_evaluation": _overlap(correction, evaluation),
        "evaluation_vs_exclusions": {
            name: _overlap(evaluation, side) for name, side in exclusions.items()
        },
    }
    failures = {}
    for boundary, overlap in (("correction_vs_evaluation",
                               separation["correction_vs_evaluation"]),
                              *separation["evaluation_vs_exclusions"].items()):
        nonzero = {
            key: value for key, value in overlap.items()
            if isinstance(value, int) and value > 0
        }
        if nonzero:
            failures[boundary] = nonzero
    if failures:
        raise ManifestError(f"cross-boundary overlap: {_canonical(failures)}")
    manifest = {
        "manifest_format_version": MANIFEST_FORMAT_VERSION,
        "identity_format": IDENTITY_FORMAT_VERSION,
        "label_set_version": tx.LABEL_SET_VERSION,
        "query_format_version": ser.QUERY_FORMAT_VERSION,
        "context_steps": args.context_steps,
        "user_chars": args.user_chars,
        "schemas_sha256": _file_sha256(args.schemas),
        "sides": {"correction": correction, "evaluation": evaluation},
        "exclusions": exclusions,
        "separation": separation,
    }
    manifest["manifest_sha256"] = _sha256(manifest)
    receipt = {
        "receipt_format": "feedback-source-gate-v1",
        "status": "ok",
        "manifest_sha256": manifest["manifest_sha256"],
        "identity_format": IDENTITY_FORMAT_VERSION,
        "label_set_version": tx.LABEL_SET_VERSION,
        "query_format_version": ser.QUERY_FORMAT_VERSION,
        "context_steps": args.context_steps,
        "user_chars": args.user_chars,
        "schemas_sha256": manifest["schemas_sha256"],
        "sides": {
            name: {"input_sha256": side["input_sha256"], **side["summary"],
                   **({"selection": side["selection"]} if "selection" in side else {})}
            for name, side in (("correction", correction), ("evaluation", evaluation))
        },
        "exclusions": {
            name: {"input_sha256": side["input_sha256"], **side["summary"]}
            for name, side in exclusions.items()
        },
        "separation": separation,
        "privacy": "aggregate hashes and counts only; no prompts, commands, rows, or local paths",
    }
    _assert_public_safe(_canonical(receipt), roots)
    return manifest, receipt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--correction", required=True, help="private namespaced pair JSONL")
    ap.add_argument("--evaluation", required=True, help="private namespaced pair JSONL")
    ap.add_argument("--source-root", action="append", default=[],
                    help="NAMESPACE=PATH; repeat for every source namespace")
    ap.add_argument("--correction-membership-pairs",
                    help="legacy pair JSONL whose selected split defines correction sessions")
    ap.add_argument("--correction-membership-split", default="train")
    ap.add_argument("--correction-legacy-source-prefix",
                    help="original absolute source prefix used by legacy path-hash session IDs")
    ap.add_argument("--exclude", action="append", default=[],
                    help="NAME=PAIR_JSONL boundary that evaluation must not overlap; repeatable")
    ap.add_argument("--exclude-legacy", action="append", default=[],
                    help="NAME=legacy PAIR_JSONL; checks q1/content without source-event claims")
    ap.add_argument("--out", required=True, help="private manifest path under data/")
    ap.add_argument("--receipt", help="optional aggregate-only public receipt")
    ap.add_argument("--schemas", default=ser.SCHEMAS_PATH)
    ap.add_argument("--context-steps", type=int, default=ser.DEFAULT_CONTEXT_STEPS)
    ap.add_argument("--user-chars", type=int, default=ser.DEFAULT_USER_CHARS)
    args = ap.parse_args(argv)
    try:
        output = _ensure_private_output(args.out)
        destinations = [output]
        if args.receipt:
            destinations.append(os.path.realpath(args.receipt))
        inputs = {os.path.realpath(args.correction), os.path.realpath(args.evaluation),
                  os.path.realpath(args.schemas)}
        if len(destinations) != len(set(destinations)) or any(p in inputs for p in destinations):
            raise ManifestError("outputs must be distinct and must not overwrite inputs")
        if any(os.path.exists(path) for path in destinations):
            raise ManifestError("refusing to overwrite an existing output")
        manifest, receipt = build(args)
        manifest_text = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        receipt_text = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
        _write_new(output, manifest_text)
        if args.receipt:
            _write_new(os.path.realpath(args.receipt), receipt_text)
        print(json.dumps({
            "status": "ok",
            "manifest_sha256": manifest["manifest_sha256"],
            "correction_rows": receipt["sides"]["correction"]["rows"],
            "evaluation_rows": receipt["sides"]["evaluation"]["rows"],
            "separation": receipt["separation"],
        }, sort_keys=True))
        return 0
    except (ManifestError, OSError, RuntimeError) as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
