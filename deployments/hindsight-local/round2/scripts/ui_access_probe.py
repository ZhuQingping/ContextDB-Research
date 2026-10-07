#!/usr/bin/env python3
"""Temporary UI access-key test; no change to existing UI or global config."""
import json,os,secrets,signal,subprocess,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[2];EV=ROOT/'round2/evidence';checks=[]
def check(name,ok,status):
 checks.append(dict(name=name,passed=bool(ok),status=status));(EV/'ui-access-probe.json').write_text(json.dumps(checks,indent=2));assert ok,name
key=secrets.token_urlsafe(32)
env={**os.environ,'HINDSIGHT_CP_ACCESS_KEY':key,'HINDSIGHT_CP_DATAPLANE_API_URL':'http://127.0.0.1:8888','HINDSIGHT_CP_DATAPLANE_API_KEY':''}
with (EV/'ui-access-process.log').open('w') as log:
 p=subprocess.Popen(['node',str(ROOT/'.runtime/ui/node_modules/@vectorize-io/hindsight-control-plane/bin/cli.js'),'--hostname','127.0.0.1','--port','9998'],env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 try:
  with httpx.Client(base_url='http://127.0.0.1:9998',trust_env=False,timeout=10) as c:
   for _ in range(100):
    try:
     r=c.get('/api/health')
     if r.status_code==200:break
    except httpx.HTTPError:pass
    if p.poll() is not None:raise RuntimeError('temporary UI exited')
    time.sleep(.1)
   check('ui-ready',r.status_code==200,r.status_code)
   r=c.get('/api/banks');check('anonymous-list-denied',r.status_code==401,r.status_code)
   r=c.post('/api/auth/login',json={'key':'invalid'});check('invalid-access-key-denied',r.status_code==401,r.status_code)
   r=c.post('/api/auth/login',json={'key':key});check('valid-access-key-login',r.status_code==200,r.status_code)
   r=c.get('/api/banks');check('authenticated-list-allowed',r.status_code==200,r.status_code)
  print(f'PASS {len(checks)} temporary UI login checks; shared operator key, not customer tenant IAM.')
 finally:
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
