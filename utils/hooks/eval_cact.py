#!/usr/bin/env python3
"""#1 §5: evaluate the EXPORTED .cact through the native engine -- the artifact the hook ships.

Different from spike/mlx/eval_oracle.py on purpose: that scores 44 candidates by
sequence probability on the fp32 MLX model (a ranking); this runs the real
deployed path -- native engine, quantised weights, generate-then-parse, one
answer or an abstention. Whatever number this reports is the number the hook
will actually deliver.

Reports three things the hook design turns on:
  answer rate   -- how often the engine commits to a label vs returns []
  precision     -- top-1 accuracy WHEN it answers (the "usable daily" number)
  top-1 overall -- comparable to the MLX fp32 figure (24.1%), so the gap is the
                   cost of PTQ + the generate path

Same 200 rows as the MLX eval: reservoir sample, seed 0, so the columns compare.
Read-only; prints aggregates; writes a receipt if asked.
"""
import argparse, json, os, random, time, warnings

def load_rows(path, n, seed):
    rng = random.Random(seed); keep = []; i = -1
    with open(path) as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line: continue
            if len(keep) < n: keep.append(line)
            else:
                j = rng.randrange(i + 1)
                if j < n: keep[j] = line
    return [json.loads(x) for x in keep], i + 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cact", required=True)
    ap.add_argument("--holdout", default="data/corpus-studio/oracle-holdout.jsonl")
    ap.add_argument("--labels", default="oracle/labels-v1.json")
    ap.add_argument("--rows", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument("--receipt", default="")
    args = ap.parse_args()

    os.environ.setdefault("HF_HUB_DISABLE_XET", "1"); os.environ.setdefault("NEEDLE_TELEMETRY", "0")
    warnings.filterwarnings("ignore")
    import needle
    schema = json.load(open(args.labels))
    # BYTE-IDENTICAL to training. render_example (finetune.py:196) serialises the
    # tool list with separators=(",", ":") and ensure_ascii=False; the SDK passes
    # this string to the engine verbatim (needle/__init__.py:165-166). Default
    # json.dumps separators put a space after every comma and colon -- ~1,400
    # schema tokens per prompt shift, and the model sees an out-of-distribution
    # prompt. The first run of this script made exactly that mistake.
    tools = json.dumps(schema["schemas"], separators=(",", ":"), ensure_ascii=False)
    labels = set(schema["labels"])
    rows, total = load_rows(args.holdout, args.rows, args.seed)

    engines = {}
    def engine(system):
        key = system or ""
        if key not in engines:
            engines[key] = needle.Needle(tools=tools, system=system or None, weights=args.cact)
        return engines[key]

    t_start = time.time(); lat = []
    n = answered = correct = invalid = 0
    per = {}
    for r in rows:
        gold = r["answers"][0]["name"] if r.get("answers") else None
        if gold not in labels: continue
        n += 1
        t = time.time()
        try:
            out = engine(r.get("system")).complete(r["query"], max_new_tokens=args.max_new_tokens)
            calls = out.get("function_calls") or []
        except Exception:
            calls = []; invalid += 1
        lat.append(time.time() - t)
        pred = calls[0].get("name") if calls else None
        rec = per.setdefault(gold, {"n": 0, "answered": 0, "correct": 0}); rec["n"] += 1
        if pred is not None:
            answered += 1; rec["answered"] += 1
            if pred not in labels: invalid += 1
            if pred == gold: correct += 1; rec["correct"] += 1
        if n % 25 == 0:
            print(f"  {n}/{len(rows)}  answer-rate {100*answered/n:.1f}%  "
                  f"precision {100*correct/max(answered,1):.1f}%  top1 {100*correct/n:.1f}%  "
                  f"median {sorted(lat)[len(lat)//2]:.2f}s", flush=True)
    for e in engines.values():
        try: e.close()
        except Exception: pass

    lat.sort(); med = lat[len(lat)//2] if lat else 0
    res = {"cact": args.cact, "rows_scored": n, "holdout_total": total, "seed": args.seed,
           "answer_rate": 100*answered/max(n,1), "precision_when_answering": 100*correct/max(answered,1),
           "top1_overall": 100*correct/max(n,1), "invalid_outputs": invalid,
           "median_s": med, "p90_s": lat[int(len(lat)*.9)] if lat else 0,
           "wall_s": round(time.time()-t_start,1), "per_label": per,
           "note": "native engine, quantised .cact, generate-then-parse; compare top1_overall to MLX fp32 24.1%"}
    print(f"\n  answer rate  {res['answer_rate']:.2f}%   ({answered}/{n})")
    print(f"  PRECISION    {res['precision_when_answering']:.2f}%   when it answers")
    print(f"  top-1        {res['top1_overall']:.2f}%   overall  (MLX fp32 ranking: 24.1%)")
    print(f"  latency      median {med:.2f}s  p90 {res['p90_s']:.2f}s   invalid {invalid}")
    if args.receipt:
        os.makedirs(os.path.dirname(args.receipt) or ".", exist_ok=True)
        json.dump(res, open(args.receipt, "w"), indent=2); print(f"  receipt      {args.receipt}")

if __name__ == "__main__":
    main()
