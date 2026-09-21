#!/usr/bin/env python3
"""Score a Needle 3 `.cact` on the converted 100-row holdout, top-1 over all rows (GH-66 step 8).

Offline research script, not part of the installed `needle` runtime. One `complete()` per holdout
row through the native engine, with the same `query` and `system` the rows were converted with;
`reset()` between rows so no conversation state leaks. The prediction is
`function_calls[0].arguments.action`; an empty `function_calls` (refusal or suppressed call) or an
out-of-enum value is a miss, never skipped. Reports top-1, per-label recall, the confusion matrix,
the empty/suppressed counts, and the confidence distribution as context (None for tuned weights:
fine-tuning does not update the confidence head).

    python spike/coding_core/eval_needle3.py --weights <model.cact> \
        --holdout data/coding-core/pilot/needle3-holdout.jsonl --out <results.json> --label l20

`--weights base` scores the untuned base model (SOP Step 5's untuned control). Aggregates and
per-row (index, gold, prediction) only; no query text is written.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import to_needle3 as conv  # noqa: E402


def load_holdout(path: Path) -> tuple[list[dict], dict, str | None]:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not rows:
        raise SystemExit(f"{path}: no rows")
    tool = rows[0]["tools"][0]
    system = rows[0].get("system")
    for i, r in enumerate(rows):
        if r["tools"] != [tool] or r.get("system") != system:
            raise SystemExit(f"row {i}: tools/system differ from row 0; the holdout is not one contract")
    labels, descriptions = conv.load_labels()
    if tool != conv.next_action_tool(labels, descriptions):
        raise SystemExit("holdout tool is not the frozen next_action tool from labels.json")
    return rows, tool, system


def predict(agent, query: str, max_new_tokens: int) -> dict:
    agent.reset()
    t0 = time.perf_counter()
    r = agent.complete(query, max_new_tokens=max_new_tokens)
    wall = time.perf_counter() - t0
    calls = r.get("function_calls") or []
    held = r.get("suppressed_calls") or []
    action = None
    if calls and isinstance(calls[0], dict) and calls[0].get("name") == "next_action":
        action = (calls[0].get("arguments") or {}).get("action")
    return {"action": action, "n_calls": len(calls), "n_suppressed": len(held),
            "type": r.get("type"), "success": r.get("success"), "error": r.get("error"),
            "confidence": r.get("confidence"), "wall_s": round(wall, 3),
            "prefill_tps": r.get("prefill_tps"), "decode_tps": r.get("decode_tps"),
            "held_action": ((held[0].get("arguments") or {}).get("action") if held and isinstance(held[0], dict) else None)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", required=True, help="path to a .cact, or 'base' for the untuned model")
    ap.add_argument("--holdout", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--label", default="", help="short name for this arm, recorded in the results")
    ap.add_argument("--max-new-tokens", type=int, default=64)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists; one file per run")
    import needle

    rows, tool, system = load_holdout(a.holdout)
    labels = tool["parameters"]["properties"]["action"]["enum"]
    weights = None if a.weights == "base" else a.weights
    if weights and not Path(weights).exists():
        raise SystemExit(f"no such weights: {weights}")
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    t_all = time.perf_counter()
    agent = needle.Needle(tools=[tool], system=system, weights=weights, auto_date=False)
    load_s = time.perf_counter() - t_all
    preds = []
    for i, row in enumerate(rows):
        p = predict(agent, row["query"], a.max_new_tokens)
        gold = row["answers"][0]["arguments"]["action"]
        p.update({"index": i, "gold": gold, "correct": p["action"] == gold})
        preds.append(p)
        print(f"  row {i + 1:3d}/{len(rows)}  gold={gold:<11} pred={str(p['action']):<11} "
              f"{'ok ' if p['correct'] else 'MISS'} {p['wall_s']:.2f}s", file=sys.stderr, flush=True)
    # Determinism: row 0 again, after everything else, must reproduce.
    again = predict(agent, rows[0]["query"], a.max_new_tokens)
    agent.close()
    wall_all = time.perf_counter() - t_all
    finished = dt.datetime.now(dt.timezone.utc).isoformat()

    truth = [p["gold"] for p in preds]
    pred = [p["action"] for p in preds]
    correct = sum(1 for p in preds if p["correct"])
    per_label = {}
    for name in labels:
        n = sum(1 for t in truth if t == name)
        hit = sum(1 for t, q in zip(truth, pred) if t == name and q == name)
        predicted = sum(1 for q in pred if q == name)
        per_label[name] = {"support": n, "recall_correct": hit,
                           "recall": (hit / n) if n else None, "predicted": predicted}
    universe = labels + ["<empty>"]
    idx = {u: k for k, u in enumerate(universe)}
    confusion = [[0] * len(universe) for _ in universe]
    for t, q in zip(truth, pred):
        confusion[idx[t]][idx[q if q in idx else "<empty>"]] += 1
    conf = [p["confidence"] for p in preds]
    results = {
        "arm": a.label, "weights": ("base (untuned)" if weights is None else Path(weights).name),
        "weights_sha256": (None if weights is None else hashlib.sha256(Path(weights).read_bytes()).hexdigest()),
        "holdout_sha256": hashlib.sha256(a.holdout.read_bytes()).hexdigest(),
        "tool_sha256": hashlib.sha256(json.dumps(tool, sort_keys=True).encode()).hexdigest(),
        "utc_started": started, "utc_finished": finished,
        "rows": len(rows), "scored": len(preds), "skipped": 0,
        "top1_correct": correct, "top1_accuracy_pct": 100.0 * correct / len(preds),
        "empty_calls": sum(1 for p in preds if p["n_calls"] == 0),
        "suppressed_calls": sum(1 for p in preds if p["n_suppressed"]),
        "out_of_enum": sum(1 for q in pred if q is not None and q not in labels),
        "errors": sum(1 for p in preds if p["error"]),
        "per_label": per_label,
        "confusion_labels": universe, "confusion": confusion,
        "prediction_counts": dict(collections.Counter(str(q) for q in pred)),
        "confidence": {"reported": sum(1 for c in conf if c is not None),
                       "values_summary": (None if not any(c is not None for c in conf) else {
                           "min": min(c for c in conf if c is not None),
                           "max": max(c for c in conf if c is not None)})},
        "deterministic_row0": again["action"] == preds[0]["action"],
        "timing": {"wall_s_total": round(wall_all, 1), "engine_load_s": round(load_s, 2),
                   "per_row_wall_s": {"min": min(p["wall_s"] for p in preds),
                                      "median": sorted(p["wall_s"] for p in preds)[len(preds) // 2],
                                      "max": max(p["wall_s"] for p in preds)},
                   "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 1)},
        "predictions": [{k: p[k] for k in ("index", "gold", "action", "correct", "n_calls", "n_suppressed",
                                            "held_action", "confidence", "type", "error")} for p in preds],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
    print(f"{a.label or a.weights}: top-1 {correct}/{len(preds)} = {results['top1_accuracy_pct']:.1f}%  "
          f"empty {results['empty_calls']}  suppressed {results['suppressed_calls']}  "
          f"wall {wall_all:.0f}s  deterministic_row0={results['deterministic_row0']}", file=sys.stderr)
    for name, m in per_label.items():
        print(f"  {name:<12} {m['recall_correct']:>3}/{m['support']:<3} predicted {m['predicted']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
