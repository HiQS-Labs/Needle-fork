"""Offline evidence gates for #14. No model imports, inference, or network.

python spike/mlx/audit_round.py --config /private/round.json --outdir /private/new-report
Paths in the configuration resolve relative to that configuration, not the shell CWD.
See doc/experiment-rounds.md for the configuration and interpretation contract.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from oracle_scoring import parse_mlx_text, parse_native

STATUSES = {'ok', 'abstain', 'malformed', 'multiple_calls', 'undeclared', 'error'}

# A gate this script CAN decide vs. one only a reviewer can close. Without this split every
# open gate reads as the same word, and "a human has not looked yet" is indistinguishable
# from "evidence is missing". Overall PASS stays unreachable while any review gate is open;
# that is the point, so `deterministic_status` exists to carry the signal a script can earn.
GATE_KIND = {'G0_inputs': 'deterministic', 'G1_identity': 'deterministic',
             'G2_raw_scoring': 'deterministic', 'G3_serving': 'review',
             'G4_arithmetic': 'deterministic', 'G5_inference': 'review',
             'G6_review': 'review'}


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_jsonl(path):
    with open(path) as source:
        return [(line.strip(), json.loads(line)) for line in source if line.strip()]


def mcnemar(b, c):
    """Exact, two-sided conditional binomial tail (independent row-pair assumption)."""
    n = b + c
    if not n:
        return 1.0
    # lgamma avoids overflow for large row sets. Sum only the shorter tail.
    log2 = math.log(2)
    tail = math.fsum(math.exp(math.lgamma(n + 1) - math.lgamma(k + 1)
                             - math.lgamma(n - k + 1) - n * log2)
                     for k in range(min(b, c) + 1))
    return min(1.0, 2 * tail)


def paired(a, b):
    if len(a) != len(b) or not a:
        raise ValueError('paired inputs must have equal nonzero length')
    both = sum(x and y for x, y in zip(a, b))
    left = sum(x and not y for x, y in zip(a, b))
    right = sum(y and not x for x, y in zip(a, b))
    return {'n': len(a), 'both_correct': both, 'a_only': left, 'b_only': right,
            'neither': len(a) - both - left - right,
            'difference_pp': 100 * (left - right) / len(a),
            'exact_mcnemar_p_assuming_independent_pairs': mcnemar(left, right)}


def audit(config, root):
    gates = {name: {'status': 'INCOMPLETE', 'reasons': ['Not evaluated']} for name in
             ('G0_inputs', 'G1_identity', 'G2_raw_scoring', 'G3_serving',
              'G4_arithmetic', 'G5_inference', 'G6_review')}
    report = {'format_version': 1, 'round_id': config.get('round_id'),
              'gates': gates, 'metrics': {}, 'comparisons': [], 'input_sha256': {},
              'analysis_sha256': {p.name: digest(p) for p in
                                  (Path(__file__), Path(__file__).with_name('oracle_scoring.py'))}}
    pinned_paths = {}
    gates['G0_inputs'] = {'status': 'PASS', 'reasons': []}

    def note(gate, status, reason):
        item = gates[gate]
        if {'PASS': 0, 'INCOMPLETE': 1, 'FAIL': 2}[status] > {'PASS': 0, 'INCOMPLETE': 1, 'FAIL': 2}[item['status']]:
            item['status'] = status
        item['reasons'].append(reason)

    def pinned(spec, label):
        if not isinstance(spec, dict) or not spec.get('path') or not spec.get('sha256'):
            note('G0_inputs', 'INCOMPLETE', label + ': path and full sha256 required')
            return None
        path = root / spec['path']
        if not path.is_file():
            note('G0_inputs', 'INCOMPLETE', label + ': file missing')
            return None
        actual = digest(path)
        report['input_sha256'][label] = actual
        if actual != spec['sha256']:
            note('G0_inputs', 'FAIL', label + ': hash mismatch')
            return None
        pinned_paths[label] = path
        return path

    for field in ('round_id', 'question', 'population', 'falsifier', 'time_cap', 'comparisons'):
        if not config.get(field):
            note('G0_inputs', 'INCOMPLETE', 'missing protocol field: ' + field)
    if config.get('format_version') != 1:
        note('G0_inputs', 'FAIL', 'unsupported configuration version')
    manifest = pinned(config.get('manifest'), 'manifest')
    taxonomy = pinned(config.get('taxonomy'), 'taxonomy')
    training = pinned(config.get('training'), 'training')
    if not manifest or not taxonomy or not training:
        return finish(report)
    try:
        labels = set(json.loads(taxonomy.read_text())['labels'])
        source = read_jsonl(manifest)
        expected = config['manifest'].get('expected_n')
        ids = [hashlib.sha1(raw.encode()).hexdigest() for raw, _ in source]
        gold = [row['answers'][0]['name'] for _, row in source]
        if not source or type(expected) is not int or expected != len(source):
            raise ValueError('manifest must be nonempty and match integer expected_n')
        if len(set(ids)) != len(ids) or not labels or not set(gold) <= labels:
            raise ValueError('duplicate manifest IDs or invalid taxonomy/gold')
        train_rows = read_jsonl(training)
        counts = Counter(row['answers'][0]['name'] for _, row in train_rows)
        if not counts or not set(counts) <= labels:
            raise ValueError('training labels empty or outside taxonomy')
        # Selecting the comparator from data it is later scored on is the exact error that
        # produced a withdrawn #12 claim (LESSONS-LEARNED #2). Pinning a file named
        # "training" does not make it disjoint, so measure it instead of trusting the name.
        # Query-level catches a re-serialised duplicate that an exact line hash would miss.
        exact = len(set(ids) & {hashlib.sha1(raw.encode()).hexdigest() for raw, _ in train_rows})
        train_q = {json.dumps(row['query'], sort_keys=True) for _, row in train_rows if 'query' in row}
        query = sum('query' in row and json.dumps(row['query'], sort_keys=True) in train_q
                    for _, row in source)
        report['baseline_fit_leakage'] = {'exact_row_overlap': exact, 'query_overlap': query,
                                          'evaluation_n': len(source), 'training_n': len(train_rows)}
        if exact or query:
            raise ValueError(f'baseline-fitting file overlaps the evaluation manifest '
                             f'({exact} identical rows, {query} identical queries)')
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        note('G0_inputs', 'FAIL', str(exc))
        return finish(report)
    # Lexical tie break is explicit; fitting never sees evaluation targets.
    baseline = min(counts, key=lambda label: (-counts[label], label))
    correct = {'training_majority': [g == baseline for g in gold]}
    report['baseline'] = {'label': baseline, 'training_count': counts[baseline],
                          'evaluation_correct': sum(correct['training_majority']),
                          'n': len(gold), 'tie_break': 'lexical label ascending'}
    report['gold_support'] = dict(sorted(Counter(gold).items()))
    for gate in ('G1_identity', 'G2_raw_scoring', 'G4_arithmetic'):
        gates[gate] = {'status': 'PASS', 'reasons': []}
    seen = set()
    if not config.get('arms'):
        note('G1_identity', 'FAIL', 'no arms')
    for arm in config.get('arms', []):
        name = arm.get('name')
        if not isinstance(name, str) or not name or name in seen or name == 'training_majority':
            note('G1_identity', 'FAIL', 'invalid/duplicate/reserved arm name')
            continue
        seen.add(name)
        path = pinned(arm, name)
        if not path:
            continue
        try:
            rows = [r for _, r in read_jsonl(path)]
            by_id = {r['sha1']: r for r in rows}
            if len(by_id) != len(rows) or set(by_id) != set(ids):
                raise ValueError('missing, duplicate, or extra row IDs')
            rows = [by_id[h] for h in ids]
            declared = arm.get('declared')
            if not isinstance(declared, list) or not declared or len(set(declared)) != len(declared) or not set(declared) <= labels:
                raise ValueError('declared must be a unique nonempty canonical label list')
            declared = set(declared)
            for r, g in zip(rows, gold):
                if r['gold'] != g or r['status'] not in STATUSES:
                    raise ValueError('gold/status mismatch')
                if r['status'] == 'ok' and r['pred'] not in declared:
                    raise ValueError('OK prediction is not declared')
                if r['status'] == 'undeclared' and (not isinstance(r.get('pred'), str) or r['pred'] in declared):
                    raise ValueError('undeclared prediction is missing or actually declared')
                if r['status'] not in ('ok', 'undeclared') and r.get('pred') is not None:
                    raise ValueError('invalid status/prediction combination')
        except (KeyError, TypeError, ValueError) as exc:
            note('G1_identity', 'FAIL', name + ': ' + str(exc))
            continue
        result = [r['status'] == 'ok' and r['pred'] == g for r, g in zip(rows, gold)]
        correct[name] = result
        reachable = [i for i, g in enumerate(gold) if g in declared]
        report['metrics'][name] = {'n': len(rows), 'correct': sum(result),
                                  'top1_pct': 100 * sum(result) / len(rows),
                                  'within_subset_n': len(reachable),
                                  'within_subset_correct': sum(result[i] for i in reachable),
                                  'status_counts': dict(sorted(Counter(r['status'] for r in rows).items()))}
        replayable = [r for r in rows if 'raw' in r and r['status'] != 'error']
        missing_raw = len(rows) - len(replayable)
        for r in replayable:
            try:
                if arm.get('runtime') == 'engine':
                    v = parse_native(json.loads(r['raw']), declared)
                elif arm.get('runtime') == 'mlx':
                    v = parse_mlx_text(r['raw'], declared)
                else:
                    raise ValueError('runtime must be engine or mlx')
                if (v.pred, v.status) != (r['pred'], r['status']):
                    raise ValueError('raw reparse disagrees with saved verdict')
            except (ValueError, TypeError) as exc:
                note('G2_raw_scoring', 'FAIL', name + ': ' + str(exc))
                break
        if missing_raw:
            note('G2_raw_scoring', 'INCOMPLETE', f'{name}: {missing_raw} rows lack replayable model output (including runtime errors)')
        # Metadata cannot be reconstructed from an artifact nickname.
        metadata = pinned(arm.get('run_metadata'), name + '.run_metadata')
        if metadata:
            meta = json.loads(metadata.read_text())
            if not meta.get('completed') or meta.get('rows_sha256') != digest(path):
                note('G1_identity', 'FAIL', name + ': run did not complete or row hash differs')
            inputs = meta.get('inputs', {})
            if inputs.get('manifest', {}).get('sha256') != digest(manifest):
                note('G1_identity', 'FAIL', name + ': run manifest hash differs')
            for key in ('artifact', 'labels'):
                if not inputs.get(key, {}).get('sha256'):
                    note('G0_inputs', 'INCOMPLETE', name + ': metadata missing ' + key)
            if meta.get('runtime') != arm.get('runtime'):
                note('G1_identity', 'FAIL', name + ': runtime metadata differs')
            if inputs.get('labels', {}).get('sha256') != digest(taxonomy):
                note('G1_identity', 'FAIL', name + ': taxonomy metadata differs')
            if meta.get('declared_names') != sorted(declared):
                note('G0_inputs', 'INCOMPLETE', name + ': effective declaration unverified')
            if arm.get('runtime') == 'mlx' and (type(meta.get('qat')) is not bool or not inputs.get('checkpoint', {}).get('sha256')):
                note('G0_inputs', 'INCOMPLETE', name + ': MLX quantization/checkpoint configuration unverified')
        else:
            note('G2_raw_scoring', 'INCOMPLETE', name + ': effective run configuration unavailable')
    for comparison in config.get('comparisons', []):
        if not isinstance(comparison, list) or len(comparison) != 2 or comparison[0] == comparison[1] or any(x not in correct for x in comparison):
            note('G4_arithmetic', 'FAIL', 'comparison must name two distinct validated arms/baseline')
            continue
        a, b = comparison
        report['comparisons'].append({'a': a, 'b': b, **paired(correct[a], correct[b])})
    report['multiplicity'] = {'n_comparisons': len(report['comparisons']),
                              'adjustment': 'none applied; p-values are unadjusted and exploratory'}
    if not report['comparisons']:
        note('G4_arithmetic', 'INCOMPLETE', 'No valid paired comparisons')
    if not report['metrics']:
        note('G2_raw_scoring', 'INCOMPLETE', 'No validated arms to reparse')
    # Presence of a claim or a file is not semantic verification of a closed binary.
    note('G3_serving', 'INCOMPLETE', 'Decoded serving spans and effective engine/tokenizer/position semantics require an independently reviewed trace receipt; counts alone do not pass.')
    note('G5_inference', 'INCOMPLETE', 'Row-level p-values are conditional arithmetic, not certified population inference. Session/sampling provenance, multiplicity and effect-size/uncertainty design need review.')
    note('G6_review', 'INCOMPLETE', 'Human/agent review must scope claims, preserve D7 and dissent, and select a bounded next experiment or stop. No automatic deployment/retrain verdict.')
    for label, path in pinned_paths.items():
        if digest(path) != report['input_sha256'][label]:
            note('G0_inputs', 'FAIL', label + ': input changed during analysis')
    return finish(report)


def finish(report):
    gates = report['gates']
    for name, gate in gates.items():
        gate['kind'] = GATE_KIND[name]
    statuses = [g['status'] for g in gates.values()]
    report['status'] = 'FAIL' if 'FAIL' in statuses else 'INCOMPLETE' if 'INCOMPLETE' in statuses else 'PASS'
    # What the deterministic half of the audit actually earned, reported separately so an
    # always-open review gate cannot hide a clean -- or a broken -- arithmetic result.
    machine = [g['status'] for g in gates.values() if g['kind'] == 'deterministic']
    report['deterministic_status'] = ('FAIL' if 'FAIL' in machine
                                      else 'INCOMPLETE' if 'INCOMPLETE' in machine else 'PASS')
    # FAIL before INCOMPLETE. Routing purely by gate order sent every contradiction to
    # whichever earlier gate merely lacked a receipt -- and G0 lacks one on every legacy
    # arm, so a real G4 failure was never the reported next action.
    failed = [k for k, v in gates.items() if v['status'] == 'FAIL']
    incomplete = [k for k, v in gates.items() if v['status'] == 'INCOMPLETE']
    blockers = failed + incomplete
    report['blocked_gates'] = {'fail': failed, 'incomplete': incomplete}
    report['next_action'] = {'kind': 'repair' if failed else 'repair_or_review' if blockers else 'review',
                             'gate': blockers[0] if blockers else None,
                             'instruction': 'Resolve the first blocked prerequisite or explicitly stop; do not infer authorization for a new campaign.'}
    return report


def markdown(report):
    lines = ['# Experimental round audit', '', '**Disposition: ' + report['status'] + '**', '',
             'This report verifies frozen-file arithmetic, not model usefulness or causal explanations.', '',
             'Deterministic gates only: **' + report.get('deterministic_status', 'UNKNOWN') + '**. '
             'Review gates stay open until a person closes them, so overall PASS is unreachable here by design.', '',
             '| Gate | Kind | Status | Reasons |', '| --- | --- | --- | --- |']
    for name, gate in report['gates'].items():
        reasons = '; '.join(gate['reasons']).replace('|', '/').replace('\n', ' ')
        lines.append(f"| {name} | {gate.get('kind', '?')} | {gate['status']} | {reasons or 'Structural checks passed'} |")
    lines += ['', '## Paired descriptive results', '',
              'Exact p-values below assume independent row pairs; session dependence is unresolved. '
              + json.dumps(report.get('multiplicity', {})), '',
              '| A | B | n | A-only | B-only | Difference pp | Conditional exact p |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for row in report['comparisons']:
        lines.append(f"| {row['a']} | {row['b']} | {row['n']} | {row['a_only']} | {row['b_only']} | {row['difference_pp']:.3f} | {row['exact_mcnemar_p_assuming_independent_pairs']:.8g} |")
    lines += ['', 'Next action: ' + json.dumps(report['next_action'], sort_keys=True), '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()
    # Reserve a new output directory before doing any work; never overwrite evidence.
    args.outdir.mkdir(parents=True, exist_ok=False)
    try:
        config = json.loads(args.config.read_text())
        report = audit(config, args.config.resolve().parent)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        report = {'format_version': 1, 'status': 'FAIL', 'gates': {'G0_inputs': {
            'status': 'FAIL', 'reasons': [type(exc).__name__ + ': ' + str(exc)]}},
                  'comparisons': [], 'next_action': {'kind': 'repair', 'gate': 'G0_inputs'}}
    (args.outdir / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    (args.outdir / 'SUMMARY.md').write_text(markdown(report))
    if args.config.is_file():
        (args.outdir / 'round.json').write_bytes(args.config.read_bytes())
    print(f"{report['status']}: {args.outdir / 'SUMMARY.md'}")
    return {'PASS': 0, 'FAIL': 1, 'INCOMPLETE': 2}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
