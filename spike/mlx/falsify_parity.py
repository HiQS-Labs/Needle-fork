#!/usr/bin/env python3
"""GH-5: prove the P1 parity check can FAIL before trusting that it passes.

`AGENTS.md` §6: *"A check that cannot fail is not a check... mutate the thing it
guards -- break the code, transpose the fix, delete the value -- and watch it go red.
If you cannot make it fail, it is decorative."*

A parity harness is exactly the kind of check that can be silently vacuous: if the MLX
side accidentally returned the JAX result, or if both sides collapsed to the same
degenerate output, max|Δ| would be ~0 and the gate would read PASS forever. So this
injects known faults into the MLX side only and reports the resulting delta.

    python3 spike/mlx/falsify_parity.py

Runs in float32 (the dtype the 1e-4 tolerance is written for). A fault is CAUGHT when
the delta exceeds --atol. A fault that is NOT caught is reported as a real sensitivity
gap in the harness, not hidden.
"""
from __future__ import annotations
import argparse, copy, json, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from parity_check import tiny_checkpoint, fixed_batches, jax_logits, mlx_logits  # noqa: E402
import san_mlx  # noqa: E402


def delta(ckpt, batches) -> float:
    ref = [jax_logits(ckpt, b) for b in batches]
    got = [mlx_logits(ckpt, b) for b in batches]
    return max(float(np.max(np.abs(a - b))) for a, b in zip(ref, got))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--atol", type=float, default=1e-4)
    ap.add_argument("--rtol", type=float, default=None,
                    help="use a RELATIVE threshold instead of --atol. Required on the real "
                         "checkpoint, whose logits reach ~7e3 and where an absolute 1e-4 is "
                         "below fp32 machine epsilon.")
    ap.add_argument("--checkpoint", default=None,
                    help="real checkpoint to falsify against; default is the tiny fixture")
    ap.add_argument("--seq", type=int, default=32)
    ap.add_argument("--batches", type=int, default=2)
    ap.add_argument("--receipt", default=None)
    args = ap.parse_args()

    if args.checkpoint:
        import pickle
        with open(args.checkpoint, "rb") as fh:
            ckpt = pickle.load(fh)
    else:
        ckpt = tiny_checkpoint()
    ckpt["config"] = dict(ckpt["config"])
    ckpt["config"]["dtype"] = "float32"
    batches = fixed_batches(int(ckpt["config"]["vocab_size"]), args.seq, args.batches)

    # Scale the threshold to the model's own logit magnitude when --rtol is given.
    if args.rtol is not None:
        _ref = jax_logits(ckpt, batches[0])
        _scale = float(np.max(np.abs(_ref)))
        args.atol = args.rtol * _scale
        print(f"logit scale {_scale:.4g}; rtol {args.rtol:g} -> effective atol {args.atol:.4g}")

    clean = delta(ckpt, batches)
    print(f"clean                         max|d| = {clean:.3e}   (baseline, must be <= atol)")

    faults, results = [], []

    # Control: perturbing a weight BOTH sides read must NOT move the delta. If it does,
    # the two sides are not reading the same weights and every other result is suspect.
    ctrl = copy.deepcopy(ckpt)
    ctrl["params"]["stack"]["layers"]["block"]["self_attn"]["q_proj"]["kernel"][0, 0, 0] += 0.05
    d = delta(ctrl, batches)
    print(f"[control] shared weight +0.05 max|d| = {d:.3e}   (expect ~clean: same weights both sides)")
    results.append({"fault": "control:shared_weight_perturbation", "delta": d,
                    "caught": None, "expect": "unchanged"})

    def inject(name, attr, replacement):
        original = getattr(san_mlx, attr)
        setattr(san_mlx, attr, replacement(original))
        try:
            d = delta(ckpt, batches)
        finally:
            setattr(san_mlx, attr, original)
        caught = d > args.atol
        print(f"{name:29s} max|d| = {d:.3e}   -> {'CAUGHT' if caught else 'NOT CAUGHT'}")
        results.append({"fault": name.strip(), "delta": d, "caught": caught})
        return caught

    inject("rope: sin sign flipped", "apply_rope",
           lambda o: (lambda x, cos, sin: o(x, cos, -sin)))
    inject("engram: indices shifted +1", "engram_indices",
           lambda o: (lambda t, ords, h, s: o(t, ords, h, s) + 1))
    inject("rms_unit: epsilon 1e-6->1e-2", "_rms_unit",
           lambda o: (lambda x, epsilon=1e-6: o(x, epsilon=1e-2)))
    inject("sinkhorn: 20 -> 3 iters", "_sinkhorn",
           lambda o: (lambda l, iters=20: o(l, iters=3)))

    injected = [r for r in results if r.get("caught") is not None]
    caught = sum(1 for r in injected if r["caught"])
    print(f"\n{caught}/{len(injected)} injected faults caught at atol={args.atol:g}")
    missed = [r["fault"] for r in injected if not r["caught"]]
    if missed:
        print("NOT caught (a real sensitivity gap in the harness, recorded not hidden):")
        for m in missed:
            print(f"  - {m}")

    if args.receipt:
        os.makedirs(os.path.dirname(args.receipt) or ".", exist_ok=True)
        with open(args.receipt, "w") as fh:
            json.dump({"atol": args.atol, "clean_delta": clean, "batches": args.batches,
                       "dtype": "float32", "faults": results,
                       "caught": caught, "injected": len(injected),
                       "not_caught": missed}, fh, indent=2)
        print(f"receipt: {args.receipt}")
    # Exit non-zero only if the harness proved vacuous (nothing caught at all).
    return 0 if caught else 1


if __name__ == "__main__":
    raise SystemExit(main())
