import sys,json,hashlib,datetime,subprocess,collections
from pathlib import Path
H=Path(__file__).resolve().parents[1];ROOT=H.parent.parent;sys.path.insert(0,str(H));import run,grade
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lock=read(H/'review/marks-lock.json');assert lock['sha256']==sha(H/'review/blind-final-marks.json')
# Original committed blinding artifacts, before any review calls; mutation of identities cannot pass.
for n in ['review/private-mapping.json','review/private-control-expectations.json','review/bundle-receipt.json']:
 original=subprocess.check_output(['git','show','2f29317:'+str((H/n).relative_to(ROOT))],cwd=ROOT);assert original==(H/n).read_bytes(),'pregrading committed mapping/bundle drift: '+n
schedule=read(H/'inputs/schedule.json');assert len(schedule)==96;seen=set();replay=collections.Counter();prompts=collections.defaultdict(set);sessions=[];cwds=[];before=None
for c in schedule:
 d=H/'runs'/c['lane']/(c['pass']+'-'+c['packet']);r=read(d/'receipt.json');assert r['status']=='complete' and r['retries']==0 and not r['tool_use'];assert r['metadata']['lane']==c['lane'] and r['metadata']['pass']==c['pass'] and r['metadata']['packet']==c['packet']
 for n,s in r['retained_hashes'].items():assert sha(d/n)==s
 assert grade.extract((d/'answer.md').read_text())==read(d/'parsed.json');assert grade.grade(read(d/'parsed.json'),read(H/'inputs'/c['packet']/'expected.json'))==read(d/'structural.json')
 ev=[json.loads(x) for x in (d/'events.jsonl').read_text().splitlines() if x.strip()];ans=(d/'answer.md').read_text().strip();cli=r['cli']
 if cli=='claude':
  result=[x for x in ev if x.get('type')=='result'];assert len(result)==1 and result[0]['result'].strip()==ans and not result[0].get('is_error');sessions.append(result[0]['session_id']);texts=[b.get('text','') for x in ev if x.get('type')=='assistant' for b in x['message'].get('content',[]) if b.get('type')=='text'];assert ''.join(texts).strip()==ans;replay['claude_assistant_result_equal']+=1
 elif cli=='codex':
  texts=[x['item']['text'] for x in ev if x.get('type')=='item.completed' and x.get('item',{}).get('type')=='agent_message'];assert texts[-1].strip()==ans;sessions.append(next(x['thread_id'] for x in ev if x.get('type')=='thread.started'));assert '--ignore-user-config' in r['flags']
 else:
  result=[x['result'] for x in ev if x.get('event')=='result'];assert len(result)==1 and result[0]['response'].strip()==ans;deltas=''.join(x['step_update'].get('text_delta','') for x in ev if x.get('event')=='step_update' and x.get('step_update',{}).get('step_type')=='agent_response');assert deltas.strip()==ans;sessions.append(next(x['conversation_id'] for x in ev if x.get('event')=='init'))
 cwds.append(r['cwd']);prompts[c['packet']].add(r['prompt_sha256']);replay['raw_answer_parsed_structural_equal']+=1;cell=(c['lane'],c['pass'],c['packet']);assert cell not in seen;seen.add(cell)
 if before:assert before<=r['started_at']
 before=r['finished_at']
assert len(set(sessions))==96 and len(set(cwds))==96 and all(len(v)==1 for v in prompts.values())
mapping=read(H/'review/private-mapping.json');blind=read(H/'review/blind-final-marks.json');assert len(mapping)==32 and set(mapping)==set(blind);mapped=[]
for gid,g in mapping.items():
 for iid,m in g['items'].items():
  cell=(m['lane'],m['pass'],m['packet']);d=H/'runs'/cell[0]/(cell[1]+'-'+cell[2]);r=read(d/'receipt.json');assert m['answer_sha256']==r['answer_sha256'];assert iid=='X'+hashlib.sha256(f"{gid}/{m['pass']}/{m['case']}/830712".encode()).hexdigest()[:12];assert iid in blind[gid];mapped.append((*cell,m['case']))
assert len(mapped)==1152 and len(set(mapped))==1152
validity=read(H/'review/review-validity.json');assert len(validity)==64;review_status=collections.Counter();review_hashes=0
for seat in ['fable','astra']:
 for gid in mapping:
  d=H/'review'/seat/gid;r=read(d/'receipt.json');assert r['status']!='pending';assert r['prompt_sha256']==sha(H/'review'/(gid+'-prompt.txt'));review_status[r['status']]+=1
  for n,s in r['retained_hashes'].items():assert sha(d/n)==s;review_hashes+=1
  if r['cli']=='codex':assert '--ignore-user-config' in r['flags']
prov=[json.loads(x) for x in (H/'provenance.jsonl').read_text().splitlines() if x.strip()];cand=[x for x in prov if x['kind']=='candidate'];reviews=[x for x in prov if x['kind']=='blind_grade'];assert len(cand)==96 and len(reviews)==64 and len({x['cell'] for x in cand})==96 and len({(x['seat'],x['group']) for x in reviews})==64
for x in cand:assert x['receipt_sha256']==sha(H/x['cell']/'receipt.json')
for x in reviews:assert x['receipt_sha256']==sha(H/'review'/x['seat']/x['group']/'receipt.json')
native_effort={}
for lane in ['opus55','haiku55','haiku45']:
 vals=[]
 for p in (H/'runs'/lane).glob('*/events.jsonl'):
  ev=[json.loads(x) for x in p.read_text().splitlines() if x.strip()];init=next(x for x in ev if x.get('type')=='system' and x.get('subtype')=='init');vals.append(init.get('per_turn_effort_active'))
 native_effort[lane]={'candidate_calls':len(vals),'native_per_turn_effort_active':sorted(set(vals),key=str)}
out={'native_claude_effort_activation':native_effort,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'post-lock non-inference manual artifact audit','candidate_cells':96,'candidate_case_answers':1152,'raw_replay':dict(replay),'unique_sessions':96,'unique_cwds':96,'same_prompt_all_models_passes':True,'original_pregrading_mapping_bundle_commit':'2f29317','mapping_case_bijection':1152,'grading_calls':64,'review_terminal_statuses':dict(review_status),'valid_review_groups':sum(x['valid'] for x in validity.values()),'retained_review_file_hashes_verified':review_hashes,'provenance_candidates':96,'provenance_grades':64,'no_observed_candidate_tools':True,'marks_lock':lock,'note':'Original ambient guard remains red; disclosed continuation exception verified separately. No inference dispatched.'};(H/'final-data-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
