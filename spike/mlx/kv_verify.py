"""Capture the KV probe as immutable evidence, not a count-only conclusion (#14).

python spike/mlx/kv_verify.py --outdir data/spike-mlx/kv-round-UNIQUE
Each child has its own stdout/stderr receipt and row identity. A nonzero exit,
timeout, or absent token arrays is never accepted as a complete trace. The raw
streams retain their own ordering; concatenating them cannot establish chronology.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

CHILD = r'''
import json, sys
import needle
n, index, manifest, labels, weights = sys.argv[1:]
r = [json.loads(l) for l in open(manifest) if l.strip()][int(index)]
schema = json.load(open(labels))
tools = json.dumps(schema["schemas"][:int(n)], separators=(",", ":"), ensure_ascii=False)
print("PROBE: initializing", flush=True)
e = needle.Needle(tools=tools, system=r.get("system"), weights=weights)
print("PROBE: completing", flush=True)
e.complete(r["query"], max_new_tokens=4)
e.close()
print("PROBE: completed", flush=True)
'''
IDS = re.compile(r'\[debug\] (prefix|turn) ids:([^\r\n]*)')


def extract_ids(stream):
    """Keep every event and reject noninteger tails rather than silently truncating."""
    events = []
    for match in IDS.finditer(stream):
        body = match.group(2).split()
        if any(not token.isdecimal() for token in body):
            raise ValueError('noninteger/truncated token-ID event')
        events.append({'kind': match.group(1), 'offset': match.start(),
                       'ids': [int(token) for token in body]})
    return events


def capture(command, env, timeout):
    try:
        result = subprocess.run(command, capture_output=True, env=env, timeout=timeout)
        out, err, code, timed_out = result.stdout, result.stderr, result.returncode, False
    except subprocess.TimeoutExpired as exc:
        out, err, code, timed_out = exc.stdout or b'', exc.stderr or b'', None, True
    streams = {'stdout': out.decode('utf-8', errors='replace'),
               'stderr': err.decode('utf-8', errors='replace')}
    record = {'command': command, 'returncode': code, 'timed_out': timed_out,
              **streams, 'events': {}, 'status': 'INCOMPLETE'}
    try:
        record['events'] = {name: extract_ids(value) for name, value in streams.items()}
    except ValueError as exc:
        record['reason'] = str(exc)
        return record
    kinds = {event['kind'] for events in record['events'].values() for event in events if event['ids']}
    if code == 0 and not timed_out and 'PROBE: completed' in streams['stdout'] and kinds == {'prefix', 'turn'}:
        record['status'] = 'PASS'
    else:
        record['reason'] = 'Incomplete process lifecycle or missing nonempty prefix/turn events'
    record['scope'] = 'Capture integrity only. Event semantics, tokenizer and schema-span accounting are not certified.'
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, required=True)
    parser.add_argument('--manifest', default='data/spike-mlx/manifests/frozen-200.jsonl')
    parser.add_argument('--labels', default='oracle/labels-v1.json')
    parser.add_argument('--weights', default='data/spike-mlx/oracle-10k-qat.cact')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--counts', type=int, nargs='+', default=[1, 5, 6, 10, 44])
    parser.add_argument('--rows', type=int, nargs='+', default=[0, 1, 7])
    parser.add_argument('--timeout', type=float, default=60)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=False)
    rows = [line.strip() for line in Path(args.manifest).read_text().splitlines() if line.strip()]
    schemas = json.loads(Path(args.labels).read_text())['schemas']
    if not rows or args.timeout <= 0 or any(i < 0 or i >= len(rows) for i in args.rows):
        parser.error('nonempty manifest, valid row indexes and positive timeout required')
    if len(set(args.counts)) != len(args.counts) or len(set(args.rows)) != len(args.rows) or any(n < 1 or n > len(schemas) for n in args.counts):
        parser.error('counts/rows must be unique and tool counts valid')
    from audit_round import digest
    inputs = {name: {'path': str(Path(path).resolve()), 'sha256': digest(path)}
              for name, path in {'manifest': args.manifest, 'labels': args.labels, 'weights': args.weights}.items()}
    env = dict(os.environ, NEEDLE_DEBUG='1', HF_HUB_DISABLE_XET='1', NEEDLE_TELEMETRY='0')
    receipts = []
    for n in args.counts:
        for index in args.rows:
            command = [args.python, '-c', CHILD, str(n), str(index), args.manifest, args.labels, args.weights]
            record = capture(command, env, args.timeout)
            record.update({'inputs': inputs, 'row_index': index,
                           'row_sha1': hashlib.sha1(rows[index].encode()).hexdigest(),
                           'declared_names': [s['name'] for s in schemas[:n]]})
            path = args.outdir / f'tools-{n}-row-{index}.json'
            with path.open('x') as target:
                json.dump(record, target, indent=2)
            receipts.append({'receipt': path.name, 'status': record['status']})
            print(f"{n} tools, row {index}: {record['status']} ({path})", flush=True)
    status = 'PASS' if all(r['status'] == 'PASS' for r in receipts) else 'INCOMPLETE'
    (args.outdir / 'index.json').write_text(json.dumps({'status': status, 'receipts': receipts}, indent=2))
    return 0 if status == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
