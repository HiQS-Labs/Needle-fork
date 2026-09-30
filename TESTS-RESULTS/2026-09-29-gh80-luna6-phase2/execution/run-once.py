import os,pathlib,subprocess,sys,json,hashlib
root=pathlib.Path(__file__).resolve().parent.parent
b=root/'TESTS-RESULTS/2026-09-29-gh80-luna6-phase2'
r=sys.argv[1]; assert r in ('r1','r2')
out=b/'runs';out.mkdir(exist_ok=True)
env=os.environ.copy();env.update(CONSULT_ROOT=str(root/'temp/candidate'),CODEX_BIN=str(b/'adapters/luna-medium.py'),CODEX_FLAGS='',LOCAL_SPIKE_ROOT=str(out),LOCAL_SPIKE_RUN=r,ANALYST_PROMPT_FILE=str(b/'QUESTIONS.md'),ANALYST_SOURCE_REFERENCE=str(root/'temp/source-reference-gh80.json'),CONSULT_TIMEOUT='900',CONSULT_IDLE_S='120')
with (out/(r+'-consult.log')).open('x') as f:
 p=subprocess.run(['bash','/Users/noelsaw/Documents/GH Repos/needle-fork/.xyz/relay-automation/consult.sh','--models','codex','--prompt-file',str(b/'QUESTIONS.md'),'--out',str(root/'temp/relay'),'--label','gh80-luna6-'+r],env=env,stdout=f,stderr=subprocess.STDOUT)
print('consult exit',p.returncode)
receipt=out/(r+'-receipt.json')
if receipt.exists(): print(receipt.read_text())
raise SystemExit(p.returncode)
