from pathlib import Path
import asyncio,json,os,sys,time,hashlib
import httpx,asyncpg
from hindsight_client import Hindsight
from fastmcp import Client as MCP
P=Path(Path('/tmp/cb-cloud-e2e-path').read_text().strip());mode=sys.argv[1] if len(sys.argv)>1 else 'merged';base='http://127.0.0.1:8891';ui='http://127.0.0.1:9991';admin=json.loads((P/'runtime/admin-key.json').read_text())['secret'];events=[]
state={};outfile=P/(mode+'-e2e.json')
def record(name,ok,detail=None):
 events.append({'case':name,'passed':bool(ok),'detail':detail});outfile.write_text(json.dumps({'mode':mode,'cases':events},ensure_ascii=False,indent=2));print(name,'PASS' if ok else 'FAIL',flush=True)
 if not ok:raise AssertionError(name+': '+str(detail))
async def main():
 sdklist=[]
 async with httpx.AsyncClient(timeout=120,trust_env=False) as http:
  for n in range(120):
   try:
    r=await http.get(base+'/health/ready')
    if r.status_code==200:break
   except httpx.HTTPError:pass
   await asyncio.sleep(1)
  else:raise RuntimeError('API readiness timeout')
  record('api-readiness',True)
  async def req(name,method,path,status=200,key=admin,**kw):
   headers=kw.pop('headers',{});headers={**headers,**({'Authorization':'Bearer '+key} if key else {})}
   r=await http.request(method,base+path,headers=headers,**kw);record(name,r.status_code==status,{'actual_status':r.status_code,'expected':status});return r
  for n in range(60):
   try:
    r=await http.get(ui+'/')
    if r.status_code in [200,307]:break
   except httpx.HTTPError:pass
   await asyncio.sleep(1)
  login=await http.post(ui+'/api/auth/login',headers={'Origin':ui},json={'key':(P/'input/ui-password').read_text().strip()});record('ui-login',login.status_code==200)
  r=await http.get(ui+'/api/contextdb/workspaces');record('ui-proxy-management',r.status_code==200)
  await req('admin-identity','GET','/ext/contextdb/v1/admin/identity')
  a=f'cloud_{mode}_a';b=f'cloud_{mode}_b';temp=f'cloud_{mode}_cycle';mgr='/ext/contextdb/v1'
  aw=(await req('workspace-create-a','POST',mgr+'/workspaces',201,json={'name':a,'description':'Cloud PG E2E '+mode})).json()
  bw=(await req('workspace-create-b','POST',mgr+'/workspaces',201,json={'name':b})).json()
  sr=await req('workspace-search','GET',mgr+'/workspaces',params={'q':a,'limit':1,'offset':0});record('workspace-search-result',sr.json()['total']==1)
  gr=await req('workspace-get','GET',mgr+'/workspaces/'+a);record('workspace-etag',bool(gr.headers.get('etag')))
  u=(await req('user-create','POST',mgr+'/users',201,json={'name':'Cloud '+mode+' User'})).json();uid=u['user_id']
  ur=await req('user-list','GET',mgr+'/users',params={'q':'Cloud '+mode});record('user-list-match',ur.json()['total']==1)
  pu=await req('user-edit','PATCH',mgr+'/users/'+uid,headers={'If-Match':f'"{u["version"]}"'},json={'name':'Cloud '+mode+' User Updated'});u=pu.json()
  async def issue(label,permission='read_write',bank=a,user_id=uid):
   return (await req(label,'POST',mgr+f'/users/{user_id}/keys',201,json={'name':label,'authorization':{'mode':'selected','workspaces':[{'bank_id':bank,'permission':permission}]}})).json()
  rw=await issue('key-create-rw');ro=await issue('key-create-ro','read');other=await issue('key-create-other',bank=b)
  lr=await req('key-list','GET',mgr+f'/users/{uid}/keys');record('key-list-secret-not-returned',all('secret' not in x for x in lr.json()['items']))
  await req('key-edit','PATCH',mgr+f'/users/{uid}/keys/{rw["key_id"]}',headers={'If-Match':f'"{rw["version"]}"'},json={'name':'Cloud verified write key'})
  path=f'/v1/default/banks/{a}/memories/recall'
  await req('anonymous-denied','POST',path,401,key=None,json={'query':'Lighthouse'})
  await req('invalid-key-denied','POST',path,401,key='invalid-key',json={'query':'Lighthouse'})
  await req('cross-space-denied','POST',path,403,key=other['secret'],json={'query':'Lighthouse'})
  await req('readonly-write-denied','POST',f'/v1/default/banks/{a}/memories',403,key=ro['secret'],json={'items':[{'content':'forbidden'}]})
  await req('business-management-denied','GET',mgr+'/users',403,key=rw['secret'])
  config=await req('business-config-projection','GET',f'/v1/default/banks/{a}/config',key=ro['secret']);record('business-config-has-no-visible-fields',config.json().get('config')=={} and config.json().get('overrides')=={})
  sdk=Hindsight(base_url=base,api_key=rw['secret']);reader=Hindsight(base_url=base,api_key=ro['secret']);outsider=Hindsight(base_url=base,api_key=other['secret']);adm=Hindsight(base_url=base,api_key=admin);sdklist=[sdk,reader,outsider,adm]
  doc='path/中文%20_part_~_1';text='Alice maintains the Lighthouse project. The project verification code is LIGHTHOUSE-20261024. Bob maintains the separate Atlas project.'
  checkpoint=P/(mode+'-private-checkpoint.json');checkpoint.write_text(json.dumps({'u':u,'rw':rw,'ro':ro,'other':other,'aw':aw,'a':a,'b':b,'uid':uid}));checkpoint.chmod(0o600)
  ret=await sdk.aretain(bank_id=a,content=text,document_id=doc,retain_async=True);record('sdk-async-retain-accepted',bool(ret.operation_id))
  stable=0
  for n in range(180):
   ops=await sdk.operations.list_operations(a,limit=100)
   failed=[x for x in ops.operations if x.status=='failed'];busy=[x for x in ops.operations if x.status in ['pending','running']];matched=next((x for x in ops.operations if x.operation_id==ret.operation_id),None)
   if failed:record('worker-completes-retain',False,{'failed_operations':len(failed)})
   if matched and matched.status=='completed' and not busy:stable+=1
   else:stable=0
   if stable>=2:break
   await asyncio.sleep(2)
  else:raise RuntimeError('Worker not settled within 6 minutes')
  record('worker-completes-retain',True,{'operation_id':ret.operation_id})
  recalled=await reader.arecall(bank_id=a,query='Who maintains Lighthouse?',include_chunks=True);record('sdk-readonly-recall',len(recalled.results)>0,{'results':len(recalled.results),'chunks':len(recalled.chunks or {})})
  listed=await sdk.documents.list_document_chunks(a,doc);record('sdk-list-document-chunks',len(listed.items)>0)
  chunk=listed.items[0]
  for label,s in [('rw',sdk),('ro',reader),('admin',adm)]:
   got=await s.documents.get_chunk(chunk.chunk_id);record('sdk-get-chunk-'+label,got.chunk_text==text)
  try:await outsider.documents.get_chunk(chunk.chunk_id);record('cross-space-chunk-denied',False)
  except Exception as e:record('cross-space-chunk-denied',getattr(e,'status',None)==403,{'status':getattr(e,'status',None)})
  empty=await outsider.arecall(bank_id=b,query='Lighthouse');record('other-schema-empty',not empty.results)
  reflected=await reader.areflect(bank_id=a,query='Who maintains Lighthouse? Answer briefly.');record('sdk-reflect',bool(reflected.text),{'answer_nonempty':bool(reflected.text)})
  async with MCP(base+'/mcp/'+a+'/',auth=ro['secret']) as mcp:
   tools={x.name for x in await mcp.list_tools()};record('mcp-tool-scope','recall' in tools and 'create_bank' not in tools and 'delete_bank' not in tools)
   r=await mcp.call_tool('recall',{'query':'Who maintains Lighthouse?'});record('mcp-recall',not r.is_error)
  # Disable/reactivate the same synthetic user with version checks.
  disabled=await req('user-disable','PATCH',mgr+'/users/'+uid,headers={'If-Match':f'"{u["version"]}"'},json={'status':'disabled'});u=disabled.json()
  await req('disabled-key-denied','POST',path,401,key=rw['secret'],json={'query':'Lighthouse'})
  active=await req('user-reactivate','PATCH',mgr+'/users/'+uid,headers={'If-Match':f'"{u["version"]}"'},json={'status':'active'});u=active.json()
  await req('key-revoke','DELETE',mgr+f'/users/{uid}/keys/{ro["key_id"]}',204)
  await req('revoked-key-denied','POST',path,401,key=ro['secret'],json={'query':'Lighthouse'})
  # Empty synthetic lifecycle: no business requests or pending jobs target this bank.
  cycle=(await req('cycle-create','POST',mgr+'/workspaces',201,json={'name':temp})).json();g=await req('cycle-snapshot','GET',mgr+'/workspaces/'+temp)
  await req('cycle-delete','DELETE',mgr+'/workspaces/'+temp,204,headers={'If-Match':g.headers['etag']})
  await req('cycle-missing','GET',mgr+'/workspaces/'+temp,404)
  new=(await req('cycle-recreate','POST',mgr+'/workspaces',201,json={'name':temp})).json();record('cycle-new-uuid',cycle['workspace_id']!=new['workspace_id'])
  await req('stale-delete-rejected','DELETE',mgr+'/workspaces/'+temp,412,headers={'If-Match':g.headers['etag']})
  g=await req('cycle-new-snapshot','GET',mgr+'/workspaces/'+temp);await req('cycle-cleanup','DELETE',mgr+'/workspaces/'+temp,204,headers={'If-Match':g.headers['etag']})
  du=(await req('disposable-user-create','POST',mgr+'/users',201,json={'name':'Disposable '+mode})).json();await req('disposable-user-delete','DELETE',mgr+'/users/'+du['user_id'],204)
  state={'user_id':uid,'bank_a':a,'bank_b':b,'workspace_id':aw['workspace_id'],'write_key':rw['secret'],'other_key':other['secret'],'chunk_id':chunk.chunk_id};f=P/(mode+'-private-state.json');f.write_text(json.dumps(state));f.chmod(0o600)
  for s in sdklist:await s.aclose()
 c=await asyncpg.connect((P/'input/database-url').read_text().strip(),timeout=10)
 q=await c.fetchrow('select current_user,current_database(),s.ssl from pg_stat_ssl s where pid=pg_backend_pid()');record('pg-session-service-tls',q['current_user']=='cb_e2e_service_20261024' and q['ssl'],dict(q))
 pub=await c.fetchval("select count(*) from pg_tables where schemaname='public'");record('public-no-business-tables-after-story',pub==0,{'count':pub})
 count=await c.fetchval("select count(*) from pg_tables where schemaname='ctxdb_meta'");record('metadata-six-tables',count==6,{'count':count})
 schema=await c.fetchval('select schema_name from ctxdb_meta.workspaces where bank_id=$1',a);owner=await c.fetchval('select pg_get_userbyid(nspowner) from pg_namespace where nspname=$1',schema);record('workspace-owned-by-service',owner=='cb_e2e_service_20261024',{'schema':schema,'owner':owner})
 await c.close();print('MODE COMPLETE',mode,len(events),flush=True)
try:asyncio.run(main())
except Exception as e:
 # Do not print SDK exception bodies that could contain request credentials.
 (P/(mode+'-error.txt')).write_text(type(e).__name__+': '+str(e).splitlines()[0][:200]);print('FAILED',type(e).__name__,flush=True);raise SystemExit(1)
