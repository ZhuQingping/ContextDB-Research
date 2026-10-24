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
async def resume():
 global events,outfile
 events=[x for x in json.loads((P/'attempt1-merged-e2e.json').read_text())['cases'] if x['passed']]
 outfile=P/'merged-final.json'; mode='merged';a='cloud_merged_a';b='cloud_merged_b';temp='cloud_merged_cycle';mgr='/ext/contextdb/v1';path=f'/v1/default/banks/{a}/memories/recall'
 sdklist=[]
 async with httpx.AsyncClient(timeout=120,trust_env=False) as http:
  async def req(name,method,path,status=200,key=admin,**kw):
   headers=kw.pop('headers',{});headers={**headers,**({'Authorization':'Bearer '+key} if key else {})};r=await http.request(method,base+path,headers=headers,**kw);record(name,r.status_code==status,{'actual_status':r.status_code,'expected':status});return r
  ur=await http.get(base+mgr+'/users',headers={'Authorization':'Bearer '+admin},params={'q':'Cloud merged User Updated'});u=next(x for x in ur.json()['items'] if x['name']=='Cloud merged User Updated');uid=u['user_id']
  aw=(await http.get(base+mgr+'/workspaces/'+a,headers={'Authorization':'Bearer '+admin})).json()
  async def issue(name,perm,bank):
   r=await http.post(base+mgr+f'/users/{uid}/keys',headers={'Authorization':'Bearer '+admin},json={'name':name,'authorization':{'mode':'selected','workspaces':[{'bank_id':bank,'permission':perm}]}});r.raise_for_status();return r.json()
  rw=await issue('Resume write key','read_write',a);ro=await issue('Resume readonly key','read',a);other=await issue('Resume other key','read_write',b)
  sdk=Hindsight(base_url=base,api_key=rw['secret']);reader=Hindsight(base_url=base,api_key=ro['secret']);outsider=Hindsight(base_url=base,api_key=other['secret']);adm=Hindsight(base_url=base,api_key=admin);sdklist=[sdk,reader,outsider,adm]
  chunk=(await sdk.documents.list_document_chunks(a,'path/中文%20_part_~_1')).items[0]
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

try:asyncio.run(resume())
except Exception as e:
 (P/'merged-resume-error.txt').write_text(type(e).__name__+': '+str(e).splitlines()[0][:200]);raise
