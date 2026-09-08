"""GH-5: MLX port of `needle/model/architecture.py::SimpleAttentionNetwork` — the target.

Ported block by block against `needle/model/architecture.py` (line refs as of `main` 1f1f4e2).
Parity first, not "improvements": every function below mirrors the JAX one operation for
operation, including where it casts to float32 and back.

WEIGHT MAPPING (the documented trap). Weights come straight from the Flax `params` pytree.
Per-layer block weights are STACKED ON AXIS 0 by `nn.scan(variable_axes={"params": 0})`, so
`stack/layers/block/self_attn/q_proj/kernel` has shape `(num_layers, in, out)` and layer `i`
is `[i]`. Non-scanned params (`stack/mhc_*`, `stack/final_norm`) are also `(num_layers, ...)`
where they are per-layer. `nn.Dense` here is `x @ kernel` with kernel `(in, out)` and no bias.

The inference path only needs: `embedding`, `engrams_*`, `stack/layers/block/*`,
`stack/mhc_*`, `stack/final_norm`. The `mtp_*` tree is the multi-token-prediction head and is
unused when `return_mtp=False`, which is what `parity_check.py` compares.

QUANT: `parity_check.py` runs `quant=False`, under which JAX's `_aq` and `maybe_quant_kv` are
both the identity, so no quant path is ported here. That is P2 scope (`--qat-bits auto`).
"""
from __future__ import annotations

import math

import numpy as np

try:
    import mlx.core as mx
    import mlx.nn as mnn
except ImportError as exc:  # keep the harness's error precise
    raise NotImplementedError(f"mlx not installed: {exc} -- pip install -r spike/mlx/requirements-mlx.txt")

ENGRAM_SUB_DIM = 128
ENGRAM_CONV_TAPS = 4
_ENGRAM_SEED = 0x9E3779B9
_ENGRAM_PRIME = 0x01000193

DTYPE_MAP = {"float32": mx.float32, "bfloat16": mx.bfloat16, "float16": mx.float16}


import quant_mlx as QM  # noqa: E402


def _aq(x, quant):
    """architecture.py:22-25 -- A8 activation fake-quant when quant, identity otherwise."""
    return QM.fake_quant_act(x) if quant else x


def _a(x, dtype=None):
    """numpy/py -> mx.array, preserving dtype unless told otherwise."""
    arr = x if isinstance(x, mx.array) else mx.array(np.asarray(x))
    return arr.astype(dtype) if dtype is not None else arr


# --- ZCRMSNorm ---------------------------------------------------------- 46-57
def zc_rms_norm(x, scale, dtype, epsilon: float = 1e-6):
    """JAX: ((1 + scale) * x / rms).astype(dtype), architecture.py 46-57.

    `1 + scale` is evaluated in the PARAM's dtype, not float32. That matters: the
    real checkpoint stores fp16 params, and fp16 has ~10 mantissa bits, so near
    zero `1 + scale` resolves to ~1e-3 rather than ~1e-7. Upcasting scale first --
    the obvious thing to write -- silently makes this norm MORE accurate than the
    reference and was the dominant term in the P2 divergence on real weights.
    """
    xf = x.astype(mx.float32)
    rms = mx.sqrt(mx.mean(xf ** 2, axis=-1, keepdims=True) + epsilon)
    return ((1 + scale) * xf / rms).astype(dtype)


def _rms_unit(x, epsilon: float = 1e-6):                                 # 160-162
    xf = x.astype(mx.float32)
    return xf * mx.rsqrt(mx.mean(xf ** 2, axis=-1, keepdims=True) + epsilon)


# --- RoPE ------------------------------------------------------------- 97-118
def rope_freqs(head_dim, seq_len, theta=10000.0):                        # 97-103
    freqs = 1.0 / (theta ** (mx.arange(0, head_dim, 2).astype(mx.float32) / head_dim))
    t = mx.arange(seq_len).astype(mx.float32)
    angles = mx.outer(t, freqs)
    return mx.cos(angles), mx.sin(angles)


def apply_rope(x, cos, sin):                                            # 104-118
    T = x.shape[2]
    half = x.shape[-1] // 2
    cos = cos[:T][None, None, :, :]
    sin = sin[:T][None, None, :, :]
    x1 = x[..., :half]
    x2 = x[..., half:]
    return mx.concatenate([x1 * cos - x2 * sin, x2 * cos + x1 * sin], axis=-1).astype(x.dtype)


