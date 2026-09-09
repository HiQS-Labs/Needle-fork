"""THE number: at 44 declared, how often is the gold label among the five tools retrieval picks?

That is the hard ceiling on engine top-1 at 44 declared. If it is ~2%, the model is not the
problem -- reachability is, and 1.50% observed is near-ceiling performance.
"""
import json, os, re, subprocess, warnings
CHILD = r'''
import json, warnings, sys
warnings.filterwarnings("ignore")
import needle
s=json.load(open("oracle/labels-v1.json"))
tools=json.dumps(s["schemas"],separators=(",",":"),ensure_ascii=False)
rows=[json.loads(l) for l in open("data/spike-mlx/manifests/frozen-200.jsonl")]
e=needle.Needle(tools=tools,system=rows[0].get("system"),weights="data/spike-mlx/oracle-10k-qat.cact")
import sys
for r in rows:
    e._worker.reset()
    print("###GOLD###", r["answers"][0]["name"], flush=True); sys.stdout.flush()
    e.complete(r["query"],max_new_tokens=4)
e.close()
'''
env = dict(os.environ, NEEDLE_DEBUG="1", HF_HUB_DISABLE_XET="1", NEEDLE_TELEMETRY="0")
warnings.filterwarnings("ignore")
from needle.model.tokenizer import get_tokenizer
from needle.model.run import load_checkpoint
_p, cfg = load_checkpoint("checkpoints/needle2.pkl")
tok = get_tokenizer(cfg.vocab_size)

proc = subprocess.run([".venv-mlx-spike/bin/python","-u","-c",CHILD], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
blob = proc.stdout
# interleave turn-id dumps with the gold markers that follow each
chunks = re.split(r"###GOLD### (\w+)", blob)
from collections import Counter
hit = tot = 0
sel_counter = Counter()
TURN = re.compile(r"\[debug\] turn ids:((?:\s+\d+)+)")
for i in range(1, len(chunks), 2):
    gold = chunks[i]
    after = chunks[i+1] if i+1 < len(chunks) else ""
    ms = TURN.findall(after)
    if not ms: continue
    ids=[int(x) for x in ms[-1].split()]
    names = re.findall(r'"name"\s*:\s*"([a-z_]+)"', tok.decode(ids))
    if not names: continue
    tot += 1
    sel_counter.update(names)
    if gold in names: hit += 1
print(f"  rows with a decoded selection : {tot}")
print(f"  gold among the retrieved five : {hit}  ({100*hit/max(tot,1):.2f}%)  <- CEILING on engine top-1 at 44 declared")
print(f"  observed engine top-1          : 1.50%")
print()
print("  most-retrieved tools across all rows:")
for n,c in sel_counter.most_common(8):
    print(f"     {n:<26} {c:>4} / {tot}")
