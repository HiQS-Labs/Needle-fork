"""#1 §5 -- top-1 / top-3 evaluation of the Oracle, scored on MLX.

WHY MLX AND NOT run.py: measured, JAX/CPU generation costs 223 s/row
(670.3 s for 3 holdout rows, max_new_tokens=24, prompts ~1,650 tokens). A
few hundred rows is days. Scoring runs on the MLX port instead, which does a
batched forward at a fraction of that.

HOW A LABEL IS RANKED: the 44 labels cannot be ranked by first token -- they
share only 31 distinct first tokens, with six colliding on one. So every
candidate is scored properly: teacher-force `prompt + <tool_call>[{"name":
"<label>"}]</tool_call><|im_end|>` and take the log-probability of the target
tokens. #1 §5 asks for "per-label sequence probability"; this is it.

Both a SUM and a MEAN ranking are reported. Sum is the true sequence
log-probability but favours short labels; mean normalises but favours long
ones. Reporting both makes the length bias visible instead of silently
choosing one.

CAVEAT, stated because it differs from the deployed path: candidates are
scored with an EMPTY reasoning block, so this measures P(label | prompt)
directly. The hook generates a <think> block first. Using the corpus's gold
reasoning would leak the answer, and generating one costs a forward pass per
row, so neither is right for ranking. The gap is constant across any two
models scored this way, so a DELTA (e.g. fp32 vs quantised) is unaffected;
an ABSOLUTE number against the static baseline carries this caveat.
"""
import argparse, json, os, pickle, random, sys, time
import numpy as np
import mlx.core as mx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from san_mlx import SimpleAttentionNetworkMLX, normalize_config          # noqa: E402
from train_lora import flatten, unflatten, merge_lora                     # noqa: E402


def load_rows(path, n, seed):
    """Reservoir-sample n rows without holding a 164 MB file in memory."""
    rng = random.Random(seed)
    keep = []
    with open(path) as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            if len(keep) < n:
                keep.append(line)
            else:
                j = rng.randrange(i + 1)
                if j < n:
                    keep[j] = line
    return [json.loads(x) for x in keep], i + 1


