from pathlib import Path
import os,json,subprocess,signal,socket,time,sys,asyncio,httpx
p=Path(Path('/tmp/cb-cloud-e2e-path').read_text().strip());mode=sys.argv[1];process=json.loads((p/'processes.json').read_text());root=Path('/Users/zhuqingping/Work/Database/Context/hindsight');build=p/'source';py=str(root/'.venv/bin/python');service=str(build/'hindsight-extensions/contextdb-service/scripts/service.sh')
async def idle():
 key=json.loads((p/'runtime/admin-key.json').read_text())['secret'];headers={'Authorization':'Bearer '+key}
 async with httpx.AsyncClient(base_url='http://127.0.0.1:8891',headers=headers,trust_env=False,timeout=30) as c:
  ws=(await c.get('/ext/contextdb/v1/workspaces',params={'limit':100})).json()['items']
  for w in ws:
   if w['state']!='active':continue
   for n in range(120):
    r=await c.get('/v1/default/banks/'+w['bank_id']+'/operations',params={'limit':100});r.raise_for_status();busy=[x for x in r.json()['operations'] if x['status'] in ['pending','running']]
    if not busy:break
    await asyncio.sleep(2)
   else:raise RuntimeError('Not drained; no process termination')
asyncio.run(idle())
for kind in ['worker','api']:
 if process.get(kind):
  os.kill(process[kind],signal.SIGTERM)
  process.pop(kind)
for n in range(60):
 s=socket.socket();s.settimeout(.1);alive=s.connect_ex(('127.0.0.1',8891))==0;s.close()
 if not alive:break
 time.sleep(1)
else:raise RuntimeError('API did not stop')
f=p/'runtime/api.env';t=f.read_text();import re
t=re.sub(r'HINDSIGHT_API_WORKER_ENABLED=(?:true|false)',f'HINDSIGHT_API_WORKER_ENABLED={"false" if mode=="split" else "true"}',t);t=re.sub(r'HINDSIGHT_API_WORKER_ID=[^\n]*',f'HINDSIGHT_API_WORKER_ID=cloud-{mode}-worker',t);f.write_text(t)
env={k:v for k,v in os.environ.items() if not k.startswith(('HINDSIGHT_','CONTEXTBASE_','CONTEXTDB_')) and k!='PGPASSWORD'};env.update(PYTHON_DOTENV_DISABLED='1',CONTEXTDB_DEPLOY_DIR=str(p/'runtime'),CONTEXTDB_PYTHON=py,PYTHONPATH=str(build/'hindsight-extensions/contextdb-service')+':'+str(build/'hindsight-api-slim'))
if mode=='merged':
 import hashlib
 names=['admin-key.json','api-secrets.json','ui-secrets.json']
 before={n:hashlib.sha256((p/'runtime'/n).read_bytes()).hexdigest() for n in names}
 with (p/'final-offline-init.log').open('w') as log:
  result=subprocess.run(['bash',service,'init'],cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT)
 if result.returncode:raise RuntimeError('Offline repeat init failed')
 after={n:hashlib.sha256((p/'runtime'/n).read_bytes()).hexdigest() for n in names}
 assert before==after,'Secrets changed on repeat init'
 (p/'repeat-init-integrity.json').write_text(json.dumps({'secrets_unchanged':True,'exit_code':0,'before_sha256':before,'after_sha256':after},indent=2))
for kind in (['api','worker'] if mode=='split' else ['api']):
 with (p/(mode+'-'+kind+'.log')).open('a') as log:proc=subprocess.Popen(['bash',service,kind],cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);process[kind]=proc.pid
(p/'processes.json').write_text(json.dumps(process,indent=2));(p/(mode+'-processes.json')).write_text(json.dumps(process,indent=2));print('Mode switched',mode,process)
