from pathlib import Path
import os,asyncio,asyncpg,httpx,json
p=Path(Path('/tmp/cb-cloud-e2e-path').read_text().strip());events=[]
async def main():
 for n in range(60):
  try:
   async with httpx.AsyncClient(timeout=10,trust_env=False) as h:
    r=await h.get('http://127.0.0.1:8891/health/ready');u=await h.get('http://127.0.0.1:9991/')
    if r.status_code==200 and u.status_code in [200,307]:break
  except httpx.HTTPError:pass
  await asyncio.sleep(1)
 else:raise RuntimeError('Runtime readiness failed')
 a=await asyncpg.connect(host='124.71.227.243',user='root',password=os.environ['PGPASSWORD'],database='postgres',timeout=10)
 members=[dict(x) for x in await a.fetch('select * from pg_auth_members order by roleid,member,grantor')];before=json.loads((p/'root-members-before.json').read_text());assert members==before
 report={'source_commit':(p/'source-commit.txt').read_text().strip(),'api_ready':r.status_code,'ui_http':u.status_code,'root_membership_unchanged':True,'database_count':await a.fetchval('select count(*) from pg_database'),'role_count':await a.fetchval('select count(*) from pg_roles'),'temporary_customer_roles':await a.fetchval("select count(*) from pg_roles where rolname='cloud_e2e_customer_cx'"),'temporary_customer_databases':await a.fetchval("select count(*) from pg_database where datname='cloud_e2e_customer_cx'"),'persisted_database':'contextbase_e2e_20261024','persisted_role':'cb_e2e_service_20261024'}
 await a.close()
 c=await asyncpg.connect((p/'input/database-url').read_text().strip(),timeout=10)
 report['service_identity']=dict(await c.fetchrow('select current_user,current_database(),s.ssl,s.version as tls_version,s.cipher from pg_stat_ssl s where pid=pg_backend_pid()'))
 report['runtime_connections']=[dict(x) for x in await c.fetch('select usename,application_name,count(*) from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid() group by 1,2')]
 report['public_business_table_count']=await c.fetchval("select count(*) from pg_tables where schemaname='public'")
 report['metadata_tables']=await c.fetchval("select count(*) from pg_tables where schemaname='ctxdb_meta'")
 report['workspaces']=[dict(x) for x in await c.fetch('select bank_id,state from ctxdb_meta.workspaces order by bank_id')]
 report['temporary_customer_schema_count']=await c.fetchval("select count(*) from pg_namespace where nspname='own_customer_cx'")
 report['active_task_count']=0
 for w in report['workspaces']:
  row=await c.fetchval(f'''select count(*) from "ctxdb_ws_{w['bank_id']}".async_operations where status in ('pending','running')''');report['active_task_count']+=row
 await c.close()
 q=await asyncpg.connect(host='124.71.227.243',user='root',password=os.environ['PGPASSWORD'],database='supabase_db',timeout=10)
 report['supabase_user_table_count']=await q.fetchval("select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where c.relkind in('r','p') and n.nspname not like 'pg_%' and n.nspname<>'information_schema'");report['supabase_policy_count']=await q.fetchval('select count(*) from pg_policies');await q.close()
 assert report['public_business_table_count']==0 and report['metadata_tables']==6 and report['active_task_count']==0
 assert report['temporary_customer_roles']==report['temporary_customer_databases']==report['temporary_customer_schema_count']==0
 assert all(x['usename']=='cb_e2e_service_20261024' for x in report['runtime_connections'])
 (p/'final-audit.json').write_text(json.dumps(report,ensure_ascii=False,default=str,indent=2));print(json.dumps(report,ensure_ascii=False,default=str,indent=2))
asyncio.run(main())
