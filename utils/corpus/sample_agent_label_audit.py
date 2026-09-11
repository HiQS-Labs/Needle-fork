#!/usr/bin/env python3
"""Create a deterministic blind semantic-label sample from normalized agents.

The sample and held-back sorter labels contain private tool arguments and must
stay below the repository's ignored ``data/`` directory. Only ``plan.json``
contains aggregate counts suitable for publication after a privacy review.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import tempfile
import sys
from pathlib import Path

CORPUS = Path(__file__).resolve().parent
sys.path.insert(0, str(CORPUS))
REPOSITORY_ROOT = CORPUS.parent.parent
PRIVATE_DATA_ROOT = (REPOSITORY_ROOT / "data").resolve()

import audit_agent_label_coverage as coverage  # noqa: E402
import sample_for_audit as sampler  # noqa: E402
import taxonomy as tx  # noqa: E402
from normalized_transcript import AdapterError, canonical_json  # noqa: E402


SAMPLE_FORMAT_VERSION = "agent-label-blind-sample-v1"


class SampleError(ValueError):
    """The source cannot produce a complete blind audit sample."""


def _private_output(path: Path) -> Path:
    """Require a new output directory under the ignored private data tree."""
    resolved = path.expanduser().resolve()
    try:
        relative = resolved.relative_to(PRIVATE_DATA_ROOT)
    except ValueError as exc:
        raise SampleError(
            "output directory must be below the repository data directory") from exc
    if not relative.parts:
        raise SampleError(
            "output directory must be below the repository data directory")
    if resolved.exists():
        raise SampleError("output directory already exists")
    return resolved


def build_pool(source: str, root: Path, namespace: str) -> dict[str, list[dict]]:
    """Group every accepted action by the unchanged taxonomy prediction."""
    pool: dict[str, list[dict]] = collections.defaultdict(list)
    seen_events = set()
    for transcript, rejection, _digest in coverage.read_independent(
            source, root, namespace):
        if rejection:
            continue
        meta, steps = transcript
        for step in steps:
            if step.kind != "action":
                continue
            if step.source_event_id in seen_events:
                raise SampleError("duplicate normalized source event identity")
            seen_events.add(step.source_event_id)
            label = "unmapped"
            if step.canonical_tool is not None:
                label, _evidence = tx.label_call(
                    step.canonical_tool, step.tool_input)
            pool[label].append({
                "session": meta.session_id,
                "tool": step.source_tool,
                "text": canonical_json(step.tool_input),
                "source_namespace": meta.source_namespace,
                "transcript_sha256": meta.transcript_sha256,
                "source_event_id": step.source_event_id,
            })
    if not seen_events:
        raise SampleError(f"{source}: sample source produced zero actions")
    return dict(pool)


def build_draw(source: str, root: Path, namespace: str, target: int,
               floor: int, seed: int) -> tuple[dict, list[dict], list[dict]]:
    """Allocate and draw one blind sample, returning aggregate plan and rows."""
    pool = build_pool(source, root, namespace)
    population = {label: len(rows) for label, rows in sorted(pool.items())}
    allocation = sampler.allocate(population, target, floor)
    sample, truth = sampler.draw(pool, allocation, seed)
    plan = {
        "audit_format_version": 2,
        "sample_format_version": SAMPLE_FORMAT_VERSION,
        "sampling_design": sampler.SAMPLING_DESIGN,
        "source": source,
        "source_namespace": namespace,
        "label_set_version": tx.LABEL_SET_VERSION,
        "seed": seed,
        "target": target,
        "floor": floor,
        "population": population,
        "allocation": allocation,
        "drawn": len(sample),
        "drawn_labels": len(allocation),
        "drawn_sessions": len({row["session"] for row in truth}),
    }
    if len(sample) != target or len(truth) != target:
        raise SampleError("blind draw did not reach its requested target")
    return plan, sample, truth


def _jsonl(rows: list[dict]) -> str:
    """Encode deterministic newline-delimited JSON."""
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                   for row in rows)


def main() -> int:
    """Run the fail-closed blind-sample CLI."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True,
                    choices=["codex", "agy_desktop", "agy_cli", "zcode"])
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--namespace", required=True)
    ap.add_argument("--target", type=int, required=True)
    ap.add_argument("--floor", type=int, default=4)
    ap.add_argument("--seed", type=int, default=3701)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    try:
        out = _private_output(args.out_dir)
        plan, sample, truth = build_draw(
            args.source, args.root, args.namespace,
            args.target, args.floor, args.seed)
        encoded = {
            "plan.json": json.dumps(plan, indent=2, sort_keys=True) + "\n",
            "sample.jsonl": _jsonl(sample),
            "sorter.jsonl": _jsonl(truth),
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
                prefix=f".{out.name}.", dir=out.parent) as staging:
            staged = Path(staging)
            for name, content in encoded.items():
                (staged / name).write_text(content)
            os.replace(staged, out)
    except (AdapterError, SampleError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
