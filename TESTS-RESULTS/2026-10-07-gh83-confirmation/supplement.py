#!/usr/bin/env python3
"""Post-capture descriptive report derivation; never dispatches inference or changes frozen scoring.
Requires anonymous marks lock before reading identity mapping. Does not impute missing marks.
"""
import json, hashlib, statistics, collections
from pathlib import Path
H=Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 lock=read(H/'review/marks-lock.json');assert lock['sha256']==digest(H/'review/blind-final-marks.json')
 blind=read(H/'review/blind-final-marks.json');mapping=read(H/'review/private-mapping.json')
 validity=read(H/'review/review-validity.json');results=read(H/'results.json')['results'];
 mapped=collections.defaultdict(dict)
 for gid,g in mapping.items():
  for iid,m in g['items'].items():mapped[m['lane']][(m['pass'],m['packet'],m['case'])]=blind[gid][iid]
 summary={}
 for lane,row in results.items():
  v=collections.Counter();crit=[];verdicts=collections.defaultdict(list);points=collections.defaultdict(list);review_counts={s:collections.Counter() for s in ['fable','astra']};g05=[];paired_review_totals={s:collections.Counter() for s in ['fable','astra']}
  for ps in ['r1','r2','r3']:
   for pkt in ['fresh1','fresh2','fresh3','legacy']:
    d=H/'runs'/lane/(ps+'-'+pkt);obj=read(d/'parsed.json');key=read(H/'inputs'/pkt/'expected.json')
    for a in obj['assessments']:
     k=key[a['id']];final=mapped[lane][(ps,pkt,a['id'])];version='legacy' if pkt=='legacy' else 'fresh'
     if version=='fresh':
      verdicts[a['id']].append(a['verdict']);v['total']+=1;v['correct']+=a['verdict']==k['verdict'];v[k['verdict']+'_total']+=1;v[k['verdict']+'_correct']+=a['verdict']==k['verdict']
      if k['critical'] and a['verdict']=='SUPPORTED' and k['verdict']!='SUPPORTED':crit.append({'pass':ps,'packet':pkt,'case':a['id']})
      if final['complete']:points[a['id']].append(sum(final['marks'].values()))
     if a['id']=='G05' and pkt=='legacy':g05.append(int(a['verdict']==k['verdict']))
     for seat in ['fable','astra']:
      avail=final.get(seat) if final['complete'] else final.get('available_reviews',{}).get(seat)
      if avail:review_counts[seat][version]+=1
      if final['complete']:paired_review_totals[seat][version]+=sum(avail['marks'].values())
  complete_cases={cid:ps for cid,ps in points.items() if len(ps)==3}
  differing=[{'case':cid,'points':ps,'range':max(ps)-min(ps)} for cid,ps in complete_cases.items() if len(set(ps))>1]
  sensitivity=[total-vpoint for total,vpoint in zip(row['legacy_pass_totals_48'],g05)] if row['legacy_complete'] else None
  token_totals={};usages=row['usage_per_attempt']
  for field in ['input_tokens_including_cached','output_tokens_inclusive','thinking_subset']:
   vals=[u[field] for u in usages if u and u[field] is not None]
   if field=='thinking_subset':
    # Frozen stats misses the native Codex reasoning_output_tokens alias. Supplement
    # only exposed descriptive telemetry; no frozen scoring/data are rewritten.
    for ps in ['r1','r2','r3']:
     for pkt in ['fresh1','fresh2','fresh3','legacy']:
      rec=read(H/'runs'/lane/(ps+'-'+pkt)/'receipt.json');raw=rec.get('usage',[])
      if rec['cli']=='codex' and raw and isinstance(raw[-1],dict) and raw[-1].get('thinking_tokens') is None and raw[-1].get('output_tokens_details',{}).get('thinking_tokens') is None and raw[-1].get('reasoning_output_tokens') is not None:vals.append(raw[-1]['reasoning_output_tokens'])
   token_totals[field]={'known_calls':len(vals),'sum_known':sum(vals) if vals else None}
  summary[lane]={'structural_verdicts_all_fresh_calls':dict(v),'structural_macro_recall':statistics.mean(v[label+'_correct']/v[label+'_total'] for label in ['SUPPORTED','CONTRADICTED','UNKNOWN']),'structural_three_pass_agreement':{'agreeing_cases':sum(len(set(vals))==1 and len(vals)==3 for vals in verdicts.values()),'total_cases':36},'critical_false_support_all_fresh_calls':crit,'paired_semantic_coverage':{'fresh':108-row['fresh_missing_case_marks'],'legacy':36 if row['legacy_complete'] else sum(x.get('complete',False) for (p,pk,c),x in mapped[lane].items() if pk=='legacy')},'valid_reviewer_case_counts':{s:dict(c) for s,c in review_counts.items()},'paired_reviewer_subtotals':{s:dict(c) for s,c in paired_review_totals.items()},'legacy_without_G05_verdict_point_47':sensitivity,'three_pass_point_spread_complete_cases':{'n_complete_cases':len(complete_cases),'n_changing':len(differing),'maximum_range':max((max(p)-min(p) for p in complete_cases.values()),default=None),'changes':differing},'token_totals_descriptive':token_totals,'telemetry_note':'Supplement reads native Codex reasoning_output_tokens alias from retained receipts; frozen stats usage extractor omits that alias. No frozen score/result data are changed; inclusive output already contains reasoning.','diagnostic_containment_status':'OBSERVED_FLAGS' if row['safety_findings'] or crit else 'ASSESSED_NO_FLAGS' if row['primary_complete'] else 'INCOMPLETE_NOT_ESTABLISHED','note':'No semantic completeness or safety PASS is inferred from absent marks. Verdict accuracy is mechanical and available independently of semantic canary validity; no scoring rule changes.'}
 invalid=[{'group_seat':g,**r} for g,r in validity.items() if not r['valid']]
 out={'schema':'needle/confirmation-descriptive-supplement@1','marks_lock':lock,'derivation':'Post-capture descriptive accounting; no replacement grades, imputation, new inferential comparisons or model-selection rules.','invalid_review_groups':invalid,'results':summary}
 (H/'descriptive-supplement.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'invalid_groups':len(invalid),'lanes':len(summary)},indent=2))
if __name__=='__main__': main()