# --- Engram geometry / hashing --------------------------------------- 120-158
def engram_geometry(config):
    orders = tuple(config["engram_orders"])
    heads = config.get("engram_heads") or max(1, config["d_model"] // (len(orders) * ENGRAM_SUB_DIM))
    sub_dim = config["d_model"] // (len(orders) * heads)
    return orders, heads, sub_dim


def _shift_right(x, offset):                                            # 126-131
    if offset == 0:
        return x
    pad = [(0, 0)] * x.ndim
    pad[1] = (offset, 0)
    return mx.pad(x, pad)[:, : x.shape[1]]


def _mask_diag(mask, offset):                                           # 134-142
    m = mask[:, 0]
    T = m.shape[-1]
    if offset >= T:
        return mx.zeros(tuple(m.shape[:-2]) + (T,), m.dtype)
    d = mx.diagonal(m, offset=-offset, axis1=-2, axis2=-1)
    if offset == 0:
        return d
    return mx.pad(d, [(0, 0), (offset, 0)])


def engram_indices(tokens, orders, heads, slots):                       # 145-158
    u = tokens.astype(mx.uint32)
    prime = mx.array(_ENGRAM_PRIME, dtype=mx.uint32)
    idx = []
    for oi, order in enumerate(orders):
        for h in range(heads):
            seed = (_ENGRAM_SEED * (oi * heads + h + 1)) & 0xFFFFFFFF
            acc = mx.full(u.shape, mx.array(seed, dtype=mx.uint32), dtype=mx.uint32)
            for j in range(order):
                acc = (acc ^ _shift_right(u, j)) * prime
            acc = acc ^ (acc >> mx.array(15, dtype=mx.uint32))
            idx.append((acc % mx.array(slots, dtype=mx.uint32)).astype(mx.int32))
    return mx.stack(idx, axis=-1)


def _sinkhorn(logits, iters: int = 20):                                 # 169-175
    log_K = logits
    for _ in range(iters):
        log_K = log_K - mx.logsumexp(log_K, axis=-1, keepdims=True)
        log_K = log_K - mx.logsumexp(log_K, axis=-2, keepdims=True)
    return mx.exp(log_K)


# --- Engram module ---------------------------------------------------- 181-207
class Engram:
    def __init__(self, params, config, num_tables, sub_dim, conv_dilation, dtype, quant=False):
        self.quant = quant
        self.tables = _a(params["embedding"])                    # (num_tables, slots, sub_dim)
        self.key_w = _a(params["key_proj"]["kernel"])
        self.value_w = _a(params["value_proj"]["kernel"])
        self.taps = _a(params["taps"])                           # (ENGRAM_CONV_TAPS, d_model)
        self.num_tables = num_tables
        self.sub_dim = sub_dim
        self.conv_dilation = conv_dilation
        self.dtype = dtype

    def __call__(self, indices, ngram_ok, tap_ok):
        # tables[arange(num_tables), indices] -> [B, T, num_tables, sub_dim]
        # MLX has no tuple-of-arrays advanced indexing, so gather per table and stack.
        fetched = mx.stack(
            [mx.take(self.tables[t], indices[..., t], axis=0) for t in range(self.num_tables)],
            axis=2,
        )
        fetched = fetched * ngram_ok[..., None]
        e = fetched.reshape(indices.shape[0], indices.shape[1], self.num_tables * self.sub_dim)
        e = _aq(e.astype(self.dtype), self.quant)                     # architecture.py:197
        k = mx.matmul(e, self.key_w.astype(self.dtype))
        v = mx.matmul(e, self.value_w.astype(self.dtype))
        taps = self.taps.astype(self.dtype)
        acc = None
        for j in range(ENGRAM_CONV_TAPS):
            term = taps[j] * _shift_right(v, j * self.conv_dilation) * tap_ok[j][..., None]
            acc = term if acc is None else acc + term
        return k, acc


# --- MultiHeadAttention (GQA) ----------------------------------------- 209-278
class MultiHeadAttention:
    def __init__(self, params, config, dtype, quant=False):
        self.quant = quant
        self.q_w = _a(params["q_proj"]["kernel"])
        self.k_w = _a(params["k_proj"]["kernel"])
        self.v_w = _a(params["v_proj"]["kernel"])
        self.gate_w = _a(params["gate_proj"]["kernel"])
        self.out_w = _a(params["out_proj"]["kernel"])
        self.q_norm = _a(params["q_norm"]["scale"])
        self.k_norm = _a(params["k_norm"]["scale"])
        self.num_heads = config["num_heads"]
        self.num_kv_heads = config["num_kv_heads"]
        self.d_model = config["d_model"]
        self.attn_dim = config.get("attn_dim") or config["d_model"]
        self.dtype = dtype

    def __call__(self, x, mask=None, rope=None):
        attn_dim = self.attn_dim
        head_dim = attn_dim // self.num_heads
        B = x.shape[0]
        dt = self.dtype

        x = _aq(x, self.quant)                                          # architecture.py:225
        q = mx.matmul(x, self.q_w.astype(dt))
        k = mx.matmul(x, self.k_w.astype(dt))
        v = mx.matmul(x, self.v_w.astype(dt))

        q = q.reshape(B, -1, self.num_heads, head_dim).transpose(0, 2, 1, 3)
        k = k.reshape(B, -1, self.num_kv_heads, head_dim).transpose(0, 2, 1, 3)
        v = v.reshape(B, -1, self.num_kv_heads, head_dim).transpose(0, 2, 1, 3)

        q = zc_rms_norm(q, self.q_norm, dt)
        k = zc_rms_norm(k, self.k_norm, dt)

        if rope is not None:
            cos, sin = rope
            q = apply_rope(q, cos, sin)
            k = apply_rope(k, cos, sin)

        repeats = self.num_heads // self.num_kv_heads
        if repeats > 1:
            k = mx.repeat(k, repeats, axis=1)
            v = mx.repeat(v, repeats, axis=1)

        scale = math.sqrt(float(head_dim))
        attn = mx.matmul(q, k.transpose(0, 1, 3, 2)) / scale
        if mask is not None:
            neg = mx.finfo(attn.dtype).min if hasattr(mx, "finfo") else -3.4e38
            attn = mx.where(mask, attn, mx.array(neg, dtype=attn.dtype))
        attn = mx.softmax(attn.astype(mx.float32), axis=-1).astype(dt)
        out = mx.matmul(attn, v)
        out = out.transpose(0, 2, 1, 3).reshape(B, -1, attn_dim)

        out = out * mx.sigmoid(mx.matmul(x, self.gate_w.astype(dt)))
        out = _aq(out, self.quant)                                      # architecture.py:276
        return mx.matmul(out, self.out_w.astype(dt))


# --- HadamardMLP ------------------------------------------------------ 280-303
def _walsh_matrix(n):                                                   # 280-285
    H = np.array([[1.0]], dtype=np.float32)
    while H.shape[0] < n:
        H = np.block([[H, H], [H, -H]])
    return mx.array(H / np.sqrt(n))


class HadamardMLP:
    def __init__(self, params, d_model, dtype):
        self.d1 = _a(params["d1"])
        self.d2 = _a(params["d2"])
        self.d3 = _a(params["d3"])
        self.d_model = d_model
        self.dtype = dtype
        self.n = 1 << (d_model - 1).bit_length()
        self.H = _walsh_matrix(self.n)

    def __call__(self, x):
        dt = self.dtype
        H = self.H.astype(dt)
        d1, d2, d3 = self.d1.astype(dt), self.d2.astype(dt), self.d3.astype(dt)
        pad = self.n - self.d_model
        z = mx.pad(x, [(0, 0), (0, 0), (0, pad)]) if pad else x
        z = mx.matmul(d1 * z, H)
        z = mx.matmul(mnn.silu(d2 * z), H)
        return (d3 * z)[..., : self.d_model]


# --- Block ------------------------------------------------------------ 305-338
class Block:
    def __init__(self, params, config, dtype, quant=False):
        self.quant = quant
        self.norm0 = _a(params["ZCRMSNorm_0"]["scale"])
        self.post_attn_norm = _a(params["post_attn_norm"]["scale"])
        self.pre_hada_norm = _a(params["pre_hada_norm"]["scale"])
        self.attn_gate = _a(params["attn_gate"])
        self.attn = MultiHeadAttention(params["self_attn"], config, dtype, quant=quant)
        self.mlp = HadamardMLP(params["hadamard_mlp"], config["d_model"], dtype)
        self.d_model = config["d_model"]
        self.dtype = dtype

    def __call__(self, x, mask=None, rope=None, engram_kv=None, site_flags=None):
        dt = self.dtype
        if engram_kv is not None:
            ek, ev = engram_kv
            alpha = mx.sigmoid(
                mx.einsum("btd,sbtd->sbt", _rms_unit(x), _rms_unit(ek)) / math.sqrt(self.d_model)
            )
            add = mx.einsum("s,sbt,sbtd->btd", site_flags.astype(mx.float32), alpha,
                            ev.astype(mx.float32))
            x = x + add.astype(x.dtype)

        skip = x
        x = zc_rms_norm(x, self.norm0, dt)
        x = self.attn(x, mask=mask, rope=rope)
        x = zc_rms_norm(x, self.post_attn_norm, dt)
        # JAX: nn.sigmoid(param).astype(dtype) -- sigmoid in the PARAM's dtype
        # (fp16 on the real checkpoint), then cast. Same reasoning as zc_rms_norm.
        gate = mx.sigmoid(self.attn_gate).astype(dt)
        x = skip + gate * x

        skip = x
        x = zc_rms_norm(x, self.pre_hada_norm, dt)
        x = self.mlp(x)
        return skip + x


# --- Stack (MHC lanes + scanned layers) ------------------------------- 340-425
class Stack:
    def __init__(self, params, config, dtype, quant=False):
        self.quant = quant
        self.config = config
        self.dtype = dtype
        self.num_layers = config["num_layers"]
        self.n = config["mhc_lanes"]
        self.d_model = config["d_model"]
        blk = params["layers"]["block"]
        self.blocks = [Block(_slice_layer(blk, i), config, dtype, quant=quant) for i in range(self.num_layers)]
        self.final_norm = _a(params["final_norm"]["scale"])
        self.mhc = {k: _a(params[f"mhc_{k}"]) for k in
                    ("phi_pre", "phi_post", "phi_res", "b_pre", "b_post", "b_res",
                     "a_pre", "a_post", "a_res")}
        lane = np.eye(self.n, dtype=np.float32)[np.arange(self.num_layers) % self.n]
        self.pre_off = mx.array(8 * lane - 4)
        self.post_off = mx.array(-4 * (1 - lane))

    def __call__(self, x, mask=None, rope=None, engram_kv=None):
        cfg = self.config
        dt = self.dtype
        x = x.astype(dt)
        n = self.n

        site_flags = None
        if engram_kv is not None:
            flags = np.zeros((self.num_layers, len(cfg["engram_layers"])), np.float32)
            for s, layer in enumerate(cfg["engram_layers"]):
                flags[layer, s] = 1.0
            site_flags = mx.array(flags)

        B, T = x.shape[0], x.shape[1]
        x = mx.broadcast_to(x[:, :, None, :], (B, T, n, x.shape[-1]))

        for i in range(self.num_layers):
            x = self._layer(i, x, mask, rope, engram_kv,
                            None if site_flags is None else site_flags[i])

        x = mx.mean(x, axis=2)
        return zc_rms_norm(x, self.final_norm, dt)

    def _layer(self, i, x, mask, rope, engram_kv, site_flags):          # _ScanBody 340-374
        dt = self.dtype
        m = self.mhc
        B, T, n, C = x.shape
        xf = x.astype(mx.float32)
        nx = _rms_unit(x.reshape(B, T, n * C))

        hpre = mx.sigmoid(m["a_pre"][i] * mx.matmul(nx, m["phi_pre"][i].astype(mx.float32))
                          + m["b_pre"][i] + self.pre_off[i])
        u = mx.einsum("btn,btnc->btc", hpre, xf).astype(dt)

        y = self.blocks[i](u, mask=mask, rope=rope, engram_kv=engram_kv,
                           site_flags=site_flags) - u

        hpost = 2 * mx.sigmoid(m["a_post"][i] * mx.matmul(nx, m["phi_post"][i].astype(mx.float32))
                               + m["b_post"][i] + self.post_off[i])
        res = mx.matmul(nx, m["phi_res"][i].astype(mx.float32))
        hres = _sinkhorn(m["a_res"][i] * res.reshape(B, T, n, n) + m["b_res"][i])
        new_x = (mx.einsum("btij,btjc->btic", hres, xf)
                 + hpost[..., None] * y.astype(mx.float32)[:, :, None, :])
        return new_x.astype(dt)


def _slice_layer(tree, i):
    """Take layer `i` from a pytree whose leaves are stacked on axis 0 by nn.scan.

    An `mx.array` leaf is indexed in-graph. Going through numpy here would sever
    the autodiff chain, which is exactly what a LoRA-merged weight needs to keep.
    """
    if isinstance(tree, dict):
        return {k: _slice_layer(v, i) for k, v in tree.items()}
    if isinstance(tree, mx.array):
        return tree[i]
    return np.asarray(tree)[i]


# --- top level ---------------------------------------------------------------
def make_causal_mask(seq_len):                                          # 588-590
    return mx.tril(mx.ones((seq_len, seq_len), dtype=mx.bool_))[None, None, :, :]


class SimpleAttentionNetworkMLX:
    """Top-level model. `logits(tokens)` returns float32 [batch, seq, vocab]."""

    def __init__(self, params, config, quant=False):
        self.quant = quant
        self.config = config
        self.dtype = DTYPE_MAP[config.get("dtype", "bfloat16")]
        self.embedding = _a(params["embedding"]["embedding"])
        self.embed_scale = math.sqrt(config["d_model"])
        self.stack = Stack(params["stack"], config, self.dtype, quant=quant)

        orders, heads, sub_dim = engram_geometry(config)
        self.orders, self.heads = orders, heads
        self.engrams = [
            Engram(params[f"engrams_{s}"], config, len(orders) * heads, sub_dim,
                   max(orders), self.dtype, quant=quant)
            for s in range(len(config["engram_layers"]))
        ]

    def _engram_kv(self, tokens, mask):                                 # 511-521
        if not self.engrams:
            return None
        orders, heads = self.orders, self.heads
        indices = engram_indices(tokens, orders, heads, self.config["engram_slots"])
        ngram_ok = mx.stack([_mask_diag(mask, o - 1) for o in orders for _ in range(heads)],
                            axis=-1)
        tap_ok = mx.stack([_mask_diag(mask, j * max(orders)) for j in range(ENGRAM_CONV_TAPS)])
        pairs = [e(indices, ngram_ok, tap_ok) for e in self.engrams]
        return (mx.stack([k for k, _ in pairs]), mx.stack([v for _, v in pairs]))

    def logits(self, tokens):
        """Eager float32 numpy logits -- the inference/parity entry point."""
        out = self.logits_mx(tokens)
        mx.eval(out)
        return np.asarray(out, dtype=np.float32)

    def logits_mx(self, tokens):
        """Same forward pass, left as a lazy `mx.array` so gradients can flow."""
        toks = _a(tokens, mx.int32)
        mask = make_causal_mask(toks.shape[1])
        x = mx.take(self.embedding, toks.reshape(-1), axis=0).reshape(
            toks.shape[0], toks.shape[1], -1) * self.embed_scale
        rope = rope_freqs((self.config.get("attn_dim") or self.config["d_model"])
                          // self.config["num_heads"],
                          toks.shape[1], self.config["rope_theta"])
        engram_kv = self._engram_kv(toks, mask)
        x = self.stack(x.astype(self.dtype), mask=mask, rope=rope, engram_kv=engram_kv)
        return mx.matmul(_aq(x, self.quant).astype(mx.float32),        # architecture.py:527
                         self.embedding.astype(mx.float32).T)


def normalize_config(config: dict) -> dict:
    """Fill dataclass defaults exactly as the JAX side does.

    A checkpoint's `config` is `dict(vars(TransformerConfig(...)))`, and that only
    carries the fields explicitly passed -- `engram_orders`, `rope_theta`, `dtype`
    and friends are class-level defaults and are absent. The JAX reference refills
    them by reconstructing `TransformerConfig(**config)`, so this does the same
    rather than re-listing the defaults here, where they could drift silently.
    """
    from needle.model.architecture import TransformerConfig
    cfg = TransformerConfig(**config)
    out = {f: getattr(cfg, f) for f in TransformerConfig.__dataclass_fields__}
    out["engram_layers"] = tuple(out["engram_layers"])
    out["engram_orders"] = tuple(out["engram_orders"])
    return out


def from_checkpoint(ckpt: dict) -> SimpleAttentionNetworkMLX:
    """Build from a Needle checkpoint dict: {"format_version": 2, "params": pytree, "config": dict}."""
    return SimpleAttentionNetworkMLX(ckpt["params"], normalize_config(ckpt["config"]))
