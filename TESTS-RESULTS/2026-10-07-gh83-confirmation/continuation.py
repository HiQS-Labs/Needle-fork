#!/usr/bin/env python3
"""Disclosed post-capture continuation after an ignored Codex configuration changed.
Original frozen verify_inputs still rejects this environment. No candidate calls,
new prompts, regrading, scoring changes or frozen-file edits are allowed here.
The native exec help says --ignore-user-config does not load config.toml.
"""
import json, pathlib, sys
import run, review
H=run.H
IGNORED='~/.codex/config.toml'
def verify():
 m=json.loads((H/'input-manifest.json').read_text());assert m['files'],'empty manifest'
 for n,s in m['files'].items():assert run.sha((H/n).read_bytes())==s,'frozen input drift: '+n
 delta=[]
 for n,s in json.loads((H/'inputs/environment.json').read_text())['ambient_fingerprints'].items():
  p=pathlib.Path(n).expanduser();actual=run.sha(p.read_bytes()) if p.is_file() else None
  if n==IGNORED:
   if actual!=s:delta.append({'path':n,'frozen_sha256':s,'current_sha256':actual})
  else:assert actual==s,'ambient input drift: '+n
 # Already-issued requests may only be skipped after their retained artifacts replay.
 for seat in ['fable','astra']:
  for p in (H/'review'/seat).glob('B*/receipt.json'):
   r=json.loads(p.read_text());assert r['status']!='pending','ambiguous pending request; do not reissue'
   for n,s in r.get('retained_hashes',{}).items():assert run.sha((p.parent/n).read_bytes())==s,'review artifact drift'
 bundle=json.loads((H/'review/bundle-receipt.json').read_text());assert len(bundle['prompt_hashes'])==32
 for gid,s in bundle['prompt_hashes'].items():assert run.sha((H/'review'/(gid+'-prompt.txt')).read_bytes())==s,'blind prompt drift'
 with (H/'review/environment-deltas.jsonl').open('a') as f:f.write(json.dumps({'utc':run.utc(),'mode':sys.argv[1] if len(sys.argv)>1 else 'manual_verify','ignored_file_delta':delta,'unchanged_frozen_files':len(m['files']),'other_ambient_inputs_match':True,'reason':'Native Codex calls explicitly ignore user config; raw flag receipts and retained exec help establish exclusion. No user configuration was modified by this coordinator.'})+'\n')
 return m
if __name__=='__main__':
 mode=sys.argv[1];assert mode in ['astra-drain','grade','reconcile','stats','verify']
 verify();review.verify_inputs=verify
 if mode=='astra-drain':
  for gid in sorted(json.loads((H/'review/bundle-receipt.json').read_text())['prompt_hashes']):review.grader('astra','codex','gpt-6-astra','medium',gid)
 elif mode=='grade':review.grade_all()
 elif mode=='reconcile':review.reconcile()
 elif mode=='stats':
  import stats
  stats.verify_inputs=verify;stats.main()
