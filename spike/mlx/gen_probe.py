"""Greedy GENERATION on MLX -- the same task the native engine performs.

eval_oracle.py ranks 44 candidates with an empty reasoning block: P(label|prompt).
The engine instead generates `<think>LAST: X -> Y</think><tool_call>[{"name":"Y"}]`
unaided. Those are different tasks, and the 19%-vs-3% gap may be entirely that.

This runs the ENGINE's task on MLX with the SAME weights and numerics, so:
  MLX-generation ~ engine  => the engine is fine; the model just can't generate it.
  MLX-generation >> engine => the gap is engine-side (prompt assembly or decode).
"""
import argparse, json, os, pickle, random, re, sys, time
import numpy as np, mlx.core as mx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath("."))
from san_mlx import SimpleAttentionNetworkMLX, normalize_config          # noqa: E402
from train_lora import flatten, unflatten, merge_lora                    # noqa: E402
from needle.model.run import load_checkpoint                             # noqa: E402
from needle.model.tokenizer import get_tokenizer, BOS_ID, EOS_ID         # noqa: E402
from needle.model.finetune import render_example                         # noqa: E402
from eval_oracle import load_rows                                        # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--checkpoint", default="checkpoints/needle2.pkl")
ap.add_argument("--adapter", default="")
ap.add_argument("--qat", action="store_true")
ap.add_argument("--rows", type=int, default=60)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--max-new", type=int, default=48)
ap.add_argument("--receipt", default="")
a = ap.parse_args()

params, config = load_checkpoint(a.checkpoint)
cfg = normalize_config(dict(vars(config))); cfg["dtype"] = "float32"
base = {p: mx.array(w) for p, w in
        {k: np.asarray(v).astype(np.float32) for k, v in flatten(params).items()}.items()}
tag = "base"
if a.adapter:
    ad = pickle.load(open(a.adapter, "rb"))
    lora = {k: {"A": mx.array(np.asarray(v["A"], np.float32)),
                "B": mx.array(np.asarray(v["B"], np.float32))} for k, v in ad["lora"].items()}
    base = merge_lora(base, lora, ad["scale"]); tag = os.path.basename(a.adapter)
if a.qat:
    import quant_mlx as QM
    wb = getattr(config, "weight_bits", "") or None
    plan = QM.ste_plan(params, wb); delta = QM.ste_delta(base, plan); mx.eval(*delta.values())
    base = {k: (v + delta[k]) if k in delta else v for k, v in base.items()}
model = SimpleAttentionNetworkMLX(unflatten(base), cfg, quant=a.qat)
tok = get_tokenizer(cfg["vocab_size"])
labels = sorted(json.load(open("oracle/labels-v1.json"))["labels"])
rows, _ = load_rows("data/corpus-studio/oracle-holdout.jsonl", a.rows, a.seed)

NAME = re.compile(r'"name"\s*:\s*"([a-z_]+)"')
n = correct = parsed = think_ok = 0
t0 = time.time()
for r in rows:
    gold = r["answers"][0]["name"] if r.get("answers") else None
    if gold not in labels: continue
    n += 1
    prompt, _ = render_example(r)
    ids = [BOS_ID] + tok.encode(prompt)
    out_ids = []
    for _ in range(a.max_new):
        lg = model.logits_mx(mx.array([ids + out_ids]))
        nxt = int(mx.argmax(lg[0, -1]).item())
        if nxt == EOS_ID: break
        out_ids.append(nxt)
    text = tok.decode(out_ids)
    m = NAME.search(text)
    pred = m.group(1) if m else None
    if pred: parsed += 1
    if "</think>" in text or "<think>" in text: think_ok += 1
    if pred == gold: correct += 1
    if n <= 3:
        print(f"  gold={gold}\n    gen={text[:160]!r}\n    pred={pred}", flush=True)
    if n % 20 == 0:
        print(f"  {n}/{len(rows)}  top1 {100*correct/n:.1f}%  parsed {100*parsed/n:.1f}%", flush=True)

res = {"adapter": tag, "qat": a.qat, "rows": n, "top1": 100*correct/max(n,1),
       "parse_rate": 100*parsed/max(n,1), "emitted_think": 100*think_ok/max(n,1),
       "wall_s": round(time.time()-t0,1), "note": "greedy MLX generation, the engine's task"}
print(f"\n  adapter    {tag}  qat={a.qat}")
print(f"  TOP-1      {res['top1']:.2f}%   (MLX ranking on same weights: see eval_oracle)")
print(f"  parse rate {res['parse_rate']:.2f}%   emitted think block {res['emitted_think']:.1f}%")
if a.receipt:
    os.makedirs(os.path.dirname(a.receipt) or ".", exist_ok=True)
    json.dump(res, open(a.receipt, "w"), indent=2); print(f"  receipt    {a.receipt}")
