"""GH-5 P3 -- LoRA fine-tuning of Needle on MLX (Apple GPU / Metal).

Semantics are taken from `needle/model/finetune.py::finetune_local`, not
re-derived. Anything that decides what the model is trained ON is imported from
the main lane so it cannot drift:

  * `needle.model.finetune.load_jsonl`  -> tokenisation, and therefore
    `render_example` (the chat template) and `_encode`'s prompt/target loss mask.
  * `needle.model.finetune.fit_max_len` -> the sequence-length bucket.
  * `needle.model.finetune.LORA_TARGETS`-> which projections get an adapter.

What is re-implemented here is only the part MLX has to own: the optimiser
schedule (optax has no MLX build) and the training step itself. Both are written
against the JAX source line-for-line and the reference is cited at each site.

SCOPE (GH-5 D6): this runs FULL PRECISION. The JAX baseline defaults to
`--qat-bits auto`, which on needle2.pkl resolves to
`CQ mixed[embedding=4,mhc=4,default=2] STE + A8`, so its loss is a
quantisation-aware objective and its curve is NOT directly comparable to this
one. Getting the fp32 loop stepping proves the backward pass through the port;
QAT is the following step. Do not report a curve from here against a QAT
baseline without saying so.
"""
import argparse
import json
import math
import os
import pickle
import sys
import time

import numpy as np
import mlx.core as mx
import mlx.nn as mlx_nn
import mlx.optimizers as mlx_opt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from san_mlx import SimpleAttentionNetworkMLX, normalize_config  # noqa: E402


# --- params as a flat dict ---------------------------------------------------
def flatten(tree, prefix=()):
    out = {}
    for k, v in tree.items():
        if isinstance(v, dict):
            out.update(flatten(v, prefix + (k,)))
        else:
            out[prefix + (k,)] = v
    return out


def unflatten(flat):
    out = {}
    for path, v in flat.items():
        node = out
        for k in path[:-1]:
            node = node.setdefault(k, {})
        node[path[-1]] = v
    return out


# --- LoRA --------------------------------------------------------------------
def lora_target_paths(flat, targets):
    """Mirror of finetune.py:254-263 -- stacked layer kernels for the 5 targets,
    minus any group that is entirely zero (max|W| <= 1e-6)."""
    paths = [p for p in flat
             if p[-1] == "kernel" and "stack" in p and "layers" in p
             and any(t in p for t in targets)]
    return [p for p in paths if float(np.max(np.abs(np.asarray(flat[p])))) > 1e-6]


def init_lora(flat, paths, rank, seed):
    """finetune.py:267-282. A ~ N(0,1)/rank, B = 0, both float32, both carrying
    the weight's leading (scan-stacked) dims."""
    rng = np.random.default_rng(seed)
    lora = {}
    for path in paths:
        w = np.asarray(flat[path])
        in_dim, out_dim = w.shape[-2], w.shape[-1]
        lead = w.shape[:-2]
        lora["/".join(path)] = {
            "A": mx.array((rng.standard_normal(lead + (in_dim, rank)) / rank).astype(np.float32)),
            "B": mx.zeros(lead + (rank, out_dim), dtype=mx.float32),
        }
    return lora


def merge_lora(base_mx, lora, scale):
    """finetune.py:285-292. W + (scale * A@B) cast back to W's dtype."""
    merged = dict(base_mx)
    for key, ad in lora.items():
        path = tuple(key.split("/"))
        w = merged[path]
        merged[path] = w + (scale * mx.matmul(ad["A"], ad["B"])).astype(w.dtype)
    return merged


# --- optimiser schedule ------------------------------------------------------
def warmup_cosine(step, peak, warmup, total, end=0.0):
    """optax.warmup_cosine_decay_schedule (finetune.py:371-374): linear 0->peak
    over `warmup`, then cosine peak->end over the remaining `total - warmup`."""
    if step < warmup:
        return peak * step / max(warmup, 1)
    span = max(total - warmup, 1)
    t = min((step - warmup) / span, 1.0)
    return end + (peak - end) * 0.5 * (1.0 + math.cos(math.pi * t))


def clip_by_global_norm(grads, max_norm=1.0):
    """optax.clip_by_global_norm(1.0) (finetune.py:375)."""
    leaves = [g for ad in grads.values() for g in ad.values()]
    total = mx.sqrt(sum(mx.sum(g.astype(mx.float32) ** 2) for g in leaves))
    factor = mx.minimum(1.0, max_norm / (total + 1e-6))
    return ({k: {n: g * factor for n, g in ad.items()} for k, ad in grads.items()},
            total)


