import asyncio,asyncpg,os,json
from pathlib import Path
p=Path(__file__).resolve().parent
async def main():
 out={}
 for db in ['supabase_db','_supabase','postgres']:
  c=await asyncpg.connect(host='124.71.227.243',port=5432,user='root',password=os.environ['PGPASSWORD'],database=db,timeout=10,server_settings={'statement_timeout':'20000','default_transaction_read_only':'on'})
  qs={
  'schemas':"SELECT nspname,pg_get_userbyid(nspowner) AS owner,nspacl,has_schema_privilege('root',oid,'USAGE') AS root_usage,has_schema_privilege('root',oid,'CREATE') AS root_create FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname <> 'information_schema' ORDER BY 1",
  'extensions':"SELECT extname,extversion,nspname FROM pg_extension JOIN pg_namespace ON extnamespace=pg_namespace.oid ORDER BY 1",
  'tables':"SELECT n.nspname,c.relname,pg_get_userbyid(c.relowner) AS owner,c.relrowsecurity,c.relforcerowsecurity,has_table_privilege('root',c.oid,'SELECT') AS root_select,has_table_privilege('root',c.oid,'UPDATE') AS root_update FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('r','p') AND n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema' ORDER BY 1,2",
  'policies':"SELECT schemaname,tablename,policyname,roles,cmd FROM pg_policies ORDER BY 1,2,3",
  'root_membership':"SELECT pg_has_role('root','service_role','MEMBER') AS member,pg_has_role('root','service_role','USAGE') AS usage,pg_has_role('root','service_role','SET') AS can_set",
  'crossdb':"SELECT e.extname FROM pg_extension e WHERE extname IN ('dblink','postgres_fdw')",
  }
  out[db]={}
  for k,q in qs.items():
   try:out[db][k]={'sql':q,'rows':[dict(x) for x in await c.fetch(q)]}
   except asyncpg.PostgresError as e:out[db][k]={'sql':q,'sqlstate':e.sqlstate,'error':str(e).splitlines()[0]}
  await c.close()
 (p/'cloud-readonly.json').write_text(json.dumps(out,default=str,indent=2,ensure_ascii=False))
 for db,d in out.items():
  print(db, 'schemas',len(d['schemas'].get('rows',[])),'tables',len(d['tables'].get('rows',[])),'policies',len(d['policies'].get('rows',[])))
  print('schemas',[(x['nspname'],x['owner'],x['root_create']) for x in d['schemas'].get('rows',[])])
  print('crossdb',d['crossdb'])
asyncio.run(main())
