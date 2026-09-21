#!/usr/bin/env python3
"""Convert #42 pilot rows into Needle 3 fine-tune JSONL with one six-value enum tool (GH-66).

Offline research script, not part of the installed `needle` runtime. The pilot's `query` (the
serialized issue + recent-action context) and `system` line are copied verbatim; the only change
is the answer shape: six tools become one extraction tool `next_action` whose `action` argument is
an enum of the six coding-core labels, and the pilot's `reasoning` field is dropped. The converter
refuses unknown labels and rows without exactly one answer, so an abstention cannot slip through.

    python spike/coding_core/to_needle3.py data/coding-core/pilot \
        --out data/coding-core/pilot --max-len 1024

Writes needle3-train.jsonl, needle3-holdout.jsonl and preflight.json (row counts, per-label
support, token-length distribution against --max-len, boilerplate fraction with the real
tokenizer). Aggregates only; no row text is printed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics
import sys
from pathlib import Path

LABELS_PATH = Path(__file__).with_name("labels.json")


class InputError(ValueError):
    pass


def load_labels(path: Path = LABELS_PATH) -> tuple[list[str], dict[str, str]]:
    doc = json.loads(path.read_text())
    labels = list(doc["labels"])
    descriptions = {s["name"]: s["description"] for s in doc["schemas"]}
    if sorted(labels) != labels or set(labels) != set(descriptions):
        raise InputError("labels.json labels must be sorted and match its schemas")
    return labels, descriptions


def next_action_tool(labels: list[str], descriptions: dict[str, str]) -> dict:
    """The one extraction tool: `action` is a closed six-value enum."""
    glossary = "; ".join(f"{name}: {descriptions[name].rstrip('.')}" for name in labels)
    return {
        "name": "next_action",
        "description": "Predict the single best next broad coding action.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(labels),
                           "description": f"The next action. {glossary}."},
            },
            "required": ["action"],
        },
    }


def convert_row(row: dict, labels: list[str], tool: dict) -> dict:
    answers = row.get("answers")
    if not isinstance(answers, list) or len(answers) != 1:
        raise InputError("pilot row must carry exactly one answer (no abstentions in this projection)")
    label = answers[0].get("name") if isinstance(answers[0], dict) else None
    if label not in labels:
        raise InputError(f"unknown label {label!r}")
    query = row.get("query")
    if not isinstance(query, str) or not query.strip():
        raise InputError("pilot row must carry a nonempty query")
    out = {"query": query, "tools": [tool],
           "answers": [{"name": "next_action", "arguments": {"action": label}}]}
    system = row.get("system")
    if isinstance(system, str) and system.strip():
        out["system"] = system
    return out


def convert_file(src: Path, labels: list[str], tool: dict) -> list[dict]:
    rows = []
    with src.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise InputError(f"{src}:{lineno}: invalid JSON") from exc
            try:
                rows.append(convert_row(row, labels, tool))
            except InputError as exc:
                raise InputError(f"{src}:{lineno}: {exc}") from exc
    if not rows:
        raise InputError(f"{src}: no rows")
    return rows


def token_stats(rows: list[dict], max_len: int) -> dict:
    """Token-length distribution and constant (boilerplate) share with the real tokenizer."""
    from needle.model.finetune import render_example
    from needle.model.tokenizer import get_tokenizer

    tokenizer = get_tokenizer()
    # The constant share of each row: the rendered prompt with the variable query removed.
    stub = dict(rows[0], query="")
    stub_prompt, _ = render_example(stub)
    constant = len(tokenizer.encode(stub_prompt))
    totals, shares, targets = [], [], []
    for row in rows:
        prompt, target = render_example(row)
        p, t = len(tokenizer.encode(prompt)), len(tokenizer.encode(target))
        total = p + t + 2  # BOS + EOS, as finetune._encode counts
        totals.append(total)
        targets.append(t)
        shares.append(constant / total)
    return {
        "max_len": max_len,
        "constant_prefix_tokens": constant,
        "total_tokens": {"min": min(totals), "median": statistics.median(totals), "max": max(totals)},
        "target_tokens": {"min": min(targets), "median": statistics.median(targets), "max": max(targets)},
        "constant_share": {"min": round(min(shares), 4), "median": round(statistics.median(shares), 4),
                           "max": round(max(shares), 4)},
        "rows_over_max_len": sum(1 for n in totals if n > max_len),
        "constant_share_exceeds_half_of_median_row": constant > statistics.median(totals) / 2,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pilot_dir", type=Path, help="directory holding pilot-train.jsonl and pilot-holdout.jsonl")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-len", type=int, default=1024)
    ap.add_argument("--skip-token-stats", action="store_true", help="no JAX/tokenizer (tests)")
    a = ap.parse_args(argv)
    try:
        labels, descriptions = load_labels()
        tool = next_action_tool(labels, descriptions)
        report = {"tool_sha256": hashlib.sha256(json.dumps(tool, sort_keys=True).encode()).hexdigest(),
                  "labels": labels, "splits": {}}
        a.out.mkdir(parents=True, exist_ok=True)
        for split in ("train", "holdout"):
            src = a.pilot_dir / f"pilot-{split}.jsonl"
            rows = convert_file(src, labels, tool)
            dst = a.out / f"needle3-{split}.jsonl"
            write_jsonl(dst, rows)
            source_rows = sum(1 for l in src.read_text(encoding="utf-8").splitlines() if l.strip())
            support = collections.Counter(r["answers"][0]["arguments"]["action"] for r in rows)
            entry = {"source_rows": source_rows, "converted_rows": len(rows),
                     "rows_preserved": source_rows == len(rows),
                     "abstention_rows": 0,  # convert_row refuses them; a nonzero count cannot be written
                     "support": {name: support.get(name, 0) for name in labels},
                     "labels_with_zero_training_rows": [n for n in labels if support.get(n, 0) == 0] if split == "train" else None,
                     "source_sha256": sha256(src), "output_sha256": sha256(dst)}
            if not a.skip_token_stats:
                entry["tokens"] = token_stats(rows, a.max_len)
            report["splits"][split] = entry
        failures = []
        for split, entry in report["splits"].items():
            if not entry["rows_preserved"]:
                failures.append(f"{split}: row count changed")
            if "tokens" in entry and entry["tokens"]["rows_over_max_len"]:
                failures.append(f"{split}: {entry['tokens']['rows_over_max_len']} rows exceed --max-len")
        if report["splits"]["train"]["labels_with_zero_training_rows"]:
            failures.append("train: zero-support labels " + ",".join(report["splits"]["train"]["labels_with_zero_training_rows"]))
        report["preflight_failures"] = failures
        (a.out / "preflight.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    except (InputError, OSError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=1, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
