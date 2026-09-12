#!/usr/bin/env python3
"""#59 tool-free, budget-bounded collection and separate locked-response scoring.

Uses only the frozen quiz prompts over HTTP. Never sends a file, tool schema, or key
to the prediction model. Never executes response text. All raw output stays private.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import signal
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import context_refresh as refresh
import context_probe as probe
import prepare_openhands as prep

MAX_TOKENS = 4096
MAX_PRICE = {"prompt": 2, "completion": 6, "request": 0}  # USD per million tokens
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def read(path):
    return json.loads(path.read_text())


def verified_data(directory):
    manifest = read(directory / "manifest.json")
    if manifest["format"] != "coding-core-q3-paired-v1" or manifest["quiz_cases"] < 30:
        raise ValueError("wrong or empty frozen quiz")
    for name, expected in manifest["hashes"].items():
        if Path(name).name != name or prep.digest(directory / name) != expected:
            raise ValueError("frozen input hash mismatch")
    return manifest


def predictions(payload, ids):
    rows = payload.get("predictions")
    if not ids or not isinstance(rows, list) or len(rows) != len(ids):
        raise ValueError("empty or incomplete predictions")
    if any(not isinstance(r, dict) or set(r) != {"case_id", "predicted_action"} for r in rows):
        raise ValueError("invalid prediction schema")
    if {r["case_id"] for r in rows} != set(ids):
        raise ValueError("duplicate, missing or unknown prediction IDs")
    lookup = {r["case_id"]: r["predicted_action"] for r in rows}
    if any(v not in prep.LABELS for v in lookup.values()):
        raise ValueError("invalid prediction label")
    return [lookup[i] for i in ids]


def request_body(prompt):
    return dict(model=refresh.MODEL, messages=[dict(role="user", content=prompt)],
                temperature=0, max_tokens=MAX_TOKENS, stream=False,
                # #60: this endpoint requires reasoning; disabling it fails before inference.
                response_format={"type": "json_object"}, reasoning={"enabled": True, "effort": "low"},
                provider={"require_parameters": True, "allow_fallbacks": False,
                          "max_price": MAX_PRICE})


def budget(prompts, model):
    pricing = {k: float(v) for k, v in model["pricing"].items()}
    if any(not math.isfinite(v) or v < 0 for v in pricing.values()):
        raise ValueError("invalid model prices")
    # Conservative byte-token upper estimate, with 1024 extra tokens per single-message
    # request for formatting overhead. This is a preflight estimate, not account credit control.
    input_price = max(pricing["prompt"], pricing.get("input_cache_write", 0),
                      MAX_PRICE["prompt"] / 1000000)
    estimates = {a: (len(p.encode("utf-8")) + 1024) * input_price
                   + MAX_TOKENS * max(pricing["completion"], MAX_PRICE["completion"] / 1000000)
                 for a, p in prompts.items()}
    if pricing.get("request", 0) or any(pricing.get(k, 0) for k in ("web_search", "internal_reasoning")):
        raise ValueError("unexpected non-token pricing")
    worst = sum(estimates.values()) + max(estimates.values())  # reserve one infrastructure retry
    if not math.isfinite(worst) or worst > 1:
        raise ValueError("campaign exceeds $1 conservative token-cost ceiling")
    return dict(per_arm_usd=estimates, total_with_one_retry_usd=worst,
                input_bound="UTF-8 bytes + 1024 tokens per request", max_tokens=MAX_TOKENS)


def collect(data, out, key_file, deadline):
    out.mkdir(parents=True, exist_ok=False)
    manifest = verified_data(data)
    prompts = {a: (data / (a + "-prompt.txt")).read_text() for a in refresh.ARMS}
    with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=30) as response:
        models = json.load(response)["data"]
    model = next((m for m in models if m["id"] == refresh.MODEL), None)
    if model is None:
        raise ValueError("frozen model route unavailable; no substitution")
    cost = budget(prompts, model)
    key = key_file.read_text().strip()
    if not key.startswith("sk-or-") or any(c.isspace() for c in key):
        raise ValueError("credential file must contain only the OpenRouter key")
    refresh.write_json(out / "preflight.json", dict(model=refresh.MODEL, pricing=model["pricing"],
        budget=cost, deadline=deadline.isoformat(), input_manifest_sha256=prep.digest(data / "manifest.json"),
        collector_sha256=prep.digest(Path(__file__)), launched=datetime.now(timezone.utc).isoformat()))
    print(json.dumps(dict(event="preflight", **cost)), flush=True)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("request wall cap")))
    for arm in refresh.ARMS:
        seconds = min(600, int((deadline - datetime.now(timezone.utc)).total_seconds()) - 60)
        if seconds <= 0:
            raise TimeoutError("campaign deadline reached; preserving completed responses")
        body = request_body(prompts[arm])
        refresh.write_json(out / (arm + "-request.json"), body)
        req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        start = time.monotonic()
        signal.alarm(seconds)
        try:
            try:
                with urllib.request.urlopen(req, timeout=seconds) as response:
                    raw = response.read(2 * 1024 * 1024 + 1)
            except urllib.error.HTTPError as exc:
                # Preserve the reason without ever writing Authorization/request headers.
                detail = exc.read(65536).decode("utf-8", errors="replace")
                refresh.write_json(out / (arm + "-error.json"), dict(status=exc.code, detail=detail))
                raise ValueError(f"HTTP {exc.code}; error detail retained privately") from None
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("response exceeds 2 MiB cap")
            received = json.loads(raw)
            refresh.write_json(out / (arm + "-response.json"), received)
            choice = received["choices"][0]
            if received.get("model") != refresh.MODEL or choice.get("finish_reason") != "stop":
                raise ValueError("route mismatch or incomplete completion")
            message = choice["message"]
            if message.get("tool_calls") or message.get("function_call"):
                raise ValueError("unexpected tool request; never executed")
            parsed = json.loads(message["content"])
            ids = [r["case_id"] for r in read(data / (arm + "-quiz.json"))]
            predictions(parsed, ids)
            refresh.write_json(out / (arm + "-locked.json"), dict(predictions=parsed["predictions"],
                response_sha256=prep.digest(out / (arm + "-response.json")),
                request_sha256=prep.digest(out / (arm + "-request.json")),
                elapsed_seconds=time.monotonic() - start))
            print(json.dumps(dict(event="locked", arm=arm, predictions=len(ids),
                elapsed_seconds=round(time.monotonic() - start, 2), usage=received.get("usage"))), flush=True)
        finally:
            signal.alarm(0)
    # Deliberately separate collect from score; no target-based decisions during collection.
    print("All three responses locked; no correctness grading performed.", flush=True)


def score(data, responses):
    manifest = verified_data(data)
    preflight = read(responses / "preflight.json")
    if preflight["input_manifest_sha256"] != prep.digest(data / "manifest.json"):
        raise ValueError("collection used a different manifest")
    selected = read(data / "answer-key.json")
    if len(selected) != manifest["quiz_cases"] or len({p["q2"]["issue"] for p in selected}) != len(selected):
        raise ValueError("empty or misaligned answer key")
    ids = [q["case_id"] for q in read(data / "q2-quiz.json")]
    vectors, receipts = {}, {}
    for arm in refresh.ARMS:
        locked = read(responses / (arm + "-locked.json"))
        for suffix in ("response", "request"):
            if locked[suffix + "_sha256"] != prep.digest(responses / (arm + "-" + suffix + ".json")):
                raise ValueError("locked response/request hash mismatch")
        if read(responses / (arm + "-request.json")) != request_body((data / (arm + "-prompt.txt")).read_text()):
            raise ValueError("request differs from frozen arm")
        raw = read(responses / (arm + "-response.json"))
        parsed = json.loads(raw["choices"][0]["message"]["content"])
        vectors[arm] = predictions(locked, ids)
        if vectors[arm] != predictions(parsed, ids):
            raise ValueError("locked predictions differ from raw response")
        receipts[arm] = dict(model=raw["model"], provider=raw.get("provider"), usage=raw.get("usage"),
            elapsed_seconds=locked["elapsed_seconds"], response_sha256=locked["response_sha256"],
            request_sha256=locked["request_sha256"], locked_sha256=prep.digest(responses / (arm + "-locked.json")))
    baseline = read(data / "baseline-predictions.json")
    if len(baseline) != len(selected) or not baseline:
        raise ValueError("empty or mismatched baseline")
    for name in ("majority", "repeat_last", "markov_1", "phase_backoff"):
        vectors[name] = [r[name] for r in baseline]
    rows = [p["q2"] for p in selected]
    metrics = {name: probe.metrics(rows, vector) for name, vector in vectors.items()}
    strongest = max(("majority", "repeat_last", "markov_1", "phase_backoff"),
                    key=lambda n: (metrics[n]["accuracy_pct"], metrics[n]["macro_f1"]))
    margins = {name: metrics["q3"]["accuracy_pct"] - metrics[name]["accuracy_pct"]
               for name in (strongest, "q2", "shuffled")}
    gate = all(m >= 5 for m in margins.values()) and metrics["q3"]["macro_f1"] >= metrics[strongest]["macro_f1"]
    paired = {name: dict(q3_only=sum(a == r["target"] and b != r["target"] for r, a, b in zip(rows, vectors["q3"], vec)),
                        comparator_only=sum(a != r["target"] and b == r["target"] for r, a, b in zip(rows, vectors["q3"], vec)))
              for name, vec in vectors.items() if name != "q3"}
    return dict(model=refresh.MODEL, metrics=metrics, strongest_baseline=strongest, margins_pp=margins,
                exploratory_followup_signal=gate, paired=paired, collection=receipts,
                input_manifest_sha256=prep.digest(data / "manifest.json"),
                preflight_sha256=prep.digest(responses / "preflight.json"),
                scorer_sha256=prep.digest(Path(__file__)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("collect", "score"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--deadline", help="absolute UTC ISO timestamp, required for collection")
    args = parser.parse_args(argv)
    if args.mode == "collect":
        if not args.key_file or not args.deadline:
            parser.error("collect requires --key-file and --deadline")
        collect(args.data, args.out, args.key_file, datetime.fromisoformat(args.deadline))
    else:
        print(json.dumps(score(args.data, args.out), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
