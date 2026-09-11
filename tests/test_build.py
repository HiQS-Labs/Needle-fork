import os
import types

import pytest

pytestmark = pytest.mark.slow


def _build_args(checkpoint, out, bits="4", lora=None):
    return types.SimpleNamespace(checkpoint=checkpoint, lora=lora, out=out,
                                 upload=False, bits=bits)


def test_build_exports_loadable_cact(tiny_checkpoint, tmp_path):
    from needle.model.finetune import build_main
    from needle.model.export import read_export

    out = str(tmp_path / "tiny.cact")
    build_main(_build_args(tiny_checkpoint, out, bits="4"))

    assert os.path.exists(out)
    assert os.path.getsize(out) > 0
    header, tensors = read_export(out)
    assert header["num_tensors"] > 0
    assert len(tensors) == header["num_tensors"]
    assert any(isinstance(t, (bytes, bytearray)) for t in tensors)


def test_build_at_two_bits(tiny_checkpoint, tmp_path):
    from needle.model.finetune import build_main
    from needle.model.export import read_export

    out = str(tmp_path / "tiny_w2.cact")
    build_main(_build_args(tiny_checkpoint, out, bits="2"))
    header, _ = read_export(out)
    assert header["num_tensors"] > 0


def test_export_round_trips_a_projection(tiny_checkpoint, tmp_path):
    import pickle
    import numpy as np
    from needle.model.export import write_export, read_export
    from needle.model.architecture import TransformerConfig, effective_kv_window
    from needle.model.tokenizer import get_tokenizer

    with open(tiny_checkpoint, "rb") as handle:
        ckpt = pickle.load(handle)
    params, config = ckpt["params"], TransformerConfig(**ckpt["config"])

    out = str(tmp_path / "rt.cact")
    write_export(params, config, out, bits=4,
                 tokenizer=get_tokenizer(config.vocab_size),
                 kv_window=effective_kv_window(config))
    header, tensors = read_export(out)

    original = np.asarray(params["stack"]["layers"]["block"]["self_attn"]["q_proj"]["kernel"][0]).T
    dequant = tensors[2]
    assert dequant.shape == original.shape
    assert np.corrcoef(dequant.ravel(), original.ravel())[0, 1] > 0.9


# --- adapter numerics provenance -------------------------------------------
# write_export always quantises (W4 if nothing else is asked for), so an adapter
# that was not trained quantisation-aware is always deployed into numerics it
# never saw. That used to happen silently, while the milder case -- a QAT
# adapter whose bit width disagrees with --bits -- already raised.

def _adapter(tmp_path, name, params, **meta):
    import pickle
    import numpy as np
    from needle.model.finetune import lora_target_paths, init_lora
    import jax

    paths = lora_target_paths(params)
    lora = init_lora(params, paths, 4, jax.random.PRNGKey(0))
    payload = {"lora": {"/".join(p): {"A": np.asarray(v["A"]), "B": np.asarray(v["B"])}
                        for p, v in lora.items()},
               "scale": 2.0, "rank": 4}
    payload.update(meta)
    path = tmp_path / name
    with open(path, "wb") as handle:
        pickle.dump(payload, handle)
    return str(path)


def _params(checkpoint):
    from needle.model.run import load_checkpoint
    params, _ = load_checkpoint(checkpoint)
    return params


def test_build_refuses_adapter_trained_full_precision(tiny_checkpoint, tmp_path):
    """qat_bits present but None == deliberately trained at full precision."""
    from needle.model.finetune import build_main

    lora = _adapter(tmp_path, "fp32.pkl", _params(tiny_checkpoint),
                    qat_bits=None, qat_bits_map=None)
    with pytest.raises(ValueError, match="was trained at full precision"):
        build_main(_build_args(tiny_checkpoint, str(tmp_path / "o.cact"),
                               bits="4", lora=lora))


def test_build_refuses_adapter_with_no_numerics_metadata(tiny_checkpoint, tmp_path):
    """No qat keys at all -- a foreign trainer, or one predating the field.

    This is the case that motivated the guard: an MLX-trained adapter carries no
    qat metadata, and .get() made that indistinguishable from an explicit None.
    """
    from needle.model.finetune import build_main

    lora = _adapter(tmp_path, "foreign.pkl", _params(tiny_checkpoint))
    with pytest.raises(ValueError, match="does not declare its training numerics"):
        build_main(_build_args(tiny_checkpoint, str(tmp_path / "o.cact"),
                               bits="4", lora=lora))


def test_build_allows_mismatch_when_explicitly_accepted(tiny_checkpoint, tmp_path):
    """Post-training quantisation stays available -- it just has to be chosen."""
    import types
    from needle.model.finetune import build_main
    from needle.model.export import read_export

    lora = _adapter(tmp_path, "foreign2.pkl", _params(tiny_checkpoint))
    out = str(tmp_path / "ok.cact")
    args = types.SimpleNamespace(checkpoint=tiny_checkpoint, lora=lora, out=out,
                                 upload=False, bits="4",
                                 allow_numerics_mismatch=True)
    build_main(args)
    header, _ = read_export(out)
    assert header["num_tensors"] > 0


def test_build_still_accepts_a_qat_adapter(tiny_checkpoint, tmp_path):
    """The guard must not fire on the case it was never about."""
    from needle.model.finetune import build_main
    from needle.model.export import read_export

    lora = _adapter(tmp_path, "qat.pkl", _params(tiny_checkpoint),
                    qat_bits=4, qat_bits_map=None)
    out = str(tmp_path / "qat.cact")
    build_main(_build_args(tiny_checkpoint, out, bits=None, lora=lora))
    header, _ = read_export(out)
    assert header["num_tensors"] > 0


def test_build_without_an_adapter_is_unaffected(tiny_checkpoint, tmp_path):
    """No --lora means no training numerics to disagree with."""
    from needle.model.finetune import build_main
    from needle.model.export import read_export

    out = str(tmp_path / "plain.cact")
    build_main(_build_args(tiny_checkpoint, out, bits="4"))
    header, _ = read_export(out)
    assert header["num_tensors"] > 0
