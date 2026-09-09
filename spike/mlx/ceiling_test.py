"""Codex's challenge: does injecting five schemas actually RESTRICT the output to those five?

My "capped near 9%" argument assumes the engine cannot emit a label outside the retrieved set.
That was never verified. If predictions fall outside it, the ceiling logic is invalid.
Captures retrieved set AND prediction in the SAME process, per row, with per-row exit checks.
"""
import json, os, re, subprocess, warnings
CHILD = r'''
import json, sys, warnings
warnings.filterwarnings("ignore")
import needle
s=json.load(open("oracle/labels-v1.json"))
tools=json.dumps(s["schemas"],separators=(",",":"),ensure_ascii=False)
rows=[json.loads(l) for l in open("data/spike-mlx/manifests/frozen-200.jsonl")][:40]
e=needle.Needle(tools=tools,system=rows[0].get("system"),weights="data/spike-mlx/oracle-10k-qat.cact")
for i,r in enumerate(rows):
    e._worker.reset()
    print(f"@@@ROW {i} {r['answers'][0]['name']}", flush=True)
    out=e.complete(r["query"],max_new_tokens=64)
    calls=out.get("function_calls") or []
    print(f"@@@PRED {calls[0]['name'] if calls else None}", flush=True)
e.close()
'''
env = dict(os.environ, NEEDLE_DEBUG="1", HF_HUB_DISABLE_XET="1", NEEDLE_TELEMETRY="0")
warnings.filterwarnings("ignore")
from needle.model.tokenizer import get_tokenizer
from needle.model.run import load_checkpoint
_p,cfg = load_checkpoint("checkpoints/needle2.pkl"); tok=get_tokenizer(cfg.vocab_size)
proc = subprocess.run([".venv-mlx-spike/bin/python","-u","-c",CHILD],
                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
print(f"  child exit code: {proc.returncode}")
blob = proc.stdout
TURN=re.compile(r"\[debug\] turn ids:((?:\s+\d+)+)")
parts=re.split(r"@@@ROW (\d+) (\w+)", blob)
inside=outside=nopred=0; miss=0; hit=0; n=0
for i in range(1,len(parts),3):
    gold=parts[i+1]; body=parts[i+2]
    tm=TURN.search(body); pm=re.search(r"@@@PRED (\w+|None)", body)
    if not tm or not pm: miss+=1; continue
    names=re.findall(r'"name"\s*:\s*"([a-z_]+)"', tok.decode([int(x) for x in tm.group(1).split()]))
    pred=pm.group(1); n+=1
    if gold in names: hit+=1
    if pred=="None": nopred+=1
    elif pred in names: inside+=1
    else: outside+=1
print(f"  rows parsed        : {n}  (unparsed {miss})")
print(f"  gold in retrieved5 : {hit}/{n} = {100*hit/max(n,1):.1f}%")
print()
print(f"  prediction INSIDE the retrieved five  : {inside}")
print(f"  prediction OUTSIDE the retrieved five : {outside}   <- if >0, the 'ceiling' logic is INVALID")
print(f"  no prediction                         : {nopred}")
