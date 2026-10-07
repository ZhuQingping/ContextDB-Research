#!/usr/bin/env python3
"""Start isolated API/Worker processes against an unused PG schema; stop on exit."""
import asyncio,json,os,secrets,signal,subprocess,time,uuid
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[2]; EV=ROOT/'round2/evidence'; RUN=ROOT/'round2/.runtime/split'
RUN.mkdir(parents=True,exist_ok=True)
records=[]; procs=[]; logs=[]
def check(name,ok,**v):
 records.append(dict(name=name,passed=bool(ok),**v));(EV/'split-worker-probe.json').write_text(json.dumps(records,indent=2));assert ok,name
async def main():
 base=os.environ.copy();base.update(json.loads((ROOT/'config.json').read_text()))
 key=secrets.token_urlsafe(32);schema='round2_split_'+uuid.uuid4().hex[:8]
 base.update({'HINDSIGHT_API_DATABASE_URL':'postgresql://hindsight:hindsight@127.0.0.1:55433/hindsight',
 'HINDSIGHT_API_DATABASE_SCHEMA':schema,'HINDSIGHT_API_PORT':'8892','HINDSIGHT_API_WORKER_ENABLED':'false',
 'HINDSIGHT_API_DB_POOL_MIN_SIZE':'2','HINDSIGHT_API_DB_POOL_MAX_SIZE':'10',
 'HINDSIGHT_API_TENANT_EXTENSION':'hindsight_api.extensions.builtin.tenant:ApiKeyTenantExtension',
 'HINDSIGHT_API_TENANT_API_KEY':key,'HINDSIGHT_API_WORKER_ID':'round2-split-worker',
 'HINDSIGHT_API_CONSOLIDATION_RECONCILE_INTERVAL_SECONDS':'0','HINDSIGHT_API_MENTAL_MODEL_REFRESH_TICK_SECONDS':'0',
 'HINDSIGHT_API_RETENTION_SWEEP_INTERVAL_SECONDS':'0','HINDSIGHT_API_OPERATION_CLEANUP_INTERVAL_SECONDS':'0',
 'HINDSIGHT_API_LLM_TRACE_ENABLED':'false'})
 def start(name,cmd,env):
  f=(EV/f'split-{name}.log').open('a');logs.append(f)
  p=subprocess.Popen(cmd,env=env,cwd=RUN,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
  procs.append(p);return p
 async def stop(p,kill=False):
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGKILL if kill else signal.SIGTERM)
   for _ in range(120):
    if p.poll() is not None:break
    await asyncio.sleep(.1)
   if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
   p.wait()
 async with httpx.AsyncClient(trust_env=False,timeout=60,headers={'Authorization':'Bearer '+key}) as h:
  async def ready(url,p):
   for _ in range(150):
    if p.poll() is not None:raise RuntimeError('process exited; see isolated logs')
    try:
     r=await h.get(url)
     if r.status_code==200:return
    except httpx.HTTPError:pass
    await asyncio.sleep(.2)
   raise RuntimeError('startup timeout')
  api=start('api',[str(ROOT/'.venv/bin/hindsight-api')],base)
  await ready('http://127.0.0.1:8892/health',api)
  check('api-only-ready',True,pid=api.pid,schema=schema)
  bank='round2-split';url='http://127.0.0.1:8892/v1/default/banks/'+bank
  r=await h.put(url,json={'retain_extraction_mode':'chunks','enable_observations':False});check('create-bank',r.status_code==200)
  async def submit(doc,content):
   op=str(uuid.uuid4());r=await h.post(url+'/memories',json={'async':True,'operation_id':op,'items':[{'document_id':doc,'content':content}]})
   check('accepted-'+doc,r.status_code==200 and r.json()['operation_id']==op);return op
  async def status(op):return (await h.get(url+'/operations/'+op)).json()
  async def done(op):
   for _ in range(300):
    r=await status(op)
    if r.get('status') in ['completed','failed']:return r
    await asyncio.sleep(.1)
   return r
  op=await submit('queued-without-worker','Synthetic split API and worker marker FIR-901.')
  await asyncio.sleep(.7);r=await status(op);check('no-inline-worker-task-remains-pending',r.get('status')=='pending',status=r.get('status'))
  worker_env={**base,'HINDSIGHT_API_WORKER_ENABLED':'true'}
  cmd=[str(ROOT/'.venv/bin/hindsight-worker'),'--http-host','127.0.0.1','--http-port','8893']
  w=start('worker',cmd,worker_env);await ready('http://127.0.0.1:8893/health',w)
  check('separate-worker-ready',True,worker_pid=w.pid,api_pid=api.pid)
  r=await done(op);check('queued-task-completed-by-separate-worker',r.get('status')=='completed',status=r.get('status'))
  await stop(w)
  r=await h.post(url+'/memories/recall',json={'query':'FIR-901','max_tokens':500,'budget':'low'})
  check('api-recall-works-with-worker-stopped',r.status_code==200 and 'FIR-901' in r.text)
  op2=await submit('queued-during-worker-outage','Synthetic worker recovery marker PINE-302.')
  await asyncio.sleep(.7);r=await status(op2);check('task-durable-while-worker-down',r.get('status')=='pending',status=r.get('status'))
  w2=start('worker-restarted',cmd,worker_env);await ready('http://127.0.0.1:8893/health',w2)
  r=await done(op2);check('restarted-worker-drains-pending-task',r.get('status')=='completed',status=r.get('status'))
  r=await h.get('http://127.0.0.1:8893/metrics');check('worker-metrics-available',r.status_code==200)
  check('api-survived-worker-restart',api.poll() is None)
  print(f'PASS {len(records)} split-process checks; pending-task restart, not mid-LLM crash or PG power-loss.')
try:asyncio.run(main())
finally:
 for p in reversed(procs):
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=15)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 for f in logs:f.close()