def main():
    ap = argparse.ArgumentParser(description="#1 §5: top-1/top-3 on MLX")
    ap.add_argument("--holdout", default="data/corpus-studio/oracle-holdout.jsonl")
    ap.add_argument("--labels", default="oracle/labels-v1.json")
    ap.add_argument("--checkpoint", default="checkpoints/needle2.pkl")
    ap.add_argument("--adapter", default="")
    ap.add_argument("--rows", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--micro-batch", type=int, default=4)
    ap.add_argument("--mem-limit-gb", type=float, default=11.0)
    ap.add_argument("--receipt", default="")
    ap.add_argument("--qat", action="store_true",
                    help="score under DEPLOYMENT numerics: the checkpoint's CQ scheme on the "
                         "merged weights + A8 activations (what needle build exports). Without "
                         "this the fp32 number is one the hook cannot deliver (D7).")
    args = ap.parse_args()

    from needle.model.finetune import render_example
    from needle.model.tokenizer import get_tokenizer, BOS_ID, EOS_ID
    from needle.model.run import load_checkpoint

    t_start = time.time()
    if args.mem_limit_gb > 0:
        mx.set_memory_limit(int(args.mem_limit_gb * 2 ** 30))
    print(f"  {'device':<10} {mx.default_device()}", flush=True)

    schema = json.load(open(args.labels))
    # oracle/labels-v1.json carries `labels` (a dict keyed by name) and
    # `schemas` (the build_schema list). Either gives the name set.
    labels = sorted(schema["labels"]) if isinstance(schema.get("labels"), dict) \
        else sorted({t["name"] for t in schema["schemas"]})
    print(f"  {'labels':<10} {len(labels)}", flush=True)

    params, config = load_checkpoint(args.checkpoint)
    cfg = normalize_config(dict(vars(config)))
    cfg["dtype"] = "float32"
    flat = {k: np.asarray(v).astype(np.float32) for k, v in flatten(params).items()}
    base = {p: mx.array(w) for p, w in flat.items()}

    tag = "base"
    if args.adapter:
        ad = pickle.load(open(args.adapter, "rb"))
        lora = {k: {"A": mx.array(np.asarray(v["A"], np.float32)),
                    "B": mx.array(np.asarray(v["B"], np.float32))}
                for k, v in ad["lora"].items()}
        base = merge_lora(base, lora, ad["scale"])
        tag = os.path.basename(args.adapter)
        print(f"  {'adapter':<10} {tag}  {len(lora)} groups  "
              f"numerics={ad.get('trained_numerics')}", flush=True)
    numerics = "float32"
    if args.qat:
        import quant_mlx as QM
        wb = getattr(config, "weight_bits", "") or None
        plan = QM.ste_plan(params, wb)
        delta = QM.ste_delta(base, plan); mx.eval(*delta.values())
        base = {k: (v + delta[k]) if k in delta else v for k, v in base.items()}
        numerics = QM.describe(plan, wb)
        print(f"  {'numerics':<10} {numerics} -- deployment numerics, {len(plan)} leaves", flush=True)
    model = SimpleAttentionNetworkMLX(unflatten(base), cfg, quant=args.qat)

    tok = get_tokenizer(cfg["vocab_size"])
    rows, total = load_rows(args.holdout, args.rows, args.seed)
    print(f"  {'holdout':<10} {len(rows)} sampled of {total} (seed {args.seed})", flush=True)

    # Per-candidate target token ids. The prompt is shared, so build once.
    cand_ids = {}
    for lab in labels:
        _, tgt = render_example({"query": "x", "tools": [], "reasoning": "",
                                 "answers": [{"name": lab}]})
        cand_ids[lab] = tok.encode(tgt) + [EOS_ID]

    hit1 = hit3 = 0
    hit1_mean = hit3_mean = 0
    per_label = {}
    skipped = 0
    step_times = []

    for ri, row in enumerate(rows):
        gold = row["answers"][0]["name"] if row.get("answers") else None
        if gold not in cand_ids:
            skipped += 1
            continue
        prompt, _ = render_example({**row, "reasoning": "", "answers": [{"name": labels[0]}]})
        p_ids = [BOS_ID] + tok.encode(prompt)
        cap = cfg["max_seq_len"]
        seqs, spans = [], []
        for lab in labels:
            ids = (p_ids + cand_ids[lab])[:cap]
            spans.append((len(p_ids) - 1, len(ids) - 1))   # predict-target positions
            seqs.append(ids)
        width = max(len(s) for s in seqs)
        arr = np.zeros((len(seqs), width), np.int32)
        for i, s in enumerate(seqs):
            arr[i, :len(s)] = s

        t0 = time.time()
        sums, means = [], []
        for off in range(0, len(seqs), args.micro_batch):
            chunk = mx.array(arr[off:off + args.micro_batch])
            lg = model.logits_mx(chunk)
            lp = lg - mx.logsumexp(lg, axis=-1, keepdims=True)
            mx.eval(lp)
            lp = np.asarray(lp, np.float32)
            for k in range(lp.shape[0]):
                a, b = spans[off + k]
                tgt = arr[off + k, a + 1:b + 1]
                got = lp[k, a:b, :][np.arange(b - a), tgt]
                sums.append(float(got.sum()))
                means.append(float(got.mean()))
        step_times.append(time.time() - t0)

        order_s = np.argsort(sums)[::-1]
        order_m = np.argsort(means)[::-1]
        top3_s = [labels[i] for i in order_s[:3]]
        top3_m = [labels[i] for i in order_m[:3]]
        rec = per_label.setdefault(gold, {"n": 0, "top1": 0, "top3": 0})
        rec["n"] += 1
        if top3_s[0] == gold:
            hit1 += 1; rec["top1"] += 1
        if gold in top3_s:
            hit3 += 1; rec["top3"] += 1
        if top3_m[0] == gold:
            hit1_mean += 1
        if gold in top3_m:
            hit3_mean += 1
        if (ri + 1) % 10 == 0:
            n = ri + 1 - skipped
            print(f"  {'progress':<10} {ri+1}/{len(rows)}  top1 {100*hit1/max(n,1):.1f}%"
                  f"  top3 {100*hit3/max(n,1):.1f}%  {np.median(step_times):.1f} s/row", flush=True)

    n = len(rows) - skipped
    res = {
        "adapter": tag, "rows_scored": n, "rows_skipped": skipped,
        "holdout": args.holdout, "holdout_total": total, "seed": args.seed,
        "top1_sum": 100 * hit1 / max(n, 1), "top3_sum": 100 * hit3 / max(n, 1),
        "top1_mean": 100 * hit1_mean / max(n, 1), "top3_mean": 100 * hit3_mean / max(n, 1),
        "median_s_per_row": float(np.median(step_times)) if step_times else 0.0,
        "wall_seconds": round(time.time() - t_start, 1),
        "peak_gb": round(mx.get_peak_memory() / 2 ** 30, 2),
        "scoring": "teacher-forced per-label sequence logprob, empty reasoning",
        "numerics": numerics,
        "per_label": per_label,
    }
    print(f"\n  {'TOP-1':<10} {res['top1_sum']:.2f}%   (mean-normalised: {res['top1_mean']:.2f}%)")
    print(f"  {'TOP-3':<10} {res['top3_sum']:.2f}%   (mean-normalised: {res['top3_mean']:.2f}%)")
    print(f"  {'scored':<10} {n} rows, {skipped} skipped, "
          f"{res['median_s_per_row']:.1f} s/row, peak {res['peak_gb']} GB")
    if args.receipt:
        os.makedirs(os.path.dirname(args.receipt) or ".", exist_ok=True)
        json.dump(res, open(args.receipt, "w"), indent=2)
        print(f"  {'receipt':<10} {args.receipt}")


if __name__ == "__main__":
    main()
