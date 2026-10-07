import json,os,signal,subprocess,time
from pathlib import Path
import httpx
base=Path(__file__).resolve().parents[1];root=base.parent
r=json.loads((base/'evidence/parameters-privilege-results.json').read_text());tag=r['schema'].removeprefix('round2_priv_');private=base/'.privilege';s=json.loads((private/(tag+'.json')).read_text());env=os.environ.copy();env.update(json.loads((root/'config.json').read_text()));env.update({'HINDSIGHT_API_PORT':'8894','HINDSIGHT_API_DATABASE_SCHEMA':r['schema'],'HINDSIGHT_API_RUN_MIGRATIONS_ON_STARTUP':'false','HINDSIGHT_API_WORKER_ENABLED':'false','HINDSIGHT_API_MCP_ENABLED':'false','HINDSIGHT_API_TENANT_EXTENSION':'hindsight_api.extensions.builtin.tenant:ApiKeyTenantExtension','HINDSIGHT_API_TENANT_API_KEY':s['key'],'HINDSIGHT_API_CONSOLIDATION_RECONCILE_INTERVAL_SECONDS':'0','HINDSIGHT_API_MENTAL_MODEL_REFRESH_TICK_SECONDS':'0','HINDSIGHT_API_LLM_TRACE_ENABLED':'false','HINDSIGHT_API_LLM_TRACE_RETENTION_DAYS':'-1'})
rows=[]
for phase in ['admin-precreate','dml-runtime']:
    env['HINDSIGHT_API_DATABASE_URL']='postgresql://hindsight:hindsight@127.0.0.1:55433/hindsight' if phase=='admin-precreate' else f"postgresql://{s['role']}:{s['password']}@127.0.0.1:55433/hindsight"
    logpath=private/(tag+'-'+phase+'.log')
    with logpath.open('w') as log: p=subprocess.Popen([str(root/'.venv/bin/hindsight-api')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        with httpx.Client(base_url='http://127.0.0.1:8894',trust_env=False,headers={'Authorization':'Bearer '+s['key']},timeout=40) as h:
            for _ in range(50):
                try:
                    if h.get('/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(1)
            cases=[('precreate','PUT','',{})] if phase=='admin-precreate' else [('configure','PATCH','/config',{'updates':{'retain_extraction_mode':'chunks','enable_observations':False,'enable_auto_consolidation':False}}),('retain','POST','/memories',{'items':[{'content':'Synthetic ZX8932 connection pool reduced from 200 to 50.','document_id':'precreated-doc'}]}),('recall','POST','/memories/recall',{'query':'ZX8932 connection pool','max_tokens':300,'budget':'low'})]
            for name,method,path,body in cases:
                x=h.request(method,'/v1/default/banks/round2-precreated'+path,json=body)
                rows.append({'phase':phase,'name':name,'status':x.status_code,'response':x.json()})
    finally:
        os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=20)
        clean=logpath.read_text().replace(s['password'],'[REDACTED]').replace(s['key'],'[REDACTED]');(base/'evidence'/('parameters-privilege-'+phase+'.log')).write_text(clean)
result={'schema':r['schema'],'role':r['role'],'checks':rows,'temporary_api_stopped':True,'all_http_checks_passed':all(x['status']==200 for x in rows),'fsync':'off','scope':'privileged precreation followed by no-DDL runtime on one synthetic bank'}
(base/'evidence/parameters-privilege-prebank.json').write_text(json.dumps(result,indent=2));print(json.dumps({'statuses':[x['status'] for x in rows],'passed':result['all_http_checks_passed']}))