def main():
    ap = argparse.ArgumentParser(description="GH-5 P3: LoRA fine-tune on MLX")
    ap.add_argument("jsonl_path")
    ap.add_argument("--checkpoint", default="checkpoints/needle2.pkl")
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lora-rank", type=int, default=16)
    ap.add_argument("--lora-alpha", type=float, default=32)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--val-split", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-steps", type=int, default=0, help="stop early (smoke test)")
    ap.add_argument("--out", default="data/spike-mlx/mlx-lora-adapter.pkl")
    ap.add_argument("--log-every", type=int, default=0, help="0 = match JAX (total/50)")
    ap.add_argument("--micro-batch", type=int, default=0,
                    help="gradient-accumulation micro-batch; 0 = no accumulation. "
                         "Keeps the effective batch (and so the loss curve) while "
                         "bounding activation memory.")
    ap.add_argument("--mem-limit-gb", type=float, default=12.0,
                    help="hard MLX allocation ceiling. MLX draws from unified memory "
                         "with no default ceiling, so an oversized run starves the "
                         "kernel and takes the MACHINE down rather than the process. "
                         "0 disables (do not).")
    ap.add_argument("--receipt", default="")
    args = ap.parse_args()

    from needle.model.finetune import (LORA_TARGETS, load_jsonl, fit_max_len)
    from needle.model.tokenizer import get_tokenizer
    from needle.model.run import load_checkpoint

    t_start = time.time()
    print(f"  {'device':<9} {mx.default_device()}", flush=True)

    if args.mem_limit_gb > 0:
        mx.set_memory_limit(int(args.mem_limit_gb * 2 ** 30))
        # MEASURED, do not trust this as a guarantee: with the cap at 12 GB a
        # micro-batch-2 step still peaked at 13.4 GB and MLX allocated straight
        # through without raising. The limit is advisory. The pre-flight estimate
        # below is the check that actually protects the host.
        print(f"  {'memcap':<9} {args.mem_limit_gb:.1f} GB (ADVISORY -- MLX has been "
              f"observed to exceed it; the pre-flight estimate is the real guard)", flush=True)

    params, config = load_checkpoint(args.checkpoint)
    cfg = normalize_config(dict(vars(config)) if not isinstance(config, dict) else dict(config))
    cfg["dtype"] = "float32"                      # finetune.py:315 -- train in fp32
    flat = {k: np.asarray(v).astype(np.float32) for k, v in flatten(params).items()}
    print(f"  {'backend':<9} mlx-gpu  float32", flush=True)

    tokenizer = get_tokenizer(cfg["vocab_size"])
    max_len = fit_max_len(args.jsonl_path, tokenizer, args.max_len)
    seqs, masks = load_jsonl(args.jsonl_path, tokenizer, max_len)
    if len(seqs) == 0:
        raise SystemExit("no usable examples in " + args.jsonl_path)
    print(f"  {'data':<9} {len(seqs)} examples  seq_len {max_len}  cap {args.max_len}", flush=True)

    # A row whose prompt alone exceeds max_len truncates before the target ever
    # starts, so its loss mask is all zeros and it teaches nothing. At
    # --max-len 512 that is EVERY row in the Oracle corpus (prompts embed all 44
    # tool schemas, ~1.5-1.9k tokens), and the run reports a clean "loss 0.0000"
    # while optimising nothing. Refuse rather than train on vacuum.
    supervised = masks.sum(axis=1)
    n_empty = int((supervised == 0).sum())
    if n_empty:
        pct = 100.0 * n_empty / len(masks)
        msg = (f"{n_empty}/{len(masks)} rows ({pct:.1f}%) have an all-zero loss mask at "
               f"seq_len {max_len} -- the target is truncated away and they teach nothing")
        if n_empty == len(masks):
            raise SystemExit("  refusing: " + msg + ". Raise --max-len.")
        print(f"  {'WARNING':<9} {msg}", flush=True)
    print(f"  {'masked':<9} median {float(np.median(supervised)):.0f} supervised tokens/row", flush=True)
    print(f"  {'numerics':<9} full precision (JAX baseline uses CQ STE -- curves not comparable)", flush=True)

    paths = lora_target_paths(flat, LORA_TARGETS)
    scale = args.lora_alpha / args.lora_rank
    lora = init_lora(flat, paths, args.lora_rank, args.seed)
    print(f"  {'lora':<9} rank {args.lora_rank}  alpha {args.lora_alpha:g}  {len(paths)} weight groups", flush=True)

    # holdout split -- finetune.py:359-365
    n_val = min(int(len(seqs) * args.val_split), len(seqs) - 1)
    val_seqs = val_masks = None
    if n_val > 0:
        order = np.random.default_rng(0).permutation(len(seqs))
        seqs, masks = seqs[order], masks[order]
        val_seqs, val_masks, seqs, masks = seqs[:n_val], masks[:n_val], seqs[n_val:], masks[n_val:]
        print(f"  {'holdout':<9} {n_val} examples for validation", flush=True)

    # Pre-flight: the dominant activation term is one [B, H, S, S] float32 score
    # matrix per layer, all retained for the backward pass. At batch 16 / seq 2048
    # on this 27-layer model that is ~54 GB -- more than twice a 24 GB machine --
    # and MLX will take the host down rather than fail. Refuse first, and say so.
    micro = args.micro_batch or args.batch_size
    scores_gb = (micro * cfg["num_heads"] * max_len * max_len * 4
                 * cfg["num_layers"]) / 2 ** 30
    # Attention scores are the dominant term but not the only one; MLP
    # intermediates, logits and the merged weight copies add roughly as much
    # again. Calibrated against a measured micro-batch-2 run: predicted 6.8 GB
    # of scores, observed 13.4 GB peak -> ~2.0x. Held at 2.64x: 2.2x with a
    # further 20% conservatism, on operator instruction, because the downside is
    # not a failed run but a downed host -- this has already happened once.
    OVERHEAD = 2.64
    est_gb = scores_gb * OVERHEAD
    print(f"  {'memest':<9} ~{scores_gb:.1f} GB attention scores -> ~{est_gb:.1f} GB "
          f"projected peak at micro-batch {micro} x seq {max_len}", flush=True)
    if args.mem_limit_gb > 0 and est_gb > args.mem_limit_gb:
        raise SystemExit(
            f"  refusing: projected peak {est_gb:.1f} GB exceeds the {args.mem_limit_gb:.1f} GB "
            f"budget. Lower --micro-batch (memory scales linearly in it) or raise "
            f"--mem-limit-gb only if the host truly has the headroom. Note the machine "
            f"has been taken down once by ignoring this.")

    batch, count = args.batch_size, len(seqs)
    steps_per_epoch = -(-count // batch)
    total_steps = args.epochs * steps_per_epoch
    warmup = min(max(1, total_steps // 20), max(total_steps - 1, 1))
    print(f"  {'schedule':<9} {total_steps} steps  warmup {warmup}  cosine decay  clip 1.0", flush=True)

    base_mx = {p: mx.array(w) for p, w in flat.items()}
    opt = mlx_opt.AdamW(learning_rate=args.lr)

    def loss_sum_fn(lora, ids, mask):
        """finetune.py:379-390 minus the QAT branch, returning the SUM of masked
        token losses rather than the mean.

        The JAX loss is  L = sum(ce*m) / sum(m)  over the whole batch, so
            dL/dw = [ sum over micro-batches of d(sum(ce*m))/dw ] / sum(m).
        Summing here and dividing once by the batch-wide token count at the end
        makes accumulation EXACTLY equal to the full-batch gradient -- which a
        per-micro-batch mean would not be, since micro-batches hold unequal
        numbers of supervised tokens.
        """
        merged = merge_lora(base_mx, lora, scale)
        model = SimpleAttentionNetworkMLX(unflatten(merged), cfg)
        logits = model.logits_mx(ids)
        logits, targets, m = logits[:, :-1], ids[:, 1:], mask[:, 1:]
        ce = mlx_nn.losses.cross_entropy(logits, targets, reduction="none")
        return (ce * m).sum()

    grad_sum_fn = mx.value_and_grad(loss_sum_fn)

    def eval_loss(lora, e_seqs, e_masks):
        """finetune.py:413-415 -- mean masked-token loss over the holdout, no
        gradient. Chunked at `micro` so the 200-row split doesn't retrigger the
        same [B,H,S,S] memory cost training was just bounded against."""
        if e_seqs is None or len(e_seqs) == 0:
            return None
        tot_loss, tot_tok = 0.0, 0.0
        for off in range(0, len(e_seqs), micro):
            ids = mx.array(e_seqs[off:off + micro].astype(np.int32))
            m = mx.array(e_masks[off:off + micro].astype(np.float32))
            tot_loss += float(loss_sum_fn(lora, ids, m))
            tot_tok += float(m[:, 1:].sum())
        return tot_loss / max(tot_tok, 1.0)

    def batch_grads(lora, b_ids, b_mask):
        """One optimiser step's gradient, over micro-batches if asked."""
        n = len(b_ids)
        step = micro if micro < n else n
        acc, tot_loss, tot_tok = None, 0.0, 0.0
        for off in range(0, n, step):
            ids = mx.array(b_ids[off:off + step].astype(np.int32))
            m = mx.array(b_mask[off:off + step].astype(np.float32))
            lsum, g = grad_sum_fn(lora, ids, m)
            ntok = float(m[:, 1:].sum())
            if acc is None:
                acc = g
            else:
                acc = {k: {n2: acc[k][n2] + v for n2, v in ad.items()}
                       for k, ad in g.items()}
            mx.eval(acc, lsum)
            tot_loss += float(lsum)
            tot_tok += ntok
        denom = max(tot_tok, 1.0)
        return ({k: {n2: v / denom for n2, v in ad.items()} for k, ad in acc.items()},
                tot_loss / denom)
    every = args.log_every or max(1, total_steps // 50)
    step_i, last, hist = 0, 0.0, []
    rng = np.random.default_rng(args.seed)

    for epoch in range(args.epochs):
        order = rng.permutation(count)
        for start in range(0, count, batch):
            idx = order[start:start + batch]
            t0 = time.time()
            grads, loss = batch_grads(lora, seqs[idx], masks[idx])
            grads, gnorm = clip_by_global_norm(grads, 1.0)
            opt.learning_rate = warmup_cosine(step_i, args.lr, warmup, total_steps)
            lora = opt.apply_gradients(grads, lora)
            mx.eval(lora)
            dt = time.time() - t0
            last, step_i = float(loss), step_i + 1
            hist.append({"step": step_i, "loss": last, "s": round(dt, 3),
                         "lr": round(float(opt.learning_rate), 8),
                         "gnorm": round(float(gnorm), 4)})
            if step_i % every == 0 or step_i == 1:
                print(f"  {'step':<9} {step_i}/{total_steps}  loss {last:.4f}"
                      f"  {dt:.1f}s  lr {float(opt.learning_rate):.2e}", flush=True)
            if args.max_steps and step_i >= args.max_steps:
                break
        if n_val > 0:
            val = eval_loss(lora, val_seqs, val_masks)
            print(f"  {'epoch':<9} {epoch + 1}/{args.epochs}  loss {last:.4f}  val {val:.4f}", flush=True)
        else:
            val = None
            print(f"  {'epoch':<9} {epoch + 1}/{args.epochs}  loss {last:.4f}", flush=True)
        if args.max_steps and step_i >= args.max_steps:
            break

    wall = time.time() - t_start
    steps_timed = [h["s"] for h in hist]
    med = float(np.median(steps_timed)) if steps_timed else 0.0
    peak_gb = mx.get_peak_memory() / 2 ** 30
    print(f"  {'done':<9} {step_i} steps  loss {last:.4f}  median {med:.2f} s/step"
          f"  wall {wall/60:.1f} min  peak {peak_gb:.1f} GB", flush=True)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "wb") as fh:
        pickle.dump({"lora": {k: {"A": np.asarray(v["A"]), "B": np.asarray(v["B"])}
                              for k, v in lora.items()},
                     "scale": scale, "rank": args.lora_rank,
                     "alpha": args.lora_alpha}, fh)
    print(f"  {'saved':<9} {args.out}", flush=True)

    if args.receipt:
        os.makedirs(os.path.dirname(args.receipt) or ".", exist_ok=True)
        with open(args.receipt, "w") as fh:
            json.dump({"gate": "P3", "runtime": "mlx-gpu", "numerics": "float32 (no QAT)",
                       "dataset": args.jsonl_path, "rows": int(count), "seq_len": int(max_len),
                       "batch_size": batch, "lora_rank": args.lora_rank,
                       "lora_alpha": args.lora_alpha, "lr": args.lr,
                       "steps_run": step_i, "total_steps": total_steps,
                       "final_loss": last, "final_val_loss": val, "median_s_per_step": med,
                       "micro_batch": micro, "peak_gb": round(peak_gb, 2),
                       "mem_limit_gb": args.mem_limit_gb,
                       "wall_seconds": round(wall, 1), "history": hist}, fh, indent=2)
        print(f"  {'receipt':<9} {args.receipt}", flush=True)


if __name__ == "__main__":
    main()
