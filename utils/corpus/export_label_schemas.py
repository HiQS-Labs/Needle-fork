#!/usr/bin/env python3
"""Publish the v1 label taxonomy as the machine-readable cross-repo contract.

Issue #1 §1 requires the taxonomy be published from THIS repo as a schema file,
because the extractor, the trainer, the evaluator and the Claude Code hook all
key off it -- and §1's third bullet requires the schemas be authored with this
repo's own `needle/agent/tools.py`, so executable tools and label schemas share
one definition instead of drifting.

So the schemas are not hand-written: each label becomes a zero-argument function
whose docstring is its description, and `build_schema` renders it exactly as it
renders a real `@needle.tool`. If needle's schema shape ever changes, this output
changes with it.

Zero arguments is the point. Per Message 3's Ponytail Output Simplification the
model predicts ONLY the label name; JSON argument generation is abandoned as
beyond a 45M edge model. A label with parameters would re-introduce it.

    python3 utils/corpus/export_label_schemas.py --out oracle/labels-v1.json
"""
from __future__ import annotations
import argparse, json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from needle.agent.tools import build_schema  # noqa: E402
import taxonomy as tx  # noqa: E402


def schema_for(name: str, meta: dict) -> dict:
    """Render one label through needle's own build_schema."""
    def _label():
        pass
    _label.__name__ = name
    _label.__doc__ = meta["description"]
    return build_schema(_label)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="oracle/labels-v1.json")
    args = ap.parse_args()

    schemas = [schema_for(n, m) for n, m in LABELS_ORDERED()]
    contract = {
        "label_set_version": tx.LABEL_SET_VERSION,
        "source_of_truth": "utils/corpus/taxonomy.py",
        "output_contract": "The model predicts ONLY a label name. Labels take no arguments.",
        "groups": sorted({m["group"] for m in tx.LABELS_V1.values()}),
        "labels": {n: {"group": m["group"], "tier": m["tier"], "detect": m["detect"]}
                   for n, m in tx.LABELS_V1.items()},
        "schemas": schemas,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(contract, fh, indent=2)
        fh.write("\n")
    print(f"wrote {args.out}  ({len(schemas)} label schemas, {tx.LABEL_SET_VERSION})")
    return 0


def LABELS_ORDERED():
    """Group-major, then alphabetical -- so the file diffs cleanly on change."""
    return sorted(tx.LABELS_V1.items(), key=lambda kv: (kv[1]["group"], kv[0]))


if __name__ == "__main__":
    raise SystemExit(main())
