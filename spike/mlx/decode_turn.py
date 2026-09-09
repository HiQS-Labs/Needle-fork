"""Verify agy's Q1 claim: decode the engine's actual turn ids and count the schemas it injects."""
import json, os, re, subprocess, sys, warnings
CHILD = r'''
import json, warnings, sys
warnings.filterwarnings("ignore")
import needle
N=int(sys.argv[1]); ROW=int(sys.argv[2])
s=json.load(open("oracle/labels-v1.json"))
tools=json.dumps(s["schemas"][:N],separators=(",",":"),ensure_ascii=False)
rows=[json.loads(l) for l in open("data/spike-mlx/manifests/frozen-200.jsonl")]
r=rows[ROW]
e=needle.Needle(tools=tools,system=r.get("system"),weights="data/spike-mlx/oracle-10k-qat.cact")
e.complete(r["query"],max_new_tokens=4); e.close()
'''
env = dict(os.environ, NEEDLE_DEBUG="1", HF_HUB_DISABLE_XET="1", NEEDLE_TELEMETRY="0")
warnings.filterwarnings("ignore")
from needle.model.tokenizer import get_tokenizer
from needle.model.run import load_checkpoint
_p, cfg = load_checkpoint("checkpoints/needle2.pkl")
tok = get_tokenizer(cfg.vocab_size)
TURN = re.compile(r"\[debug\] turn ids:((?:\s+\d+)+)")

for n, row in [(6,0),(10,0),(44,0),(44,1),(44,7)]:
    out = subprocess.run([".venv-mlx-spike/bin/python","-c",CHILD,str(n),str(row)],
                         capture_output=True, text=True, env=env)
    blob = out.stdout + out.stderr
    m = TURN.search(blob)
    if not m:
        print(f"  {n:>3} tools row {row}: no turn ids"); continue
    ids = [int(x) for x in m.group(1).split()]
    text = tok.decode(ids)
    names = re.findall(r'"name"\s*:\s*"([a-z_]+)"', text)
    # measure just the <tools>…</tools> span
    mm = re.search(r"<tools>(.*?)</tools>", text, re.DOTALL)
    span = mm.group(1) if mm else ""
    ntok = len(tok.encode(span)) if span else 0
    print(f"  {n:>3} declared, row {row}: schemas injected = {len(names):<2} ({ntok} tokens)")
    print(f"      {names}")
