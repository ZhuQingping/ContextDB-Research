from pathlib import Path
import asyncio,asyncpg,httpx,subprocess,os,json,secrets,signal,time,io,tarfile,socket,shlex
root=Path('/Users/zhuqingping/Work/Database/Context/hindsight');d=root/'.git'/'deployments'/'cloud-pg-e2e-20261024';d.mkdir(parents=True,exist_ok=False,mode=0o700);d.chmod(0o700)
Path('/tmp/cb-cloud-e2e-path').write_text(str(d)+'\n')
(d/'input').mkdir(mode=0o700);(d/'runtime').mkdir(mode=0o700)
subprocess.run(['git','status','--porcelain'],cwd=root,stdout=(d/'initial-code-status.txt').open('w'),check=True)
(d/'source-commit.txt').write_text(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True))
async def stop_local():
 report=[]
 for port,runtime in [(8888,Path('/Users/zhuqingping/Work/Database/Context/test/hindsight_test/contextdb-local/20261020_150331/runtime')),(8891,Path('/Users/zhuqingping/Work/Database/Context/hindsight/.git/worktrees/rsixdb-contextdb/deployments/2606e8831-20261021/runtime'))]:
  key=json.loads((runtime/'admin-key.json').read_text())['secret']
  async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{port}',headers={'Authorization':'Bearer '+key},timeout=15,trust_env=False) as c:
   r=await c.get('/ext/contextdb/v1/workspaces',params={'limit':100});r.raise_for_status()
   assert r.json()['total']<=100,'Too many spaces to audit stopping'
   active=[]
   for w in r.json()['items']:
    if w['state']!='active':continue
    rr=await c.get(f"/v1/default/banks/{w['bank_id']}/operations",params={'limit':100});rr.raise_for_status()
    active.extend([x['operation_id'] for x in rr.json().get('operations',[]) if x['status'] in ['pending','running']])
   report.append({'port':port,'spaces':r.json()['total'],'active_operations':active})
   assert not active,'Existing instance has active operations; do not interrupt'
 (d/'local-before-stop.json').write_text(json.dumps(report,indent=2))
 for pid in [24217,60928,60926]:
  # Each identity was verified above using ps and listener ownership.
  try:os.kill(pid,signal.SIGTERM)
  except ProcessLookupError:pass
 for n in range(60):
  busy=False
  for port in [8888,9999,8891,9991]:
   s=socket.socket();s.settimeout(.2);busy|=s.connect_ex(('127.0.0.1',port))==0;s.close()
  if not busy:break
  await asyncio.sleep(1)
 else:raise RuntimeError('Old listeners did not exit; no forced kill')
 (d/'local-stop.json').write_text(json.dumps({'stopped_ports':[8888,9999,8891,9991],'forced_kill':False,'local_databases_untouched':True}))
 print('Both local Hindsight deployments gracefully stopped',flush=True)
