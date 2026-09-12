"""Read-only #53 source audit. Stdout contains raw public cases: retain privately."""
import collections
import copy
import inspect
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spike/coding_core'))
import prepare_openhands as prep

PANEL = ROOT / 'data/next-action-panel-v1'
SOURCE = ROOT / 'data/context-next-action-2026-09-12-launch2/source.jsonl'
assert prep.digest(SOURCE) == '929b8265bf1432d2602c51cc1d0b993167a3a857e22cdf170f3d6b2ef467ba5a'
original = json.loads(subprocess.check_output([sys.executable,
    str(ROOT / 'TESTS-RESULTS/2026-09-12-next-action-panel/score.py')]))
assert original['aggregates'] == json.loads((ROOT / 'TESTS-RESULTS/2026-09-12-next-action-panel/metrics.json').read_text())
cases = original['per_case']
seats = ('fable', 'glm', 'astra', 'gemini', 'qwen', 'deepseek', 'tencent')
misses = [r for r in cases if all(r['predictions'][s] != r['target'] for s in seats)]
controls = [next(r for r in cases if r['target'] == label and r not in misses)
            for label in ('read', 'run_command', 'run_tests')]
selected = misses + controls
assert len(misses) == 9 and len({r['case_id'] for r in selected}) == 12
key = {r['case_id']: r for r in json.loads((PANEL / 'private-manifest.json').read_text())['answer_key']}
by_issue = {key[r['case_id']]['issue']: r for r in selected}
code, start = inspect.getsourcelines(prep._context_rows)
emit_line = start + next(i for i, line in enumerate(code) if 'rows.append({' in line)
seen = set()
records = []
red_controls = []
with SOURCE.open() as fh:
    for source_line, line in enumerate(fh, 1):
        source = json.loads(line)
        issue = source['instance_id']
        if source.get('resolved') != 1 or issue not in by_issue or issue in seen:
            continue
        seen.add(issue)
        case = by_issue[issue]
        messages = prep._json_value(source['trajectory'], 'trajectory')
        # Pass decoded messages so trace identities refer to the original source objects.
        source['trajectory'] = messages
        indices = {id(m): i for i, m in enumerate(messages)}
        events = {}
        def trace(frame, event, arg):
            if frame.f_code is prep._context_rows.__code__ and event == 'line' and frame.f_lineno == emit_line:
                v = frame.f_locals
                events[v['call_id']] = (indices[id(v['msg'])], dict(task=v['task'],
                    history=list(v['prior']), observation=v['observation'], target=v['label']))
            return trace
        sys.settrace(trace)
        try:
            made = prep.trajectory_rows(source, [], context=True)
        finally:
            sys.settrace(None)
        assert made == [r for _, r in events.values()]
        target = {k: case[k] for k in ('task', 'history', 'observation', 'target')}
        matched = [(call_id, idx) for call_id, (idx, r) in events.items() if r == target]
        assert len(matched) == 1
        call_id, idx = matched[0]
        tool_idx = max(i for i in range(idx) if messages[i]['role'] == 'tool')
        response = messages[tool_idx]
        prior_matches = [(i, c) for i, m in enumerate(messages[:tool_idx]) if m['role'] == 'assistant'
            for c in (prep._json_value(m.get('tool_calls'), 'calls') or []) if c.get('id') == response.get('tool_call_id')]
        assert len(prior_matches) == 1
        prev_idx, prev_call = prior_matches[0]
        current = prep._json_value(messages[idx]['tool_calls'], 'calls')[0]
        user_idx = max(i for i in range(idx) if messages[i]['role'] == 'user')
        task = messages[user_idx]['content']
        raw = response['content']
        assert user_idx < prev_idx < tool_idx < idx
        assert current['id'] == call_id and prep.project_call(current) == target['target']
        assert prep.project_call(prev_call) == target['history'][-1]
        assert ' '.join(raw[-2000:].split()) == target['observation']
        assert prep._clean(task, 600) == target['task']
        assert response.get('name') in (None, prev_call['function']['name'])
        next_results = [(i, m) for i, m in enumerate(messages[idx+1:], idx+1)
            if m.get('role') == 'tool' and m.get('tool_call_id') == call_id]
        assert len(next_results) == 1
        result_idx, next_result = next_results[0]
        if case['case_id'] == 'case-08':
            damaged = copy.deepcopy(source)
            damaged['trajectory'][tool_idx]['tool_call_id'] = 'audit-deliberately-wrong-id'
            assert target not in prep.trajectory_rows(damaged, [], context=True)
            red_controls.append('Wrong prior response ID removes the audited target row')
            future = copy.deepcopy(source)
            future['trajectory'][result_idx]['content'] = 'AUDIT_FUTURE_SENTINEL'
            assert target in prep.trajectory_rows(future, [], context=True)
            assert 'AUDIT_FUTURE_SENTINEL' not in str(target)
            red_controls.append('Changing target result cannot change the pre-action audited row')
            wrong_call = copy.deepcopy(source)
            calls = prep._json_value(wrong_call['trajectory'][idx]['tool_calls'], 'calls')
            calls[0]['function']['arguments'] = json.dumps({'command': 'git status'})
            wrong_call['trajectory'][idx]['tool_calls'] = calls
            assert target not in prep.trajectory_rows(wrong_call, [], context=True)
            red_controls.append('Replacing raw next call rejects original target alignment')
        records.append(dict(case_id=case['case_id'], cohort='shared_miss' if case in misses else 'control',
            issue=issue, trajectory_id=source['trajectory_id'], source_line=source_line,
            target_message_index=idx, previous_call_index=prev_idx, response_index=tool_idx,
            user_message_index=user_idx, target=target['target'], quiz=target,
            previous_call=prev_call, next_call=current, full_previous_response=raw, full_task=task,
            target_result_index=result_idx, target_result=next_result['content'],
            raw_observation_chars=len(raw), omitted_observation_chars=max(0,len(raw)-2000),
            normalized_task_chars=len(' '.join(task.split())),
            omitted_task_chars=max(0,len(' '.join(task.split()))-600)))
assert len(records) == len(seen) == 12
assert len(red_controls) == 3
print(json.dumps(dict(source_sha256=prep.digest(SOURCE), projection_sha256=prep.digest(Path(prep.__file__)),
    red_controls=red_controls, records=sorted(records, key=lambda r:r['case_id'])), indent=2))
