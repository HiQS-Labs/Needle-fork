"""Quantisation-aware training primitives for the MLX port -- mirrors needle/model/quantize.py.

What is PORTED here is only the array math that has to run inside MLX's autodiff:
`cq_quantize` (~12 lines) and `fake_quant` (~10 lines), each wrapped as a straight-
through estimator. What is IMPORTED, not ported: the Lloyd-Max codebook and the
Hadamard matrix (`@lru_cache` numpy constants keyed only on (bits, group)), the
leaf-selection rule, the canonical-name -> bits mapping, and the bit-map parser.
Reusing those is what keeps this from drifting: the bits plan is computed by JAX's
own helpers, so the MLX model quantises exactly the leaves JAX would, at exactly
the widths JAX would.

Why this exists (D7): post-training quantisation of LoRA-merged weights destroys
the fine-tune -- measured, the tuned model degenerates to '<think> } } } }' with
no engine involved. Training THROUGH the quantiser is the fix, and this is what
`needle finetune --qat-bits auto` does on JAX.

Reference lines cited per function. Every function is verified against the JAX
original by spike/mlx/parity_qat.py before it is trusted.
"""
from __future__ import annotations
import numpy as np
import mlx.core as mx
from needle.model import quantize as Q

_CB: dict = {}
_H: dict = {}

def codebook(bits, group):
    k = (bits, group)
    if k not in _CB:
        _CB[k] = mx.array(Q._cq_codebook_np(bits, group))     # quantize.py:113
    return _CB[k]

def hadamard(group):
    if group not in _H:
        _H[group] = mx.array(Q._cq_hadamard_np(group))        # quantize.py:119
    return _H[group]

def cq_quantize(w, bits, group=Q.CQ_GROUP_SIZE):
    """quantize.py:134-148, op for op. Returns the DEQUANTISED value (no gradient)."""
    cb = codebook(bits, group)
    D = w.shape[-1]
    pad = (-D) % group
    wp = mx.pad(w, [(0, 0)] * (w.ndim - 1) + [(0, pad)]) if pad else w
    groups = wp.reshape(*wp.shape[:-1], -1, group).astype(mx.float32)
    H = hadamard(group)
    rot = groups @ H
    norm = mx.sqrt(mx.sum(rot ** 2, axis=-1, keepdims=True))
    unit = rot / mx.maximum(norm, 1e-12)
    norm = norm.astype(mx.float16).astype(mx.float32)
    # _cq_nearest (quantize.py:126-132): nearest codeword, ties to the LEFT entry.
    # argmin returns the first minimum, i.e. the lower index -- the same tie rule.
    idx = mx.argmin(mx.abs(unit[..., None] - cb), axis=-1)
    deq = (cb[idx] * norm) @ H
    deq = deq.reshape(wp.shape).astype(w.dtype)
    return deq[..., :D] if pad else deq

def cq_ste(w, bits, group=Q.CQ_GROUP_SIZE):
    """quantize.py:354 -- forward uses the quantised value, gradient passes straight through."""
    return w + mx.stop_gradient(cq_quantize(w, bits, group) - w)

def fake_quant(w, group_size, bits):
    """quantize.py:10-23 (absmax per group, symmetric int, STE)."""
    qmax = 2 ** (bits - 1) - 1
    D = w.shape[-1]
    pad = (-D) % group_size
    wp = mx.pad(w, [(0, 0)] * (w.ndim - 1) + [(0, pad)]) if pad else w
    g = wp.reshape(*wp.shape[:-1], -1, group_size).astype(mx.float32)
    absmax = mx.max(mx.abs(g), axis=-1, keepdims=True)
    scale = mx.where(absmax > 0, absmax / qmax, mx.array(1.0, dtype=mx.float32))
    q = mx.clip(mx.round(g / scale), -qmax - 1, qmax) * scale
    q = q.reshape(wp.shape).astype(w.dtype)
    if pad:
        q = q[..., :D]
    return w + mx.stop_gradient(q - w)

def fake_quant_act(x):
    """quantize.py:33-34 -- A8 over the full last dim (one group), as configure_deploy(act_bits=8)."""
    return fake_quant(x, x.shape[-1], 8)

def ste_plan(params_nested, weight_bits: str | None):
    """{path_tuple: (bits, transposed)} for every leaf JAX would quantise.

    Mirrors finetune.py:332-346 + quantize.py:150-160/218-222/254-266:
      * `weight_bits` set  -> mixed map via parse_bits_map, default from the map
      * `weight_bits` empty -> uniform W4 (finetune.py's `qat_bits = 4` branch)
    Leaves are chosen by `_is_quant_leaf`; kernels and mhc_phi are quantised along the
    second-to-last axis (`_reduces_second_last`), so they are transposed around the op.
    """
    if weight_bits:
        bits_map, default = Q.parse_bits_map(weight_bits)
    else:
        bits_map, default = {}, 4
    plan = {}
    for name, _ in Q.quant_leaf_names(params_nested):
        path = tuple(name.split("/"))
        key = path[-1]
        transposed = key == "kernel" or key.startswith("mhc_phi")
        plan[path] = (Q._bits_for(name, bits_map, default), transposed)
    return plan

def apply_weight_ste(flat_mx: dict, plan: dict, group=Q.CQ_GROUP_SIZE) -> dict:
    """Apply cq_ste to every leaf in the plan (the MLX twin of cq_ste_mixed_params)."""
    out = dict(flat_mx)
    for path, (bits, transposed) in plan.items():
        w = out[path]
        if transposed:
            out[path] = mx.swapaxes(cq_ste(mx.swapaxes(w, -1, -2), bits, group), -1, -2)
        else:
            out[path] = cq_ste(w, bits, group)
    return out

def ste_delta(flat_mx: dict, plan: dict, group=Q.CQ_GROUP_SIZE) -> dict:
    """{path: stop_gradient(cq_quantize(w) - w)} for every planned leaf -- the STE's constant.

    Within one optimiser step the LoRA params do not change, so the STE delta is the
    same for every micro-batch. Computing it ONCE per step and adding it inside the
    differentiated function is mathematically identical to calling cq_ste per
    micro-batch -- the gradient through `w + stop_gradient(q - w)` is the identity on
    `w` either way -- and it removes a 16x recomputation of the quantiser. Measured:
    the per-micro-batch form ran at 63-65 s/step against 22 s/step for fp32.
    """
    out = {}
    for path, (bits, transposed) in plan.items():
        w = flat_mx[path]
        wt = mx.swapaxes(w, -1, -2) if transposed else w
        d = cq_quantize(wt, bits, group) - wt
        out[path] = mx.stop_gradient(mx.swapaxes(d, -1, -2) if transposed else d)
    return out

def describe(plan: dict, weight_bits: str | None) -> str:
    """The same 'numerics' line finetune.py prints, so logs read identically."""
    return f"CQ mixed[{weight_bits}] STE + A8" if weight_bits else "CQ W4 STE + A8"
