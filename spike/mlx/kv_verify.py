"""Re-verify the KV prefix/turn claim RIGOROUSLY -- it is D10's load-bearing measurement.

The first sweep used `grep | head -1` on a line I had already seen emitted TWICE with
different values (39 and 0) for the 44-tool case, and counted turn tokens with `wc -w`
minus a fudge. Both are brittle. This parses every occurrence, counts real token ids,
and repeats each condition on multiple rows to check it is not query-dependent.
"""
import json, os, random, re, subprocess, sys

CHILD = r'''
import json, warnings, sys
warnings.filterwarnings("ignore")
import needle
N=int(sys.argv[1]); ROW=int(sys.argv[2])
schema=json.load(open("oracle/labels-v1.json"))
tools=json.dumps(schema["schemas"][:N],separators=(",",":"),ensure_ascii=False)
rows=[json.loads(l) for l in open("data/spike-mlx/manifests/frozen-200.jsonl")]
r=rows[ROW]
e=needle.Needle(tools=tools,system=r.get("system"),weights="data/spike-mlx/oracle-10k-qat.cact")
e.complete(r["query"],max_new_tokens=4); e.close()
'''

env = dict(os.environ, NEEDLE_DEBUG="1", HF_HUB_DISABLE_XET="1", NEEDLE_TELEMETRY="0")
PREFIX = re.compile(r"kv prefix (\d+)")
IDS = re.compile(r"\[debug\] (prefix|turn) ids:((?:\s+\d+)+)")

def probe(n, row):
    out = subprocess.run([".venv-mlx-spike/bin/python", "-c", CHILD, str(n), str(row)],
                         capture_output=True, text=True, env=env)
    blob = out.stdout + out.stderr
    prefixes = [int(x) for x in PREFIX.findall(blob)]
    ids = {}
    for kind, body in IDS.findall(blob):
        ids.setdefault(kind, []).append(len(body.split()))
    return prefixes, ids

print("  all 'kv prefix N' occurrences (not just the first), and real id counts")
print(f"  {'tools':>5} {'row':>4} | {'kv prefix line(s)':<22} | {'prefix ids':<12} {'turn ids'}")
print("  " + "-" * 76)
for n in (1, 5, 6, 10, 44):
    for row in (0, 1, 7):
        pre, ids = probe(n, row)
        pid = ",".join(str(x) for x in ids.get("prefix", [])) or "-"
        tid = ",".join(str(x) for x in ids.get("turn", [])) or "-"
        print(f"  {n:>5} {row:>4} | {str(pre):<22} | {pid:<12} {tid}")
