"""Score an Oracle artifact against a frozen manifest, with per-row receipts.

  engine:  python spike/mlx/run_eval.py --runtime engine --cact X.cact --manifest ...
  mlx:     python spike/mlx/run_eval.py --runtime mlx --adapter X.pkl --qat --manifest ...

Both runtimes are parsed by their own reader (spike/mlx/oracle_scoring.py) and normalised
to one Verdict, so the arms are comparable without forcing the native envelope onto MLX
text output.

--no-reset is the NEGATIVE CONTROL for the conversational-state defect: the engine is
conversational and `complete()` never calls needle_reset(), so a reused instance answers
every other row. With reset the answer rate should be ~100%; --no-reset should roughly
halve it. If --no-reset does NOT degrade, the control has stopped controlling anything.
"""
import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath("."))
from oracle_scoring import parse_native, parse_mlx_text, OK, ABSTAIN  # noqa: E402


def sha256(path, cap=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(cap)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def save_row(args, h, row, verdict):
    record = {"sha1": h, "gold": row["answers"][0]["name"],
              "pred": verdict.pred, "status": verdict.status, "raw": verdict.raw}
    with open(args.row_receipt, "a") as fh:
        fh.write(json.dumps(record) + "\n")


def load_manifest(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append((hashlib.sha1(line.encode()).hexdigest(), json.loads(line)))
    return rows


def run_engine(args, rows, labels, tools):
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("NEEDLE_TELEMETRY", "0")
    import warnings
    warnings.filterwarnings("ignore")
    import needle

    eng = needle.Needle(tools=tools, system=rows[0][1].get("system"), weights=args.cact)
    out = []
    for h, r in rows:
        if not args.no_reset:
            # the fix: clear conversational state so rows are independent
            if getattr(eng, "_worker", None) is not None:
                eng._worker.reset()
        try:
            env = eng.complete(r["query"], max_new_tokens=args.max_new_tokens)
            v = parse_native(env, labels)
        except Exception as exc:                                  # noqa: BLE001
            from oracle_scoring import Verdict, ERROR
            v = Verdict(None, ERROR, repr(exc)[:200])
        out.append((h, r, v))
        save_row(args, h, r, v)
        if len(out) % 100 == 0:
            ok = sum(1 for _, rr, vv in out if vv.status == OK and vv.pred == rr["answers"][0]["name"])
            print(f"  {len(out)}/{len(rows)}  top1 {100*ok/len(out):.1f}%", flush=True)
    try:
        eng.close()
    except Exception:
        pass
    return out


def run_mlx(args, rows, labels, _tools):
    import numpy as np, mlx.core as mx, pickle
    from san_mlx import SimpleAttentionNetworkMLX, normalize_config
    from train_lora import flatten, unflatten, merge_lora
    from needle.model.run import load_checkpoint
    from needle.model.tokenizer import get_tokenizer, BOS_ID, EOS_ID
    from needle.model.finetune import render_example

    params, config = load_checkpoint(args.checkpoint)
    cfg = normalize_config(dict(vars(config))); cfg["dtype"] = "float32"
    base = {p: mx.array(w) for p, w in
            {k: np.asarray(v).astype(np.float32) for k, v in flatten(params).items()}.items()}
    if args.adapter:
        ad = pickle.load(open(args.adapter, "rb"))
        lora = {k: {"A": mx.array(np.asarray(v["A"], np.float32)),
                    "B": mx.array(np.asarray(v["B"], np.float32))} for k, v in ad["lora"].items()}
        base = merge_lora(base, lora, ad["scale"])
    if args.qat:
        import quant_mlx as QM
        wb = getattr(config, "weight_bits", "") or None
        plan = QM.ste_plan(params, wb)
        delta = QM.ste_delta(base, plan); mx.eval(*delta.values())
        base = {k: (v + delta[k]) if k in delta else v for k, v in base.items()}
    model = SimpleAttentionNetworkMLX(unflatten(base), cfg, quant=args.qat)
    tok = get_tokenizer(cfg["vocab_size"])
    # stop as soon as the tool_call block closes -- the target ends there, and generating
    # to the full budget on every row is what made this arm 13 s/row.
    stop = tok.encode("</tool_call>")[-1]

    out = []
    for h, r in rows:
        prompt, _ = render_example(r)
        ids = [BOS_ID] + tok.encode(prompt)
        gen = []
        for _ in range(args.max_new_tokens):
            lg = model.logits_mx(mx.array([ids + gen]))
            nxt = int(mx.argmax(lg[0, -1]).item())
            if nxt == EOS_ID:
                break
            gen.append(nxt)
            if nxt == stop:
                break
        v = parse_mlx_text(tok.decode(gen), labels)
        out.append((h, r, v))
        save_row(args, h, r, v)
        if len(out) % 20 == 0:
            ok = sum(1 for _, rr, vv in out if vv.status == OK and vv.pred == rr["answers"][0]["name"])
            print(f"  {len(out)}/{len(rows)}  top1 {100*ok/len(out):.1f}%", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime", choices=("engine", "mlx"), required=True)
    ap.add_argument("--manifest", default="data/spike-mlx/manifests/frozen-200.jsonl")
    ap.add_argument("--labels", default="oracle/labels-v1.json")
    ap.add_argument("--cact", default="")
    ap.add_argument("--checkpoint", default="checkpoints/needle2.pkl")
    ap.add_argument("--adapter", default="")
    ap.add_argument("--qat", action="store_true")
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument("--no-reset", action="store_true", help="negative control (engine only)")
    ap.add_argument("--declare", default="",
                    help="path to a JSON list of label names: declare ONLY these tools. "
                         "Applies to BOTH runtimes -- the MLX prompt is re-rendered with the "
                         "same subset, so the arms stay comparable (restricting one side only "
                         "would reintroduce the unpaired-comparison problem).")
    ap.add_argument("--tag", default="")
    ap.add_argument("--outdir", default="data/spike-mlx/logs/frozen")
    a = ap.parse_args()

    schema = json.load(open(a.labels))
    all_schemas = schema["schemas"]
    if a.declare:
        keep = json.load(open(a.declare))
        by = {t["name"]: t for t in all_schemas}
        all_schemas = [by[n] for n in keep]
        labels = set(keep)
        print(f"  declaring {len(keep)} of {len(schema['schemas'])} tools: {keep}")
    else:
        labels = set(schema["labels"])
    tools = json.dumps(all_schemas, separators=(",", ":"), ensure_ascii=False)
    rows = load_manifest(a.manifest)
    if not rows or len({h for h, _ in rows}) != len(rows):
        ap.error("manifest must be nonempty with unique row identities")
    if len({r.get('system') for _, r in rows}) != 1:
        ap.error("the native runner requires one shared system prompt")
    if a.declare:
        # the MLX prompt is rendered from the row's own `tools`; rewrite it so both
        # runtimes are shown the same catalogue.
        for _, r in rows:
            r["tools"] = all_schemas
    art = a.cact or a.adapter or a.checkpoint
    # The suffix is NOT optional: without it an explicit --tag makes the negative control
    # overwrite the run it is meant to control, silently. That happened once already.
    tag = (a.tag or os.path.basename(art)) + ("-noreset" if a.no_reset else "")
    if not tag or os.path.basename(tag) != tag or tag in (".", ".."):
        ap.error("tag must be a single directory name")
    # One directory per invocation; an existing tag is an error, never a retry slot.
    a.outdir = os.path.join(a.outdir, a.runtime + "-" + tag)
    os.makedirs(a.outdir, exist_ok=False)
    a.row_receipt = os.path.join(a.outdir, "rows.jsonl")
    with open(a.row_receipt, "x"):
        pass
    config = {k: v for k, v in vars(a).items() if k != "row_receipt"}
    config["format_version"] = 2
    config["completed"] = False
    config["inputs"] = {k: {"path": os.path.abspath(p), "sha256": sha256(p)}
                        for k, p in {"manifest": a.manifest, "labels": a.labels,
                                     "artifact": art,
                                     **({"checkpoint": a.checkpoint} if a.runtime == "mlx" else {}),
                                     **({"declaration": a.declare} if a.declare else {})}.items()}
    config["source_sha256"] = {os.path.basename(p): sha256(p) for p in
                               (__file__, os.path.join(os.path.dirname(__file__), "oracle_scoring.py"))}
    config["engine_binary_sha256"] = None  # Unknown until the actual loaded binary is attested.
    config["session_provenance"] = None
    config_path = os.path.join(a.outdir, "run.json")
    with open(config_path, "x") as fh:
        json.dump(config, fh, indent=2)
    print(f"  runtime   {a.runtime}   artifact {os.path.basename(art)} sha256:{sha256(art)}")
    print(f"  manifest  {os.path.basename(a.manifest)}  {len(rows)} rows"
          f"   reset={'OFF (negative control)' if a.no_reset else 'on'}   max_new={a.max_new_tokens}")

    t0 = time.time()
    res = (run_engine if a.runtime == "engine" else run_mlx)(a, rows, labels, tools)
    wall = time.time() - t0

    per = a.row_receipt
    n = len(res)
    counts = {}
    for _, _, v in res:
        counts[v.status] = counts.get(v.status, 0) + 1
    correct = sum(1 for _, r, v in res if v.status == OK and v.pred == r["answers"][0]["name"])
    answered = counts.get(OK, 0)
    # When only a subset is declared, a row whose gold is undeclared is UNREACHABLE by
    # construction. Report it as a full-task failure AND report within-subset separately;
    # collapsing to one number would either hide the drop or flatter the condition.
    in_sub = [(r, v) for _, r, v in res if r["answers"][0]["name"] in labels]
    sub_correct = sum(1 for r, v in in_sub if v.status == OK and v.pred == r["answers"][0]["name"])
    summary = {
        "runtime": a.runtime, "artifact": art, "artifact_sha256": sha256(art),
        "manifest": a.manifest, "n": n, "reset": not a.no_reset,
        "max_new_tokens": a.max_new_tokens,
        "top1_pct": round(100 * correct / max(n, 1), 2),
        "answer_rate_pct": round(100 * answered / max(n, 1), 2),
        "precision_when_answering_pct": round(100 * correct / max(answered, 1), 2),
        "declared": sorted(labels) if a.declare else "all",
        "coverage_pct": round(100 * len(in_sub) / max(n, 1), 2),
        "within_subset_top1_pct": round(100 * sub_correct / max(len(in_sub), 1), 2),
        "within_subset_n": len(in_sub),
        "status_counts": counts, "wall_s": round(wall, 1),
        "s_per_row": round(wall / max(n, 1), 3), "per_row": per,
    }
    with open(os.path.join(a.outdir, "summary.json"), "x") as fh:
        json.dump(summary, fh, indent=2)
    config["completed"] = True
    config["rows_sha256"] = sha256(per)
    temporary = config_path + ".pending"
    with open(temporary, "x") as fh:
        json.dump(config, fh, indent=2)
    os.replace(temporary, config_path)
    print(f"\n  TOP-1        {summary['top1_pct']:.2f}%   ({correct}/{n})")
    print(f"  answer rate  {summary['answer_rate_pct']:.2f}%")
    print(f"  statuses     {counts}")
    if a.declare:
        print(f"  coverage     {summary['coverage_pct']:.1f}%  ({len(in_sub)}/{n} rows have a declared gold)")
        print(f"  within-sub   {summary['within_subset_top1_pct']:.2f}%   ({sub_correct}/{len(in_sub)})")
    print(f"  wall         {wall/60:.1f} min  ({summary['s_per_row']:.2f} s/row)")
    print(f"  receipts     {per}")


if __name__ == "__main__":
    main()
