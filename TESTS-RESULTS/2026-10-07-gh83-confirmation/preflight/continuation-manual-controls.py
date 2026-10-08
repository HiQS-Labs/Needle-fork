import json,sys,shutil,tempfile,hashlib,datetime
from pathlib import Path
SRC=Path(__file__).resolve().parents[1];ROOT=SRC.parent.parent;(ROOT/'temp').mkdir(exist_ok=True);sys.path.insert(0,str(SRC));import continuation as c
F=Path(tempfile.mkdtemp(prefix='gh83-continuation-control-',dir=ROOT/'temp'));m=json.loads((SRC/'input-manifest.json').read_text())
for name in ['input-manifest.json',*m['files'],'review/bundle-receipt.json']:
 p=F/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(SRC/name,p)
for p in (SRC/'review').glob('B*-prompt.txt'):shutil.copyfile(p,F/'review'/p.name)
c.H=F;checks=[]
def check(label,expected):
 try:c.verify();observed='PASS';detail='all24 frozen files, other ambient fingerprints and32 blind prompt hashes match'
 except AssertionError as e:observed='FAIL';detail=str(e)
 checks.append({'control':label,'expected':expected,'observed':observed,'detail':detail});assert observed==expected
check('unaltered copy with disclosed ignored-config delta','PASS')
p=F/'inputs/fresh1/QUESTIONS.md';old=p.read_bytes();p.write_bytes(old+b'\nDRIFT CONTROL\n');check('one frozen prompt byte change','FAIL');p.write_bytes(old)
p=F/'review/B001-prompt.txt';old=p.read_bytes();p.write_bytes(old+b'\nDRIFT CONTROL\n');check('one blind bundle byte change','FAIL');p.write_bytes(old)
ep=F/'inputs/environment.json';old=ep.read_bytes();env=json.loads(old);env['ambient_fingerprints']['~/.codex/AGENTS.md']='0'*64;ep.write_text(json.dumps(env)+'\n')
mp=F/'input-manifest.json';oldm=mp.read_bytes();fm=json.loads(oldm);fm['files']['inputs/environment.json']=hashlib.sha256(ep.read_bytes()).hexdigest();mp.write_text(json.dumps(fm)+'\n');check('different nonignored ambient expected fingerprint in synthetic manifest','FAIL');ep.write_bytes(old);mp.write_bytes(oldm)
d=F/'review/astra/B000';d.mkdir(parents=True);rp=d/'receipt.json';rp.write_text(json.dumps({'status':'pending'}));check('ambiguous pending review','FAIL');rp.write_text(json.dumps({'status':'complete','retained_hashes':{'answer.md':'0'*64}}));(d/'answer.md').write_text('nonempty local control');check('changed retained review answer','FAIL');rp.unlink();(d/'answer.md').unlink();check('all own control mutations restored from saved bytes','PASS')
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'manual continuation controls, no provider/model requests','scope':'isolated copy of24 frozen input files and32 blind prompts; fake B000 receipt and synthetic nonignored fingerprint; no real candidate mapping read or user file changed','source_sha256':hashlib.sha256((SRC/'continuation.py').read_bytes()).hexdigest(),'checks':checks}
(SRC/'preflight/continuation-controls.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
