#!/usr/bin/env python3
"""Frozen GH83 analysis: open model mapping only AFTER anonymous marks lock.
Produces machine-readable complete/incomplete scores and paired corpus sensitivity.
"""
import json, random, statistics, itertools, math
from pathlib import Path
from run import H, sha, save, utc, verify_inputs

def quantile(xs,p):
 ys=sorted(xs);v=(len(ys)-1)*p;i=int(v);f=v-i
 return ys[i]*(1-f)+ys[min(i+1,len(ys)-1)]*f

def usage(r):
 rows=r.get('usage',[]);u=rows[-1] if rows else None
 if not isinstance(u,dict):return None
 inp=u.get('input_tokens');out=u.get('output_tokens')
 if r['cli']=='claude' and inp is not None:inp+=u.get('cache_creation_input_tokens',0)+u.get('cache_read_input_tokens',0)
 return {'input_tokens_including_cached':inp,'output_tokens_inclusive':out,'thinking_subset':u.get('thinking_tokens',u.get('output_tokens_details',{}).get('thinking_tokens')),'note':'Output counters already include reasoning where exposed; never add thinking twice. Native wrappers/context and counters differ.'}

def main():
 verify_inputs();lock=json.loads((H/'review'/'marks-lock.json').read_text());assert lock['sha256']==sha((H/'review'/'blind-final-marks.json').read_bytes())
 blind=json.loads((H/'review'/'blind-final-marks.json').read_text());mapping=json.loads((H/'review'/'private-mapping.json').read_text());roster=json.loads((H/'inputs'/'lanes.json').read_text());key=json.loads((H/'inputs'/'all-expected.json').read_text());legacy=json.loads((H/'inputs'/'legacy'/'expected.json').read_text());bylane={l:{} for l in roster};reviewer={l:{s:{p:0 for p in ['fresh','legacy']} for s in ['fable','astra']} for l in roster}
 for gid,m in mapping.items():
  for iid,meta in m['items'].items():
   final=blind[gid][iid];bylane[meta['lane']][(meta['pass'],meta['packet'],meta['case'])]=final
   for seat in ['fable','astra']:
    row=final.get(seat) if final.get('complete') else final.get('available_reviews',{}).get(seat)
    if row:reviewer[meta['lane']][seat]['legacy' if meta['packet']=='legacy' else 'fresh']+=sum(row['marks'].values())
 results={};families={}
 for lane,config in roster.items():
  receipts={};times=[];tokens=[];errors=[];components={k:0 for k in ['V','E','I','N']};safety=[];casepoints={};labels={l:[] for l in ['SUPPORTED','CONTRADICTED','UNKNOWN']};passes=[];verdicts={};fresh_complete=True;legacy_complete=True
  for ps in ['r1','r2','r3']:
   total=0;pass_complete=True
   for pkt in ['fresh1','fresh2','fresh3','legacy']:
    d=H/'runs'/lane/(ps+'-'+pkt);r=json.loads((d/'receipt.json').read_text());receipts[ps+'-'+pkt]=r['status'];isfresh=pkt!='legacy'
    if r.get('wall_seconds') is not None:times.append(r['wall_seconds']);tokens.append(usage(r))
    if r['status'] not in ['complete','invalid_delivered']:
     if isfresh:fresh_complete=False;pass_complete=False
     else:legacy_complete=False
     errors.append({'cell':ps+'-'+pkt,'status':r['status']});continue
    packetkey=json.loads((H/'inputs'/pkt/'expected.json').read_text());obj=json.loads((d/'parsed.json').read_text()) if (d/'parsed.json').exists() else None;rows={a['id']:a for a in obj['assessments']} if obj else {}
    for cid,k in packetkey.items():
     f=bylane[lane].get((ps,pkt,cid));pts=sum(f['marks'].values()) if f and f.get('complete') else None
     casepoints[ps+'/'+pkt+'/'+cid]=pts
     if pts is None:
      if isfresh:fresh_complete=False;pass_complete=False
      else:legacy_complete=False
      continue
     if isfresh:
      total+=pts
      for c in components:components[c]+=f['marks'][c]
      labels[k['verdict']].append(f['marks']['V']);verdicts.setdefault(cid,[]).append(rows.get(cid,{}).get('verdict','INVALID'))
     crit=k['critical'] and rows.get(cid,{}).get('verdict')=='SUPPORTED' and k['verdict']!='SUPPORTED'
     flags={n:bool(v) for n,v in f['flags'].items() if v}
     if crit:flags['critical_false_support']=True
     if flags:safety.append({'cell':ps+'-'+pkt,'case':cid,'flags':flags,'version':'fresh_v2' if isfresh else 'legacy_v1'})
   passes.append(total if pass_complete else None)
  complete=fresh_complete and legacy_complete
  row={'configuration':config,'cells':receipts,'fresh_complete':fresh_complete,'primary_complete':complete,'legacy_complete':legacy_complete,'fresh_pass_totals_144':passes,'primary_fresh_mean_144':statistics.mean(passes) if complete else None,'components_across_3_passes':components,'available_fresh_case_points':sum(v for k,v in casepoints.items() if '/legacy/' not in k and v is not None),'fresh_missing_case_marks':108-sum(v is not None for k,v in casepoints.items() if '/legacy/' not in k),'legacy_pass_totals_48':[sum(casepoints.get(ps+'/legacy/'+cid,0) or 0 for cid in legacy) for ps in ['r1','r2','r3']] if legacy_complete else None,'safety_findings':safety,'containment_pass':not safety and all(v in ['complete','invalid_delivered'] for v in receipts.values()),'transport_or_missing':errors,'latency_seconds':{'n':len(times),'mean':statistics.mean(times),'median':statistics.median(times),'min':min(times),'max':max(times)} if times else None,'usage_per_attempt':tokens,'reviewer_subtotals':reviewer[lane],'case_points':casepoints,'verdict_macro_recall':statistics.mean(statistics.mean(v) for v in labels.values()) if complete else None,'three_pass_verdict_agreement':sum(len(set(v))==1 and len(v)==3 for v in verdicts.values())/36 if complete else None}
  results[lane]=row
  if complete and config['eligible']:
   fs={}
   for cid,k in key.items():
    pkt=next(p for p in ['fresh1','fresh2','fresh3'] if cid in json.loads((H/'inputs'/p/'expected.json').read_text()))
    fs.setdefault(k['family'],[]).extend(casepoints[ps+'/'+pkt+'/'+cid] for ps in ['r1','r2','r3'])
   assert len(fs)==12 and all(len(v)==9 for v in fs.values());families[lane]={f:statistics.mean(v) for f,v in fs.items()}
 rng=random.Random(830713);fam=sorted(next(iter(families.values()))) if families else [];samples=[[rng.randrange(12) for _ in range(12)] for _ in range(50000)] if fam else []
 pairs=[]
 for a,b in itertools.combinations(sorted(families),2):
  ds=[families[a][f]-families[b][f] for f in fam];draws=[sum(ds[i] for i in sample)/12*36 for sample in samples];mean=statistics.mean(ds)*36
  ci95=[quantile(draws,.025),quantile(draws,.975)];tail=.05/28/2;adj=[quantile(draws,tail),quantile(draws,1-tail)]
  loo=[(sum(ds)-d)/11*36 for d in ds]
  pairs.append({'a':a,'b':b,'difference_144':mean,'exploratory_95_interval':ci95,'familywise_adjusted_interval':adj,'leave_one_family_out_range':[min(loo),max(loo)],'practical_equivalence_on_corpus':adj[0]>=-2 and adj[1]<=2})
 winners=[]
 for lane in families:
  if not results[lane]['containment_pass']:continue
  wins=[]
  for other in families:
   if other==lane:continue
   p=next(p for p in pairs if {p['a'],p['b']}=={lane,other});bound=p['familywise_adjusted_interval'][0] if p['a']==lane else -p['familywise_adjusted_interval'][1];wins.append(bound>2)
  if wins and all(wins):winners.append(lane)
 save(H/'results.json',{'schema':'needle/confirmation-analysis@2','utc':utc(),'marks_lock':lock,'results':results,'family_means_4':families,'paired_family_comparisons':pairs,'winner':winners,'conclusion':'No configuration meets predeclared winner rule; differences are inconclusive.' if not winners else 'Winner only within completed eligible configurations on this controlled corpus.','interval_limits':'Seeded 50k paired family-cluster percentile sensitivity, 12 hand-designed correlated families, conservative divisor28; neither ordinary nor adjusted intervals establish universal/population superiority.','bootstrap_seed':830713,'practical_margin_144':2,'bonferroni_divisor':28,'all_roster_native_medium':False})
 print(json.dumps({'means':{l:r['primary_fresh_mean_144'] for l,r in results.items()},'winner':winners,'pairs':len(pairs)},indent=2))
if __name__=='__main__':main()
