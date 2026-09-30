import os,pathlib,subprocess,sys,json
b=pathlib.Path(__file__).resolve().parent;root=b.parent.parent
lane,r=sys.argv[1:];assert lane in ('luna-high','sonnet-medium') and r in ('r1','r2')
out=b/lane;out.mkdir(exist_ok=True)
env=os.environ.copy();env.update(CONSULT_ROOT=str(root/'temp/candidate'),CODEX_BIN=str(b/'adapters'/(lane+'.py')),CODEX_FLAGS='',LOCAL_SPIKE_ROOT=str(out),LOCAL_SPIKE_RUN=r,ANALYST_PROMPT_FILE=str(b/'QUESTIONS.md'),ANALYST_SOURCE_REFERENCE=str(root/'temp/source-reference.json'),CONSULT_TIMEOUT='900',CONSULT_IDLE_S='120')
with (out/(r+'-consult.log')).open('x') as f:
 p=subprocess.run(['bash','/Users/noelsaw/Documents/GH Repos/needle-fork/.xyz/relay-automation/consult.sh','--models','codex','--prompt-file',str(b/'QUESTIONS.md'),'--out',str(root/'temp/relay'),'--label','gh81-'+lane+'-'+r],env=env,stdout=f,stderr=subprocess.STDOUT)
receipt=out/(r+'-receipt.json');print(receipt.read_text() if receipt.exists() else 'NO RECEIPT');raise SystemExit(p.returncode)
