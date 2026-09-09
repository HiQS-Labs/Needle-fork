"""Negative evidence controls for #14; no native/model inference."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

SPIKE = Path(__file__).resolve().parents[1] / 'spike' / 'mlx'
# These gates are spike-scoped: the modules live outside the packaged `needle*` tree.
# `tests/` is the release train's gate (pyproject testpaths, release.yaml), so a missing
# spike directory must skip, never fail the release.
# Skip only when the whole spike is absent -- a branch that does not carry it. If the
# directory EXISTS but the module is gone, that is the feature being deleted out from
# under its own tests, and it must fail loudly (agent2, #729301). A guard that goes green
# when the thing it guards disappears is the defect this suite exists to catch.
if not SPIKE.is_dir():
    pytest.skip('spike/mlx absent on this branch; #14 gates are spike-scoped',
                allow_module_level=True)
sys.path.insert(0, str(SPIKE))
import audit_round as audit
import kv_verify
import oracle_scoring as scoring


def pin(path, **extra):
    return {'path': str(path), 'sha256': audit.digest(path), **extra}


@pytest.fixture
def frozen(tmp_path):
    labels = tmp_path / 'labels.json'
    labels.write_text(json.dumps({'labels': {'a': {}, 'b': {}}}))
    manifest = tmp_path / 'manifest.jsonl'
    records = [{'query': str(i), 'answers': [{'name': g}]} for i, g in enumerate(['a', 'b', 'b', 'a'])]
    lines = [json.dumps(r) for r in records]
    manifest.write_text('\n'.join(lines) + '\n')
    train = tmp_path / 'train.jsonl'
    train.write_text('\n'.join(json.dumps({'query': f'train-{i}', 'answers': [{'name': 'b'}]})
                               for i in range(3)))
    rows = tmp_path / 'rows.jsonl'
    receipts = [{'sha1': hashlib.sha1(line.encode()).hexdigest(), 'gold': r['answers'][0]['name'],
                 'status': 'ok', 'pred': g,
                 'raw': '<tool_call>' + json.dumps([{'name': g, 'arguments': {}}]) + '</tool_call>'}
                for line, r, g in zip(lines, records, ['a', 'a', 'b', 'a'])]
    rows.write_text('\n'.join(json.dumps(r) for r in receipts) + '\n')
    meta = tmp_path / 'run.json'
    meta.write_text(json.dumps({'completed': True, 'runtime': 'mlx', 'qat': False,
                               'declared_names': ['a', 'b'], 'rows_sha256': audit.digest(rows),
                               'inputs': {'manifest': pin(manifest), 'labels': pin(labels),
                                          'checkpoint': pin(train), 'artifact': pin(train)}}))
    config = {'format_version': 1, 'round_id': 'synthetic', 'question': 'paired control',
              'population': 'synthetic', 'falsifier': 'mismatch', 'time_cap': 'one minute',
              'manifest': pin(manifest, expected_n=4), 'taxonomy': pin(labels), 'training': pin(train),
              'arms': [pin(rows, name='model', runtime='mlx', declared=['a', 'b'], run_metadata=pin(meta))],
              'comparisons': [['model', 'training_majority']]}
    return config, tmp_path


def rewrite_rows(config, mutate):
    path = Path(config['arms'][0]['path'])
    rows = [r for _, r in audit.read_jsonl(path)]
    mutate(rows)
    path.write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    config['arms'][0]['sha256'] = audit.digest(path)


def test_repeatable_arithmetic_does_not_certify_inference(frozen):
    config, root = frozen
    a = audit.audit(config, root)
    assert a == audit.audit(config, root)
    assert a['baseline']['label'] == 'b'
    assert a['metrics']['model']['correct'] == 3
    assert a['comparisons'][0]['a_only'] == 2
    assert a['comparisons'][0]['b_only'] == 1
    for gate in ('G0_inputs', 'G1_identity', 'G2_raw_scoring', 'G4_arithmetic'):
        assert a['gates'][gate]['status'] == 'PASS'
    assert a['status'] == 'INCOMPLETE'
    assert a['gates']['G5_inference']['status'] == 'INCOMPLETE'


@pytest.mark.parametrize('mutate', [lambda rows: rows.pop(), lambda rows: rows.append(rows[0]),
                                  lambda rows: rows[0].update(sha1='wrong'),
                                  lambda rows: rows[0].update(gold='b'),
                                  lambda rows: rows[0].update(pred='outside')])
def test_corrupted_pairs_fail(frozen, mutate):
    config, root = frozen
    rewrite_rows(config, mutate)
    result = audit.audit(config, root)
    assert result['gates']['G1_identity']['status'] == 'FAIL'
    assert result['comparisons'] == []


def test_hash_and_empty_controls(frozen):
    config, root = frozen
    Path(config['manifest']['path']).write_text('')
    assert audit.audit(config, root)['gates']['G0_inputs']['status'] == 'FAIL'
    config['manifest']['sha256'] = audit.digest(config['manifest']['path'])
    assert audit.audit(config, root)['gates']['G0_inputs']['status'] == 'FAIL'


def test_missing_raw_is_not_replay_success(frozen):
    config, root = frozen
    rewrite_rows(config, lambda rows: rows[0].pop('raw'))
    assert audit.audit(config, root)['gates']['G2_raw_scoring']['status'] == 'INCOMPLETE'


def test_saved_verdict_cannot_override_raw(frozen):
    config, root = frozen
    rewrite_rows(config, lambda rows: rows[0].update(raw='<think>a</think>'))
    assert audit.audit(config, root)['gates']['G2_raw_scoring']['status'] == 'FAIL'


def test_statistics_hand_calculated():
    assert audit.mcnemar(0, 0) == 1
    assert audit.mcnemar(4, 0) == pytest.approx(0.125)
    assert audit.mcnemar(2, 8) == pytest.approx(0.109375)
    assert audit.mcnemar(61, 1) == pytest.approx(2.7321894746634712e-17, rel=1e-10, abs=0)
    result = audit.paired([True, True, False, False], [True, False, True, False])
    assert (result['both_correct'], result['a_only'], result['b_only'], result['neither']) == (1, 1, 1, 1)
    assert result['difference_pp'] == 0
    with pytest.raises(ValueError):
        audit.paired([], [])


@pytest.mark.parametrize('payload', [
    '<think>"name":"a"</think>',
    '<tool_call>[{"name":"a"}',
    '<tool_call>[{"name":"a"}]</tool_call><tool_call>[{"name":"b"}]</tool_call>',
    '<tool_call>[{"name":"a"}]</tool_call><tool_call>',
    '<tool_call>[{"name":"a","arguments":123}]</tool_call>',
    '<tool_call>[{"name":"a","arguments":null}]</tool_call>',
    '<tool_call>[{"name":"a","name":"b"}]</tool_call>',
])
def test_scoring_false_positive_controls(payload):
    assert scoring.parse_mlx_text(payload, {'a', 'b'}).status != 'ok'


def test_good_outputs_and_full_raw_preserved():
    raw = '<think>' + 'x' * 500 + '</think><tool_call>[{"name":"a","arguments":{}}]</tool_call>'
    assert scoring.parse_mlx_text(raw, {'a'}).raw == raw
    assert scoring.parse_mlx_text(raw, {'a'}).status == 'ok'
    assert scoring.parse_native({'function_calls': [{'name': 'a', 'arguments': 123}]}, {'a'}).status == 'malformed'
    assert scoring.parse_native({'function_calls': [{'name': 'a', 'arguments': {}}]}, {'a'}).status == 'ok'


def test_debug_logits_are_not_retrieved_tools():
    text = '[debug] top5: 12 34 56\n[debug] prefix ids: 1 2\n[debug] prefix ids: 3\n[debug] turn ids: 4 5\n'
    events = kv_verify.extract_ids(text)
    assert [e['ids'] for e in events] == [[1, 2], [3], [4, 5]]
    with pytest.raises(ValueError):
        kv_verify.extract_ids('[debug] turn ids: 1 2 broken\n')


@pytest.mark.parametrize('code,expected', [
    ("print('[debug] prefix ids: 1 2'); print('[debug] turn ids: 3'); print('PROBE: completed')", 'PASS'),
    ("print('[debug] prefix ids: 1 2'); print('PROBE: completed')", 'INCOMPLETE'),
    ("print('PROBE: completed'); raise SystemExit(3)", 'INCOMPLETE'),
    ("import time; time.sleep(1)", 'INCOMPLETE'),
])
def test_capture_lifecycle(code, expected):
    result = kv_verify.capture([sys.executable, '-c', code], {}, 0.3)
    assert result['status'] == expected


def test_cli_exit_codes_and_overwrite(frozen):
    config, root = frozen
    source = root / 'round.json'
    source.write_text(json.dumps(config))
    output = root / 'report'
    command = [sys.executable, str(SPIKE / 'audit_round.py'), '--config', str(source), '--outdir', str(output)]
    first = subprocess.run(command, capture_output=True)
    assert first.returncode == 2
    retained = (output / 'report.json').read_bytes()
    second = subprocess.run(command, capture_output=True)
    assert second.returncode != 0
    assert (output / 'report.json').read_bytes() == retained
    config['manifest']['expected_n'] = 200
    source.write_text(json.dumps(config))
    command[-1] = str(root / 'bad-report')
    assert subprocess.run(command, capture_output=True).returncode == 1


@pytest.mark.parametrize('crash', [False, True])
def test_new_eval_retains_rows_and_refuses_overwrite(frozen, monkeypatch, crash):
    import run_eval
    config, root = frozen
    taxonomy = Path(config['taxonomy']['path'])
    taxonomy.write_text(json.dumps({'labels': {'a': {}, 'b': {}},
                                    'schemas': [{'name': 'a'}, {'name': 'b'}]}))
    artifact = root / 'synthetic.cact'
    artifact.write_bytes(b'fixture only; never loaded by a model')

    def fake_engine(args, rows, labels, tools):
        results = []
        for h, row in rows:
            verdict = scoring.parse_native({'function_calls': [{'name': row['answers'][0]['name']}]}, labels)
            run_eval.save_row(args, h, row, verdict)
            results.append((h, row, verdict))
            if crash:
                raise RuntimeError('injected collection failure')
        return results

    monkeypatch.setattr(run_eval, 'run_engine', fake_engine)
    argv = ['run_eval.py', '--runtime', 'engine', '--cact', str(artifact),
            '--manifest', config['manifest']['path'], '--labels', str(taxonomy),
            '--tag', 'test', '--outdir', str(root / 'new-eval')]
    monkeypatch.setattr(sys, 'argv', argv)
    if crash:
        with pytest.raises(RuntimeError, match='injected'):
            run_eval.main()
    else:
        run_eval.main()
    output = root / 'new-eval' / 'engine-test'
    meta = json.loads((output / 'run.json').read_text())
    assert meta['completed'] == (not crash)
    assert len(audit.read_jsonl(output / 'rows.jsonl')) == (1 if crash else 4)
    retained = (output / 'rows.jsonl').read_bytes()
    with pytest.raises(FileExistsError):
        run_eval.main()
    assert (output / 'rows.jsonl').read_bytes() == retained


def test_baseline_fitting_file_must_not_contain_evaluation_rows(frozen):
    """RED CONTROL: leak one evaluation row into the baseline-fitting file.

    Selecting a comparator from data it is later scored against is the error behind a
    withdrawn #12 claim. Pinning a path called "training" is not evidence it is disjoint,
    so the gate must FAIL on measured overlap rather than trust the filename.
    """
    config, root = frozen
    assert audit.audit(config, root)['gates']['G0_inputs']['status'] == 'PASS'
    training = Path(config['training']['path'])
    leaked = Path(config['manifest']['path']).read_text().splitlines()[0]
    training.write_text(training.read_text().rstrip('\n') + '\n' + leaked + '\n')
    config['training']['sha256'] = audit.digest(training)
    result = audit.audit(config, root)
    assert result['gates']['G0_inputs']['status'] == 'FAIL'
    assert 'overlaps the evaluation manifest' in ' '.join(result['gates']['G0_inputs']['reasons'])
    assert result['comparisons'] == []


def test_a_contradiction_outranks_a_missing_receipt_when_routing(frozen):
    """RED CONTROL: a real FAIL must be the routed next action, not an earlier INCOMPLETE.

    Routing by gate order alone always named G0, which is INCOMPLETE on every legacy arm
    for want of run metadata -- so a genuine G4 contradiction was never reported as the
    thing to fix.
    """
    config, root = frozen
    config['arms'][0].pop('run_metadata')                 # G0 INCOMPLETE, as every legacy arm is
    config['comparisons'] = [['model', 'no_such_arm']]    # G4 FAIL, a real contradiction
    result = audit.audit(config, root)
    assert result['gates']['G0_inputs']['status'] == 'INCOMPLETE'
    assert result['gates']['G4_arithmetic']['status'] == 'FAIL'
    assert result['status'] == 'FAIL'
    assert result['next_action']['gate'] == 'G4_arithmetic'
    assert result['next_action']['kind'] == 'repair'
    assert result['blocked_gates']['fail'] == ['G4_arithmetic']


def test_review_gates_are_named_and_cannot_be_earned_by_a_script(frozen):
    config, root = frozen
    result = audit.audit(config, root)
    kinds = {name: gate['kind'] for name, gate in result['gates'].items()}
    assert [n for n, k in kinds.items() if k == 'review'] == ['G3_serving', 'G5_inference', 'G6_review']
    # The deterministic half can be clean while the whole report stays honestly open.
    assert result['deterministic_status'] == 'PASS'
    assert result['status'] == 'INCOMPLETE'
    assert result['multiplicity']['n_comparisons'] == len(result['comparisons'])


def test_ambiguous_sessions_are_not_silently_attributed(tmp_path):
    """RED CONTROL for session_clustering: a query reachable from two sessions is unassignable.

    The first version kept whichever session was read first and counted the rest as
    "collisions", so an unassignable row was silently attributed to one of them and the
    table still printed as though it covered the whole manifest.
    """
    import session_clustering as sc
    shared = {'recent_user_request': 'same request', 'prior_actions': ['read_file']}
    pairs = tmp_path / 'pairs.jsonl'
    pairs.write_text('\n'.join(json.dumps(r) for r in [
        {**shared, 'session': 'sess_a'},
        {**shared, 'session': 'sess_b'},                       # same query, different session
        {'recent_user_request': 'unique', 'prior_actions': ['read_file'], 'session': 'sess_c'},
    ]) + '\n')
    index = sc.query_to_sessions(pairs)
    assert sorted(len(v) for v in index.values()) == [1, 2], \
        'both candidate sessions must be retained, not first-writer'
    ambiguous = [q for q, v in index.items() if len(v) > 1]
    assert len(ambiguous) == 1 and index[ambiguous[0]] == {'sess_a', 'sess_b'}