async def provision():
 c=await asyncpg.connect(host='124.71.227.243',user='root',database='postgres',password=os.environ['PGPASSWORD'],timeout=10)
 role='cb_e2e_service_20261024';db='contextbase_e2e_20261024';pw='Cb!9aZ'+secrets.token_hex(10)
 assert not await c.fetchval('SELECT EXISTS(SELECT FROM pg_roles WHERE rolname=$1)',role)
 assert not await c.fetchval('SELECT EXISTS(SELECT FROM pg_database WHERE datname=$1)',db)
 members=[dict(x) for x in await c.fetch('SELECT * FROM pg_auth_members ORDER BY roleid,member,grantor')]
 (d/'root-members-before.json').write_text(json.dumps(members,default=str))
 await c.execute(f"CREATE ROLE {role} LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS")
 await c.execute(f"CREATE DATABASE {db} OWNER {role} TEMPLATE template0 ENCODING 'UTF8'")
 await c.execute(f'REVOKE ALL ON DATABASE {db} FROM PUBLIC;GRANT CONNECT,CREATE,TEMPORARY ON DATABASE {db} TO {role}')
 q=await asyncpg.connect(host='124.71.227.243',user='root',database=db,password=os.environ['PGPASSWORD'],timeout=10)
 await q.execute(f'REVOKE CREATE ON SCHEMA public FROM PUBLIC;GRANT USAGE ON SCHEMA public TO {role}')
 for ext in ['vector','pg_trgm','btree_gin']:await q.execute(f'CREATE EXTENSION {ext} WITH SCHEMA public')
 await q.close()
 after=[dict(x) for x in await c.fetch('SELECT * FROM pg_auth_members ORDER BY roleid,member,grantor')]
 assert after==members,'Root/member graph unexpectedly changed during provisioning'
 await c.close()
 url=f'postgresql://{role}:<redacted>@124.71.227.243:5432/{db}?ssl=require'
 def secret(name,v):p=d/'input'/name;p.write_text(v+'\n');p.chmod(0o600)
 secret('database-url',url);secret('ui-password',secrets.token_urlsafe(24))
 old=Path('/Users/zhuqingping/Work/Database/Context/test/hindsight_test/contextdb-local/20261020_150331/input')
 secret('maas-key',(old/'maas-key').read_text().strip());oldi=json.loads((old/'intent.json').read_text())
 intent=json.loads((root/'hindsight-extensions/contextdb-service/deployment/intent.example.json').read_text());intent.update(instance_id='cloud-e2e-20261024',cloud_tenant_id='validation-tenant',database_url_file=str(d/'input/database-url'),maas_api_key_file=str(d/'input/maas-key'),ui_password_file=str(d/'input/ui-password'),api_port=8891,ui_port=9991,ui_api_url='http://127.0.0.1:8891',worker_id='cloud-merged-worker',db_pool_max=4,llm_model=oldi.get('llm_model','deepseek-v4.1-flash'))
 if oldi.get('ca_bundle_file'):intent['ca_bundle_file']=oldi['ca_bundle_file']
 secret('intent.json',json.dumps(intent,indent=2));(d/'provision.json').write_text(json.dumps({'db':db,'role':role,'host':'124.71.227.243','root_membership_unchanged':True,'extensions':['vector','pg_trgm','btree_gin'],'ssl':'require'}))
 print('Cloud service database and five-NO role provisioned; no runtime root',flush=True)
asyncio.run(stop_local());asyncio.run(provision())
build=d/'source';build.mkdir()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive','HEAD'],cwd=root))) as archive:archive.extractall(build,filter='data')
for name in ['node_modules','hindsight-control-plane/node_modules','hindsight-clients/typescript/node_modules']:
 if (root/name).exists():subprocess.run(['cp','-cR',str(root/name),str(build/name)],check=True)
(build/'.venv').symlink_to(root/'.venv',target_is_directory=True)
env={k:v for k,v in os.environ.items() if not k.startswith(('HINDSIGHT_','CONTEXTBASE_','CONTEXTDB_')) and k!='PGPASSWORD'};env.update(PYTHON_DOTENV_DISABLED='1',PYTHONPATH=str(build/'hindsight-extensions/contextdb-service')+':'+str(build/'hindsight-api-slim'))
py=str(root/'.venv/bin/python')
def run(name,args):
 with (d/(name+'.log')).open('w') as log:
  r=subprocess.run(args,cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT)
 (d/(name+'-result.json')).write_text(json.dumps({'command':args,'exit_code':r.returncode}))
 if r.returncode:raise RuntimeError(name+' failed; inspect private log')
run('build-ui',[py,'-m','hindsight_ext_contextdb','build-ui','--source-root',str(build)])
run('render',[py,'-m','hindsight_ext_contextdb.deployment','render','--config',str(d/'input/intent.json'),'--directory',str(d/'runtime')])
for name,extra in [('api.env','\nHINDSIGHT_API_HOST=127.0.0.1\nHINDSIGHT_API_WORKER_HTTP_PORT=8892\n'),('ui.env','\nHINDSIGHT_CP_HOST=127.0.0.1\n')]:
 p=d/'runtime'/name;p.write_text(p.read_text()+extra)
env.update(CONTEXTDB_DEPLOY_DIR=str(d/'runtime'),CONTEXTDB_PYTHON=py);service=str(build/'hindsight-extensions/contextdb-service/scripts/service.sh')
run('init',['bash',service,'init']);run('init-repeat',['bash',service,'init'])
process={}
for kind in ['api','ui']:
 with (d/(kind+'.log')).open('a') as log:
  proc=subprocess.Popen(['bash',service,kind],cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);process[kind]=proc.pid
(d/'processes.json').write_text(json.dumps(process,indent=2))
print('Production API/UI started against cloud PG; runtime '+str(d),flush=True)
