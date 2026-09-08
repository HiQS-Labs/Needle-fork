"""QAT parity: MLX (weight STE + A8) vs JAX `quant=True` -- the gate on training under QAT.

Same shape as parity_check.py, but the reference is what `needle finetune --qat-bits auto`
actually computes: `configure_deploy(act_bits=8, kv_bits=8)` (KV quant OFF at 8 bits),
weights through `cq_ste_mixed_params` / `cq_ste_params`, and `model.apply(..., quant=True)`
so `_aq` fires at all four activation sites. The STE's forward IS the quantised value, so
forward parity here proves the MLX quantiser matches JAX's op for op -- including the
codebook, the Hadamard rotation, the fp16 round-trip on the norm, and the tie rule.

    python3 spike/mlx/parity_qat.py --tiny
    python3 spike/mlx/parity_qat.py --checkpoint checkpoints/needle2.pkl --seq 64
"""
import argparse, json, os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parity_check import tiny_checkpoint, load, fixed_batches            # noqa: E402
from san_mlx import SimpleAttentionNetworkMLX, normalize_config           # noqa: E402
from train_lora import flatten, unflatten                                  # noqa: E402
import quant_mlx as QM                                                     # noqa: E402


def jax_qat_logits(ckpt, tokens, weight_bits):
    import jax, jax.numpy as jnp
    from needle.model.architecture import SimpleAttentionNetwork, TransformerConfig
    from needle.model import quantize as Q
    cfg = TransformerConfig(**{**ckpt["config"], "dtype": "float32"})
    params = jax.tree.map(lambda a: jnp.asarray(np.asarray(a, np.float32)), ckpt["params"])
    Q.configure_deploy(act_bits=8, kv_bits=8)                                # finetune.py:348-349
    if weight_bits:
        bits_map, default = Q.parse_bits_map(weight_bits)
        params = Q.cq_ste_mixed_params(params, bits_map, default)           # finetune.py:381-383
    else:
        params = Q.cq_ste_params(params, 4)                                  # finetune.py:384-385
    model = SimpleAttentionNetwork(cfg)
    return np.asarray(model.apply({"params": params}, jnp.asarray(tokens), quant=True), np.float32)


def mlx_qat_logits(ckpt, tokens, weight_bits):
    import mlx.core as mx
    cfg = normalize_config(dict(ckpt["config"])); cfg["dtype"] = "float32"
    flat = {k: mx.array(np.asarray(v, np.float32)) for k, v in flatten(ckpt["params"]).items()}
    plan = QM.ste_plan(ckpt["params"], weight_bits)
    flat = QM.apply_weight_ste(flat, plan)
    model = SimpleAttentionNetworkMLX(unflatten(flat), cfg, quant=True)
    return model.logits(tokens), len(plan)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint"); ap.add_argument("--tiny", action="store_true")
    ap.add_argument("--seq", type=int, default=32); ap.add_argument("--batches", type=int, default=2)
    ap.add_argument("--rtol", type=float, default=1e-4); ap.add_argument("--receipt", default="")
    a = ap.parse_args()
    if not (a.tiny or a.checkpoint):
        ap.error("pass --tiny or --checkpoint")
    ckpt = load(a.checkpoint, a.tiny)
    weight_bits = ckpt["config"].get("weight_bits") or None
    vocab = ckpt["config"]["vocab_size"]
    worst_abs = worst_rel = 0.0; agree1 = agree3 = tot = 0; nq = 0
    t0 = time.time()
    for toks in fixed_batches(vocab, a.seq, a.batches):
        ref = jax_qat_logits(ckpt, toks, weight_bits)
        out, nq = mlx_qat_logits(ckpt, toks, weight_bits)
        d = np.abs(out - ref); worst_abs = max(worst_abs, float(d.max()))
        worst_rel = max(worst_rel, float(d.max() / (np.abs(ref).max() + 1e-12)))
        r1, o1 = ref.argmax(-1), out.argmax(-1); agree1 += int((r1 == o1).sum()); tot += r1.size
        r3 = np.argsort(-ref, -1)[..., :3]; o3 = np.argsort(-out, -1)[..., :3]
        agree3 += int(sum(len(set(x) & set(y)) == 3 for x, y in zip(r3.reshape(-1, 3), o3.reshape(-1, 3))))
    verdict = "PASS" if worst_rel <= a.rtol else "FAIL"
    scheme = f"mixed[{weight_bits}]" if weight_bits else "W4"
    print(f"scheme {scheme} + A8   quantised leaves {nq}   seq {a.seq} x {a.batches} batches   {time.time()-t0:.1f}s")
    print(f"max |Δlogits| = {worst_abs:.3e}   relative = {worst_rel:.3e}   argmax {agree1/tot:.4f}   top-3 {agree3/tot:.4f}")
    print(f"gate rel {a.rtol:g} -> {verdict}")
    if a.receipt:
        json.dump({"scheme": scheme, "quantised_leaves": nq, "seq": a.seq, "batches": a.batches,
                   "max_abs": worst_abs, "max_rel": worst_rel, "argmax": agree1/tot, "top3": agree3/tot,
                   "rtol": a.rtol, "verdict": verdict}, open(a.receipt, "w"), indent=2)
    return 0 if verdict == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
