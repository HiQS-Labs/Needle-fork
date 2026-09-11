#!/usr/bin/env python3
"""Validate reviewed augmentation candidates and publish an immutable training run."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serialize  # noqa: E402

KINDS = {"paraphrase", "counterfactual", "negation", "mixed_event", "abstention"}
SEED_FIELDS = {"source_id", "source_kind", "reviewed_by", "taxonomy_version", "label",
               "recent_user_request", "prior_actions"}
_HEX = frozenset("0123456789abcdef")


class ContractError(ValueError):
    pass


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and set(value) <= _HEX


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ContractError(f"{path.name}:{number}: invalid JSON") from exc
                if not isinstance(value, dict):
                    raise ContractError(f"{path.name}:{number}: expected object")
                rows.append(value)
    return rows


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _fsync_file(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def compose(seeds_path: Path, candidates_path: Path, output_parent: Path, run_id: str,
            forbidden_path: Path | None = None, fail_before_publish: bool = False) -> Path:
    seeds, candidates = read_jsonl(seeds_path), read_jsonl(candidates_path)
    _require(bool(seeds), "reviewed seed input is empty")
    _require(bool(candidates), "candidate input is empty")
    _require(run_id and Path(run_id).name == run_id, "run-id must be one path component")

    seed_by_id: dict[str, tuple[dict, str]] = {}
    digest_bytes: dict[str, bytes] = {}
    for seed in seeds:
        _require(set(seed) == SEED_FIELDS, "seed fields do not match the v1 contract")
        _require(all(isinstance(seed[k], str) and seed[k] for k in
                     ("source_id", "source_kind", "reviewed_by", "taxonomy_version", "label")),
                 "seed identity fields must be nonempty strings")
        _require(isinstance(seed["recent_user_request"], str) and
                 isinstance(seed["prior_actions"], list), "seed content has invalid types")
        _require(seed["source_kind"] in {"human", "rule"}, "invalid source_kind")
        _require(bool(seed["reviewed_by"]), "reviewed_by is required")
        _require(seed["label"] in serialize.tx.LABELS_V1, f"unknown seed label: {seed['label']}")
        _require(bool(seed["prior_actions"]) and all(
            action in serialize.tx.LABELS_V1 or action == "unmapped"
            for action in seed["prior_actions"]), "invalid seed prior_actions")
        sid, raw, sha = seed["source_id"], canonical_bytes(seed), digest(seed)
        _require(sid not in seed_by_id, f"duplicate source_id: {sid}")
        if sha in digest_bytes and digest_bytes[sha] != raw:
            raise ContractError("SHA-256 collision between unequal seed bytes")
        digest_bytes[sha] = raw
        seed_by_id[sid] = (seed, sha)

    forbidden: set[str] = set()
    if forbidden_path:
        doc = json.loads(forbidden_path.read_text(encoding="utf-8"))
        _require(isinstance(doc, dict), "forbidden manifest must be an object")
        ids, hashes = doc.get("source_ids", []), doc.get("source_sha256", [])
        _require(isinstance(ids, list) and isinstance(hashes, list) and
                 all(isinstance(v, str) and v for v in ids + hashes),
                 "forbidden identities must be nonempty string lists")
        forbidden = set(ids) | set(hashes)

    seen_records: set[str] = set()
    seen_requests: set[str] = set()
    pairs: dict[str, list[dict]] = defaultdict(list)
    normalized: list[dict] = []
    for row in candidates:
        for key in ("record_id", "source_id", "source_sha256", "split", "generated", "kind",
                    "generator", "config_sha256", "taxonomy_version", "recent_user_request",
                    "prior_actions", "label"):
            _require(key in row, f"candidate missing {key}")
        _require(all(isinstance(row[k], str) and row[k] for k in
                     ("record_id", "source_id", "source_sha256", "split", "kind", "generator",
                      "config_sha256", "taxonomy_version", "recent_user_request", "label")),
                 "candidate identity/content fields must be nonempty strings")
        _require(isinstance(row["prior_actions"], list), "candidate prior_actions must be a list")
        _require(_is_sha256(row["source_sha256"]), "source_sha256 must be lowercase SHA-256")
        _require(_is_sha256(row["config_sha256"]), "config_sha256 must be lowercase SHA-256")
        _require(row["record_id"] not in seen_records, f"duplicate record_id: {row['record_id']}")
        seen_records.add(row["record_id"])
        _require(row["split"] == "train" and row["generated"] is True,
                 "candidate must be generated training data")
        _require(row["kind"] in KINDS, f"invalid augmentation kind: {row['kind']}")
        _require(row["source_id"] in seed_by_id, f"unknown source_id: {row['source_id']}")
        seed, actual_sha = seed_by_id[row["source_id"]]
        _require(row["source_sha256"] == actual_sha, f"source digest mismatch: {row['source_id']}")
        _require(row["source_id"] not in forbidden and actual_sha not in forbidden,
                 f"forbidden source identity: {row['source_id']}")
        _require(row.get("taxonomy_version") == seed["taxonomy_version"], "taxonomy version mismatch")
        _require(row["label"] == seed["label"] and row["prior_actions"] == seed["prior_actions"],
                 f"candidate label/actions are not grounded by seed: {row['source_id']}")
        request_key = hashlib.sha256(serialize._clean(row["recent_user_request"]).encode()).hexdigest()
        _require(request_key not in seen_requests, "duplicate normalized request")
        seen_requests.add(request_key)
        if row["kind"] == "counterfactual":
            _require(isinstance(row.get("pair_id"), str) and bool(row["pair_id"]) and
                     row.get("pair_role") in {"baseline", "counterfactual"},
                     "counterfactual requires pair_id and pair_role")
            pairs[row["pair_id"]].append(row)
        normalized.append(row)

    for pair_id, pair in pairs.items():
        _require(len(pair) == 2 and {r["pair_role"] for r in pair} == {"baseline", "counterfactual"},
                 f"incomplete counterfactual pair: {pair_id}")
        before = next(r for r in pair if r["pair_role"] == "baseline")
        after = next(r for r in pair if r["pair_role"] == "counterfactual")
        change = before.get("controlled_change")
        other_change = after.get("controlled_change")
        _require(isinstance(change, dict) and isinstance(other_change, dict),
                 f"controlled_change must be an object: {pair_id}")
        for item in (change, other_change):
            _require(isinstance(item.get("before"), str) and
                     isinstance(item.get("after"), str) and bool(item["before"]),
                     f"controlled spans must be strings: {pair_id}")
        _require(change == other_change,
                 f"controlled_change mismatch: {pair_id}")
        exceptions = {"record_id", "pair_role", "label", "recent_user_request", "controlled_change"}
        _require({k: v for k, v in before.items() if k not in exceptions} ==
                 {k: v for k, v in after.items() if k not in exceptions},
                 f"counterfactual undeclared field drift: {pair_id}")
        old, new = change.get("before", ""), change.get("after", "")
        _require(before["recent_user_request"].count(old) == 1,
                 f"controlled before span must occur exactly once: {pair_id}")
        _require(before["recent_user_request"].replace(old, new, 1) == after["recent_user_request"],
                 f"counterfactual changes more than declared span: {pair_id}")

    schemas = serialize.load_schemas()
    normalized.sort(key=lambda r: r["record_id"])
    trainer_rows = [serialize.to_finetune_row(r, schemas) for r in normalized]
    expected_row_fields = {"query", "tools", "answers", "reasoning", "system"}
    _require(all(isinstance(row, dict) and set(row) == expected_row_fields for row in trainer_rows),
             "canonical serializer returned an invalid trainer row")
    manifest_rows = [{"record_id": r["record_id"], "source_id": r["source_id"],
                      "source_sha256": r["source_sha256"], "row_sha256": digest(out),
                      "split": "train", "generated": True}
                     for r, out in zip(normalized, trainer_rows)]
    report = {"records": len(normalized), "pairs": len(pairs),
              "labels": dict(sorted(Counter(r["label"] for r in normalized).items())),
              "kinds": dict(sorted(Counter(r["kind"] for r in normalized).items()))}

    output_parent.mkdir(parents=True, exist_ok=True)
    final = output_parent / run_id
    _require(not final.exists(), f"run already exists: {run_id}")
    stage = Path(tempfile.mkdtemp(prefix=f".{run_id}.", dir=output_parent))
    try:
        (stage / "training.jsonl").write_bytes(b"".join(canonical_bytes(r) + b"\n" for r in trainer_rows))
        (stage / "manifest.json").write_bytes(canonical_bytes({"version": 1, "rows": manifest_rows}) + b"\n")
        (stage / "report.json").write_bytes(canonical_bytes(report) + b"\n")
        for name in ("training.jsonl", "manifest.json", "report.json"):
            _fsync_file(stage / name)
        if fail_before_publish:
            raise ContractError("injected failure before publish")
        os.replace(stage, final)
        return final
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output-parent", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--forbidden", type=Path)
    args = parser.parse_args()
    try:
        final = compose(args.seeds, args.candidates, args.output_parent, args.run_id, args.forbidden)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"grounded augmentation refused: {exc}\n")
    print(final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
