import asyncio,asyncpg,os,json,secrets
from pathlib import Path
p=Path(Path('/tmp/cb-cloud-e2e-path').read_text().strip());root=Path('/Users/zhuqingping/Work/Database/Context/hindsight');R='cloud_e2e_customer_cx';D='cloud_e2e_customer_cx';SERVICE='cb_e2e_service_20261024';MAIN='contextbase_e2e_20261024';records=[]
async def conn(user='root',db='postgres',password=None):return await asyncpg.connect(host='124.71.227.243',user=user,password=password or os.environ['PGPASSWORD'],database=db,timeout=10)
async def test(c,name,sql,status='00000'):
 try:r=(await c.execute(sql)) if ';' in sql.strip().rstrip(';') else [dict(x) for x in await c.fetch(sql)];actual='00000'
 except asyncpg.PostgresError as e:r=str(e).splitlines()[0];actual=e.sqlstate
 records.append({'case':name,'sql':sql,'expected':status,'actual':actual,'passed':actual==status,'result':r});print(name,actual,flush=True)
 if actual!=status:raise RuntimeError(name+' unexpected SQLSTATE '+actual)
async def main():
 a=await conn();created=False;dbcreated=False;cc=None;svc=None;biz=None;mr=None
 before=[dict(x) for x in await a.fetch('select * from pg_auth_members order by roleid,member,grantor')]
 assert not await a.fetchval('select exists(select from pg_roles where rolname=$1)',R)
 pw='Cx!9aZ'+secrets.token_hex(10)
 try:
  await a.execute(f"CREATE ROLE {R} LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS");created=True
  await a.execute(f'CREATE DATABASE {D} OWNER {R} TEMPLATE template0');dbcreated=True
  await a.execute(f'REVOKE ALL ON DATABASE {D} FROM PUBLIC')
  biz=await conn(R,D,pw);await test(biz,'customer-own-business-write',"CREATE SCHEMA own_biz_cx;CREATE TABLE own_biz_cx.notes_cx(body text);INSERT INTO own_biz_cx.notes_cx VALUES('mine')")
  await test(biz,'customer-own-business-read','SELECT * FROM own_biz_cx.notes_cx')
  try:
   x=await conn(R,MAIN,pw);await x.close();raise RuntimeError('customer unexpectedly connected before grant')
  except asyncpg.InsufficientPrivilegeError:records.append({'case':'independent-db-customer-connect-service-denied','passed':True,'actual':'42501'})
  svc=await asyncpg.connect((p/'input/database-url').read_text().strip(),timeout=10)
  try:
   url=(p/'input/database-url').read_text().strip().replace('/'+MAIN,'/'+D);x=await asyncpg.connect(url,timeout=10);await x.close();raise RuntimeError('service unexpectedly connected to customer DB')
  except asyncpg.InsufficientPrivilegeError:records.append({'case':'service-connect-independent-customer-db-denied','passed':True,'actual':'42501'})
  await a.execute(f'GRANT CONNECT,TEMPORARY ON DATABASE {MAIN} TO {R}')
  mr=await conn(db=MAIN);await mr.execute(f'CREATE SCHEMA own_customer_cx AUTHORIZATION {R}')
  schemas=['ctxdb_meta']+[r['schema_name'] for r in await svc.fetch("select schema_name from ctxdb_meta.workspaces where state='active'")]
  for sch in schemas:
   await svc.execute("select set_config('contextdb.boundary_owner',$1,false)",SERVICE);await svc.execute("select set_config('contextdb.boundary_customer',$1,false)",R);await svc.execute("select set_config('contextdb.boundary_schema',$1,false)",sch)
   await svc.execute((root/'hindsight-extensions/contextdb-service/deployment/pg-role-boundary.sql').read_text());records.append({'case':'apply-boundary-'+sch,'passed':True})
  cc=await conn(R,MAIN,pw)
  await test(cc,'customer-own-schema-create',"CREATE TABLE own_customer_cx.notes_cx(body text);INSERT INTO own_customer_cx.notes_cx VALUES('mine')")
  await test(cc,'customer-own-schema-select','SELECT * FROM own_customer_cx.notes_cx')
  await test(cc,'shared-vector-works',"SELECT '[1,2]'::public.vector")
  await test(cc,'protected-metadata-read','SELECT 1 FROM ctxdb_meta.users LIMIT 1','42501')
  await test(cc,'protected-metadata-update',"UPDATE ctxdb_meta.users SET name='tampered'",'42501')
  for sch in schemas[1:]:
   for name,sql in [('read',f'SELECT 1 FROM "{sch}".memory_units LIMIT 1'),('delete',f'DELETE FROM "{sch}".memory_units'),('truncate',f'TRUNCATE "{sch}".memory_units'),('drop',f'DROP SCHEMA "{sch}" CASCADE')]:await test(cc,name+'-'+sch,sql,'42501')
  await test(cc,'cannot-switch-owner',f'SET ROLE {SERVICE}','42501')
  # Root counterexample reads only synthetic names/counts, never existing platform rows.
  await test(mr,'root-no-service-membership',f"SELECT pg_has_role('root','{SERVICE}','MEMBER') AS member")
  await test(mr,'root-reads-synthetic-service-metadata',"SELECT name FROM ctxdb_meta.users WHERE name LIKE 'Cloud %' ORDER BY name")
  await test(svc,'runtime-pg-identities',"SELECT usename,application_name,count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() GROUP BY 1,2 ORDER BY 1,2")
 finally:
  for q in [cc,svc,biz]:
   if q and not q.is_closed():await q.close()
  if mr:
   await mr.execute('DROP SCHEMA IF EXISTS own_customer_cx CASCADE');await mr.close()
   await a.execute(f'REVOKE ALL ON DATABASE {MAIN} FROM {R}')
  if dbcreated:await a.execute(f'DROP DATABASE {D} WITH(FORCE)')
  if created:await a.execute(f'DROP ROLE {R}')
  after=[dict(x) for x in await a.fetch('select * from pg_auth_members order by roleid,member,grantor')]
  clean={'role_count':await a.fetchval('select count(*) from pg_roles where rolname=$1',R),'db_count':await a.fetchval('select count(*) from pg_database where datname=$1',D),'root_membership_unchanged':before==after};await a.close();assert not clean['role_count'] and not clean['db_count'] and clean['root_membership_unchanged']
  (p/'sql-boundary.json').write_text(json.dumps({'cases':records,'cleanup':clean},ensure_ascii=False,default=str,indent=2))
asyncio.run(main())
