"""GH-5: MLX port of `needle/model/architecture.py::SimpleAttentionNetwork` — the target.

Port ONE block at a time, in this order, and run `parity_check.py --tiny` after each. Every
class carries the exact source range it must match. Do not "improve" anything: parity first,
then P3. Weights come straight from the Flax `params` pytree in the checkpoint; the mapping
from Flax names to these modules is the first thing to get right and the most common source
of a silent mismatch — print the pytree keys once and keep the mapping explicit.

Reference: `needle/model/architecture.py` (line numbers as of `main` 1f1f4e2)
    TransformerConfig ........ 59-96   (fields; note engram_layers is a tuple of layer indices)
    ZCRMSNorm ................ 46-57
    precompute_rope_freqs .... 97-103
    apply_rope ............... 104-118
    engram_geometry/indices .. 120-158
    _sinkhorn ................ 169-175
    Engram ................... 181-207
    MultiHeadAttention (GQA) . 209-278
    _walsh_matrix ............ 280-285
    HadamardMLP .............. 287-303
    Block .................... 305+
    SimpleAttentionNetwork ... (top of file after Block)
Quant-aware path (`_aq`, 22-27; `act_bits`/`kv_bits`/`weight_bits` in config) is P2 scope.
"""
from __future__ import annotations

try:
    import mlx.core as mx  # noqa: F401
    import mlx.nn as nn  # noqa: F401
except ImportError as exc:  # keep the harness's error precise
    raise NotImplementedError(f"mlx not installed: {exc} -- pip install -r spike/mlx/requirements-mlx.txt")


def _todo(block: str, lines: str):
    raise NotImplementedError(f"{block} not ported (architecture.py {lines})")


class ZCRMSNorm:            # architecture.py 46-57
    def __init__(self, params, eps=1e-6): _todo("ZCRMSNorm", "46-57")


def rope_freqs(head_dim, seq_len, theta):   # 97-103
    _todo("precompute_rope_freqs", "97-103")


def apply_rope(x, cos, sin):                 # 104-118
    _todo("apply_rope", "104-118")


class Engram:               # 120-158 geometry/indices, 169-175 sinkhorn, 181-207 module
    def __init__(self, params, config): _todo("Engram", "120-207")


class MultiHeadAttention:   # 209-278, GQA with num_kv_heads
    def __init__(self, params, config): _todo("MultiHeadAttention", "209-278")


class HadamardMLP:          # 280-303 (_walsh_matrix + module)
    def __init__(self, params, config): _todo("HadamardMLP", "280-303")


class Block:                # 305+
    def __init__(self, params, config, layer_idx): _todo("Block", "305+")


class SimpleAttentionNetworkMLX:
    """Top-level model. `logits(tokens)` must return float32 [batch, seq, vocab]."""

    def __init__(self, params, config):
        self.config = config
        self.params = params
        _todo("SimpleAttentionNetwork (embedding/blocks/final norm/lm head)", "top-level")

    def logits(self, tokens):
        _todo("SimpleAttentionNetworkMLX.logits", "top-level")


def from_checkpoint(ckpt: dict) -> SimpleAttentionNetworkMLX:
    """Build from a Needle checkpoint dict: {"format_version": 2, "params": pytree, "config": dict}."""
    return SimpleAttentionNetworkMLX(ckpt["params"], ckpt["config"])
