"""Reproduce #52 from retained private inputs; prints aggregate + per-case JSON.

Run from any directory. Redirect stdout only to an ignored/private location:
the per_case section contains quiz inputs. No training/generation or gate changes.
"""
import collections
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spike/coding_core'))
import baselines
import context_probe as probe

PANEL = ROOT / 'data/next-action-panel-v1'
SOURCE = ROOT / 'data/context-next-action-2026-09-12-score'
SEATS = ('fable', 'glm', 'astra', 'gemini', 'deepseek', 'qwen', 'tencent')
HOLDOUT_SHA = '6663c93e5810c12724dbbf60be16d107881e1d7c3eb9e19497262dde6214884d'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def predictions(payload, ids):
    rows = payload['response']['predictions']
    if len(rows) != len(ids) or {r['case_id'] for r in rows} != set(ids):
        raise ValueError('missing, duplicate, or unknown case')
    by_id = {r['case_id']: r['predicted_action'] for r in rows}
    if any(v not in probe.LABELS for v in by_id.values()):
        raise ValueError('invalid prediction label')
    return [by_id[cid] for cid in ids]


def controls():
    ids = ['a', 'b']
    for bad in ([], [{'case_id': 'a', 'predicted_action': 'read'}] * 2,
                [{'case_id': i, 'predicted_action': 'fake'} for i in ids]):
        try:
            predictions({'response': {'predictions': bad}}, ids)
        except ValueError:
            continue
        raise AssertionError('malformed-input control did not fail')
    rows = [{'target': 'read', 'history': ['edit'], 'issue': 'a'},
            {'target': 'edit', 'history': ['read'], 'issue': 'b'}]
    assert probe.metrics(rows, ['read', 'edit'])['accuracy_pct'] == 100
    assert probe.metrics(rows, ['edit', 'read'])['accuracy_pct'] == 0
    for r, p in (([], []), (rows, ['read'])):
        try:
            probe.metrics(r, p)
        except ValueError:
            continue
        raise AssertionError('empty/mismatched metric control did not fail')


