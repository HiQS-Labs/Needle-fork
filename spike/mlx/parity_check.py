#!/usr/bin/env python3
"""GH-5 P1/P2 parity harness: JAX reference vs the MLX port, same weights, same tokens.

    python3 spike/mlx/parity_check.py --tiny                        # random-init tiny config (no download)
    python3 spike/mlx/parity_check.py --checkpoint checkpoints/needle2.pkl

The JAX side is complete and is the reference. The MLX side (`san_mlx.py`) raises
NotImplementedError per block until ported; this script reports which block, so the
port proceeds one block at a time with a passing check after each.

Pass criterion is stated, not assumed: max |Δlogits| <= --atol (default 1e-4 for fp32)
AND argmax agreement == 100% on every position. Both are written to the receipt.
"""
from __future__ import annotations
import argparse
import json
import os
import pickle
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

# Same tiny config as tests/conftest.py::tiny_checkpoint, so P1 needs no download.
TINY = dict(vocab_size=8192, d_model=64, num_heads=4, num_kv_heads=2, num_layers=2,
            max_seq_len=128, engram_layers=(1,), engram_slots=64, mhc_lanes=2, flash=False)


def tiny_checkpoint(seed: int = 0) -> dict:
    import numpy as np, jax, jax.numpy as jnp
    from needle.model.architecture import SimpleAttentionNetwork, TransformerConfig
    config = TransformerConfig(**TINY)
    model = SimpleAttentionNetwork(config)
    params = model.init(jax.random.PRNGKey(seed), jnp.ones((1, 8), jnp.int32))["params"]
    params = jax.tree_util.tree_map(lambda x: np.asarray(x), params)
    return {"format_version": 2, "params": params, "config": dict(vars(config))}


def load(path: str | None, tiny: bool) -> dict:
    if tiny:
        return tiny_checkpoint()
    with open(path, "rb") as fh:
        ckpt = pickle.load(fh)
    if ckpt.get("format_version") != 2:
        raise SystemExit(f"unexpected checkpoint format_version={ckpt.get('format_version')!r}")
    return ckpt


def fixed_batches(vocab: int, seq: int, n: int, seed: int = 1234):
    import numpy as np
    rng = np.random.default_rng(seed)
    return [rng.integers(1, vocab, size=(2, seq), dtype=np.int32) for _ in range(n)]


def jax_logits(ckpt: dict, tokens):
    import jax.numpy as jnp, numpy as np
    from needle.model.architecture import SimpleAttentionNetwork, TransformerConfig
    config = TransformerConfig(**ckpt["config"])
    model = SimpleAttentionNetwork(config)
    out = model.apply({"params": ckpt["params"]}, jnp.asarray(tokens))
    logits = out[0] if isinstance(out, (tuple, list)) else out
    return np.asarray(logits, dtype=np.float32)


def mlx_logits(ckpt: dict, tokens):
    import numpy as np
    import san_mlx  # the port target; raises NotImplementedError per unported block
    model = san_mlx.from_checkpoint(ckpt)
    return np.asarray(model.logits(tokens), dtype=np.float32)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--tiny", action="store_true")
    ap.add_argument("--seq", type=int, default=32)
    ap.add_argument("--batches", type=int, default=4)
    ap.add_argument("--atol", type=float, default=1e-4)
    ap.add_argument("--receipt", default=None, help="write JSON receipt here (aggregates only)")
    args = ap.parse_args()
    if not (args.tiny or args.checkpoint):
        ap.error("pass --tiny or --checkpoint")

    import numpy as np
    ckpt = load(args.checkpoint, args.tiny)
    vocab = int(ckpt["config"]["vocab_size"])
    seq = min(args.seq, int(ckpt["config"]["max_seq_len"]))
    batches = fixed_batches(vocab, seq, args.batches)

    t0 = time.perf_counter()
    ref = [jax_logits(ckpt, b) for b in batches]
    t_jax = time.perf_counter() - t0
    print(f"JAX reference: {len(ref)} batches x {ref[0].shape} in {t_jax*1000:.0f} ms")

    result = {"source": "tiny" if args.tiny else os.path.basename(args.checkpoint),
              "config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in ckpt["config"].items()},
              "seq": seq, "batches": args.batches, "atol": args.atol,
              "jax_ms": round(t_jax * 1000, 1)}
    try:
        t0 = time.perf_counter()
        got = [mlx_logits(ckpt, b) for b in batches]
        t_mlx = time.perf_counter() - t0
    except NotImplementedError as exc:
        print(f"MLX side not ported yet: {exc}")
        result.update(status="NOT_PORTED", blocker=str(exc))
        _write(args.receipt, result)
        return 3

    max_abs = max(float(np.max(np.abs(a - b))) for a, b in zip(ref, got))
    agree = float(np.mean([np.mean(np.argmax(a, -1) == np.argmax(b, -1)) for a, b in zip(ref, got)]))
    ok = max_abs <= args.atol and agree == 1.0
    result.update(status="PASS" if ok else "FAIL", max_abs_delta=max_abs,
                  argmax_agreement=agree, mlx_ms=round(t_mlx * 1000, 1))
    print(f"max |Δlogits| = {max_abs:.3e}  argmax agreement = {agree:.4f}  -> {result['status']}")
    _write(args.receipt, result)
    return 0 if ok else 1


def _write(path, result):
    if path:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as fh:
            json.dump(result, fh, indent=2)
        print(f"receipt: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
