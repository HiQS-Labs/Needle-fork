from pathlib import Path
import json,importlib.util,os,subprocess
r=Path('/Users/noelsaw/marathon-clones/needle-gh81-model-eval'); b=r/'TESTS-RESULTS/2026-09-29-gh81-phase2';old=r/'TESTS-RESULTS/2026-09-29-gh80-luna6-phase2'
spec=importlib.util.spec_from_file_location('grade',b/'grade.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);key=json.loads((b/'expected.json').read_text())
answers={}
for label,lane,n in [('A','luna-high','r1'),('B','luna-high','r2'),('C','sonnet-medium','r1'),('D','sonnet-medium','r2')]:
 p=b/lane/(n+'-answer.md');obj=m.extract(p.read_text());p.with_suffix('.json').write_text(json.dumps(obj,indent=2)+'\n');g=m.grade(obj,key);p.with_name(n+'-structural.json').write_text(json.dumps(g,indent=2)+'\n');answers[label]=obj
base=(old/'review/prompt.txt').read_text().split('\nKEY\n')[0].replace('two anonymized','four anonymized').replace('A and B','A, B, C and D')
prompt=base+'\nKEY\n'+(b/'expected.json').read_text()+'\nSOURCE PACKET\n'+(b/'packet.json').read_text()+'\nANONYMIZED ANSWERS\n'+json.dumps(answers,indent=2)
(b/'review/prompt.txt').write_text(prompt)
rows=[]
for run in ['C','D']:
 rs=[]
 for i in range(1,13):
  sem=[1,1];why='Meets both requirements by semantic equivalence.'
  if i==1:sem=[1,0] if run=='C' else [0,0];why='C names issue2 and retired CPU path but no current blocker check; D omits those material details and checks pointer resolution only.'
  if i==2 and run=='C':sem=[0,1];why='Lists command-position/wrappers without explaining invocation versus argument classification; execution verification is explicit.'
  if i==3:sem=[1,0];why='Omits primary-checkout review/AgentChorus change scope.'
  if i==4 and run=='D':sem=[1,0];why='Does not state PR is open at snapshot.'
  if i==7 and run=='D':sem=[1,0];why='Suggests re-landing enablement before checking why reverted; noting reason is not investigating before recommendation.'
  rs.append(dict(id=f'G{i:02d}',verdict=int(not(run=='D' and i in (5,12))),evidence=1,semantic_requirements=sem,reason=why))
 rows.append(dict(run=run,rows=rs,total=sum(x['verdict']+x['evidence']+sum(x['semantic_requirements']) for x in rs),critical_errors=[]))
(b/'review/coordinator-sonnet-initial.json').write_text(json.dumps({'runs':rows},indent=2)+'\n')
env=os.environ.copy();env.update(CONSULT_ROOT=str(r/'temp/candidate'),CODEX_BIN=str(b/'adapters/review.py'),CODEX_FLAGS='',LOCAL_SPIKE_ROOT=str(b/'review'),LOCAL_SPIKE_RUN='r1',ANALYST_SOURCE_REFERENCE=str(r/'temp/source-reference.json'),REVIEW_PROMPT=str(b/'review/prompt.txt'),CONSULT_TIMEOUT='900',CONSULT_IDLE_S='120')
with (b/'review/consult.log').open('x') as f:
 p=subprocess.run(['bash','/Users/noelsaw/Documents/GH Repos/needle-fork/.xyz/relay-automation/consult.sh','--models','codex','--prompt-file',str(b/'review/prompt.txt'),'--out',str(r/'temp/relay'),'--label','gh81-independent-review'],env=env,stdout=f,stderr=subprocess.STDOUT)
print('review exit',p.returncode)