def main():
    controls()
    manifest = read(PANEL / 'private-manifest.json')
    quiz = read(PANEL / 'quiz.json')
    key = manifest['answer_key']
    assert len(quiz) == len(key) == 30
    assert digest(SOURCE / 'holdout.jsonl') == manifest['source_sha256'] == HOLDOUT_SHA
    holdout = [json.loads(l) for l in (SOURCE / 'holdout.jsonl').read_text().splitlines()]
    train = [json.loads(l) for l in (SOURCE / 'train.jsonl').read_text().splitlines()]
    assert len(holdout) == 3000 and len(train) == 10000
    assert len({r['issue'] for r in train}) == 224
    assert not {r['issue'] for r in train} & {r['issue'] for r in holdout}
    # Reproduce the original target-blind selection, not just the manifest's targets.
    seed = manifest['selection']
    rank = lambda s: hashlib.sha256((seed + ':' + s).encode()).hexdigest()
    groups = collections.defaultdict(list)
    for n, r in enumerate(holdout):
        groups[r['issue']].append(n)
    expected = [min(groups[i], key=lambda n: rank(i + ':' + str(n)))
                for i in sorted(groups, key=rank)[:30]]
    rows = []
    for pos, (q, k, n) in enumerate(zip(quiz, key, expected), 1):
        r = holdout[n]
        assert q['case_id'] == k['case_id'] == f'case-{pos:02d}'
        assert k['source_line'] == n + 1 and k['issue'] == r['issue']
        assert k['target'] == r['target']
        assert q == {'case_id': k['case_id'], **{f: r[f] for f in ('task', 'history', 'observation')}}
        rows.append(r)
    assert len({r['issue'] for r in rows}) == 30
    ids = [q['case_id'] for q in quiz]
    receipts = {s: read(PANEL / (s + '-locked.json')) for s in SEATS}
    for seat, receipt in receipts.items():
        source = Path(receipt['source'])
        if not source.is_absolute():
            source = ROOT / source
        raw = source.read_text()
        if 'turn_sha256' in receipt:
            body = raw.split('### Turn 2 — agent2 —', 1)[1].split('\n### Turn 3', 1)[0]
            assert hashlib.sha256(body.encode()).hexdigest() == receipt['turn_sha256']
            original = json.loads(re.search(r'```json\n(.*?)\n```', body, re.S).group(1))
        else:
            assert digest(source) == receipt['transcript_sha256']
            body = raw.rsplit('► **ANSWER**', 1)[-1]
            found = []
            decoder = json.JSONDecoder(strict=False)
            for n, c in enumerate(body):
                if c != '{':
                    continue
                try:
                    obj, _ = decoder.raw_decode(body[n:])
                except ValueError:
                    continue
                if isinstance(obj, dict) and isinstance(obj.get('predictions'), list):
                    found.append(obj)
            assert found and all(x == found[0] for x in found)
            original = found[0]
        assert original == receipt['response'], 'locked response differs from source'
    output = {s: predictions(v, ids) for s, v in receipts.items()}
    model = baselines.fit([(r['issue'], tuple(r['history']), r['target']) for r in train])
    names = tuple(baselines.predict(model, rows[0]['history']))
    previous = read(SOURCE / 'result.json')
    for module in (baselines, probe):
        p = Path(module.__file__)
        assert digest(p) == previous['code_sha256'][p.name]
    # Replay the four unchanged baselines on the original holdout as an anchor.
    anchor = {}
    for name in names:
        full = [baselines.predict(model, r['history'])[name] for r in holdout]
        anchor[name] = probe.metrics(holdout, full)['correct']
        assert anchor[name] == previous['metrics'][name]['correct']
        output['baseline_' + name] = [baselines.predict(model, r['history'])[name] for r in rows]
    scores = {name: probe.metrics(rows, p) for name, p in output.items()}
    # Independent arithmetic: confusion counts, without calling probe.metrics.
    for name, preds in output.items():
        confusion = collections.Counter(zip((r['target'] for r in rows), preds))
        correct = sum(confusion[y, y] for y in probe.LABELS)
        assert scores[name]['correct'] == correct
        f1 = sum(2 * confusion[y, y] / max(1, sum(v for (a, b), v in confusion.items() if a == y)
                     + sum(v for (a, b), v in confusion.items() if b == y)) for y in probe.LABELS) / 6
        assert abs(f1 - scores[name]['macro_f1']) < 1e-12
    target_counts = collections.Counter(r['target'] for r in rows)
    for name, preds in output.items():
        # Exact expectation under a random permutation of fixed predictions.
        counts = collections.Counter(preds)
        scores[name]['permutation_null_expected_accuracy_pct'] = 100 * sum(
            counts[y] * target_counts[y] for y in probe.LABELS) / 30**2
    per_case = [dict(q, target=r['target'], predictions={n: p[i] for n, p in output.items()})
                for i, (q, r) in enumerate(zip(quiz, rows))]
    unanimous = [i for i in range(30) if len({output[s][i] for s in SEATS}) == 1]
    all_wrong = [i for i in range(30) if all(output[s][i] != rows[i]['target'] for s in SEATS)]
    aggregates = dict(issue=52, cases=30, issues=30, seats=7, predictions=210,
        train_rows=10000, train_issues=224, label_support={y: target_counts[y] for y in probe.LABELS},
        scores=scores, baseline_original_holdout_correct=anchor,
        unanimous_rows=len(unanimous), unanimous_correct=sum(output[SEATS[0]][i] == rows[i]['target'] for i in unanimous),
        all_seven_wrong_rows=len(all_wrong), at_least_one_model_correct_rows=30-len(all_wrong),
        validation='Source digest, selection replay, input/key alignment, disjoint training, 210 predictions, original baseline replay, malformed-input controls, 100-to-0 scorer control, independent confusion arithmetic passed.',
        limitations='Reused 30-issue development sample; mapped observed actions, not preferred actions or human usefulness. Unequal harnesses and model attestation. No ensemble selection or milestone promotion.',
        hashes={str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), Path(baselines.__file__), Path(probe.__file__), SOURCE/'train.jsonl', SOURCE/'holdout.jsonl', PANEL/'quiz.json'] + [PANEL/(s+'-locked.json') for s in SEATS]})
    print(json.dumps(dict(aggregates=aggregates, per_case=per_case), indent=2))


if __name__ == '__main__':
    main()
