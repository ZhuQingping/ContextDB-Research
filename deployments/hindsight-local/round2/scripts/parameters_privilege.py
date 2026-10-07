import asyncio,json,os,secrets,signal,subprocess,time
from pathlib import Path
import asyncpg,httpx
base=Path(__file__).resolve().parents[1];root=base.parent
async def main():
    tag=str(int(time.time()));schema='round2_priv_'+tag;role='round2_run_'+tag;password=secrets.token_hex(24);key=secrets.token_urlsafe(32)
    private=base/'.privilege';private.mkdir(mode=0o700,exist_ok=True)
    secretsfile=private/(tag+'.json');secretsfile.write_text(json.dumps({'role':role,'password':password,'key':key}));secretsfile.chmod(0o600)
    admin='postgresql://hindsight:hindsight@127.0.0.1:55433/hindsight';runtime=f'postgresql://{role}:{password}@127.0.0.1:55433/hindsight'
    result={'schema':schema,'role':role,'checks':[],'scope':'pre-migrated single-schema local PG, no RDS or complete runtime-path certification'}
    c=await asyncpg.connect(admin);await c.execute(f'CREATE SCHEMA {schema}');await c.execute(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT")
    env=os.environ.copy();env.update(json.loads((root/'config.json').read_text()));env.update({'HINDSIGHT_API_DATABASE_URL':admin,'HINDSIGHT_API_DATABASE_SCHEMA':schema})
    with (private/(tag+'-migration.log')).open('w') as log:
        p=subprocess.run([str(root/'.venv/bin/hindsight-admin'),'run-db-migration','--schema',schema],env=env,stdout=log,stderr=subprocess.STDOUT)
    result['migration_exit']=p.returncode
    if p.returncode: raise RuntimeError('pre-migration failed; see private log')
    await c.execute(f'GRANT USAGE ON SCHEMA {schema} TO {role}; GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {schema} TO {role}; GRANT USAGE,SELECT,UPDATE ON ALL SEQUENCES IN SCHEMA {schema} TO {role}')
    result['runtime_privileges']=dict(await c.fetchrow("SELECT has_schema_privilege($1,$2,'USAGE') AS usage,has_schema_privilege($1,$2,'CREATE') AS create",role,schema));result['fsync']=await c.fetchval('SHOW fsync');await c.close()
    env.update({'HINDSIGHT_API_DATABASE_URL':runtime,'HINDSIGHT_API_PORT':'8894','HINDSIGHT_API_RUN_MIGRATIONS_ON_STARTUP':'false','HINDSIGHT_API_WORKER_ENABLED':'false','HINDSIGHT_API_MCP_ENABLED':'false','HINDSIGHT_API_TENANT_EXTENSION':'hindsight_api.extensions.builtin.tenant:ApiKeyTenantExtension','HINDSIGHT_API_TENANT_API_KEY':key,'HINDSIGHT_API_CONSOLIDATION_RECONCILE_INTERVAL_SECONDS':'0','HINDSIGHT_API_MENTAL_MODEL_REFRESH_TICK_SECONDS':'0','HINDSIGHT_API_LLM_TRACE_ENABLED':'false','HINDSIGHT_API_LLM_TRACE_RETENTION_DAYS':'-1'})
    proc=None
    try:
        with (private/(tag+'-api.log')).open('w') as log:
            proc=subprocess.Popen([str(root/'.venv/bin/hindsight-api')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        with httpx.Client(base_url='http://127.0.0.1:8894',trust_env=False,headers={'Authorization':'Bearer '+key},timeout=30) as h:
            for _ in range(60):
                if proc.poll() is not None: break
                try:
                    r=h.get('/health')
                    if r.status_code==200: break
                except httpx.HTTPError: pass
                await asyncio.sleep(1)
            result['api_alive']=proc.poll() is None
            if result['api_alive']:
                for name,method,path,body in [('health','GET','/health',None),('create-bank','PUT','/v1/default/banks/round2-privilege',{}),('config','PATCH','/v1/default/banks/round2-privilege/config',{'updates':{'retain_extraction_mode':'chunks','enable_observations':False,'enable_auto_consolidation':False}}),('retain','POST','/v1/default/banks/round2-privilege/memories',{'items':[{'content':'Synthetic database incident ZX8932 fixed by reducing connection pool size.','document_id':'privilege-doc'}]}),('recall','POST','/v1/default/banks/round2-privilege/memories/recall',{'query':'ZX8932 connection pool','budget':'low','max_tokens':300})]:
                    try:
                        r=h.request(method,path,json=body) if body is not None else h.request(method,path)
                        result['checks'].append({'name':name,'status':r.status_code,'response':r.json()})
                    except Exception as exc: result['checks'].append({'name':name,'error':type(exc).__name__})
    finally:
        if proc and proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try: proc.wait(timeout=15)
            except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        result['temporary_api_stopped']=True
        for kind in ['api','migration']:
            p=private/(tag+'-'+kind+'.log')
            if p.exists():
                clean=p.read_text().replace(password,'[REDACTED]').replace(key,'[REDACTED]')
                (base/'evidence'/('parameters-privilege-'+kind+'.log')).write_text(clean)
        result['all_http_checks_passed']=len(result['checks'])==5 and all(x.get('status')==200 for x in result['checks'])
        (base/'evidence/parameters-privilege-results.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
asyncio.run(main())
