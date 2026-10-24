import asyncio,asyncpg,os,json
from pathlib import Path
p=Path(__file__).resolve().parent;events=[];D='doc_sql_20261024_cx';R='doc_app_20261024_cx'
async def conn(db='postgres'):
 return await asyncpg.connect(host='124.71.227.243',user='root',database=db,password=os.environ['PGPASSWORD'],timeout=10,server_settings={'statement_timeout':'20000','lock_timeout':'3000'})
async def run(c,label,sql):
 try:x={'id':label,'sql':sql,'sqlstate':'00000','result':[dict(x) for x in await c.fetch(sql)]}
 except asyncpg.PostgresError as e:x={'id':label,'sql':sql,'sqlstate':e.sqlstate,'error':str(e).splitlines()[0]}
 events.append(x);return x
async def main():
 a=await conn();q=None;madeRole=False;madeDb=False
 baseline=[dict(x) for x in await a.fetch('SELECT * FROM pg_auth_members ORDER BY roleid,member,grantor')]
 assert not await a.fetchval('SELECT EXISTS(SELECT FROM pg_database WHERE datname=$1)',D)
 assert not await a.fetchval('SELECT EXISTS(SELECT FROM pg_roles WHERE rolname=$1)',R)
 try:
  await a.execute(f'CREATE DATABASE {D} OWNER root TEMPLATE template0');madeDb=True
  await a.execute(f'CREATE ROLE {R} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS');madeRole=True
  q=await conn(D)
  await run(q,'default-search-path','SHOW search_path')
  await q.execute('CREATE SCHEMA biz_ext_cx AUTHORIZATION root;CREATE EXTENSION pg_trgm')
  await run(q,'default-pg-trgm-schema',"SELECT extname,nspname FROM pg_extension JOIN pg_namespace ON extnamespace=pg_namespace.oid WHERE extname='pg_trgm'")
  await q.execute(f'GRANT USAGE ON SCHEMA public,biz_ext_cx TO {R};CREATE TABLE public.before_cx(id int);ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO {R};CREATE TABLE public.after_cx(id serial)')
  await run(q,'existing-vs-future-acl',f"SELECT has_table_privilege('{R}','public.before_cx','SELECT') AS existing_table,has_table_privilege('{R}','public.after_cx','INSERT') AS future_table,has_sequence_privilege('{R}','public.after_cx_id_seq','USAGE') AS serial_sequence,has_schema_privilege('{R}','public','CREATE') AS create_public")
  await run(q,'valid-until',f"ALTER ROLE {R} VALID UNTIL '2027-12-31'")
  await run(q,'valid-until-read',f"SELECT rolname,rolvaliduntil FROM pg_roles WHERE rolname='{R}'")
  await run(q,'schema-public-acl',"SELECT nspname,nspacl FROM pg_namespace WHERE nspname='public'")
 finally:
  if q:await q.close()
  if madeDb:await a.execute(f'DROP DATABASE {D} WITH(FORCE)')
  if madeRole:await a.execute(f'DROP ROLE {R}')
  after=[dict(x) for x in await a.fetch('SELECT * FROM pg_auth_members ORDER BY roleid,member,grantor')]
  cleanup={'databases':await a.fetchval('SELECT count(*) FROM pg_database WHERE datname=$1',D),'roles':await a.fetchval('SELECT count(*) FROM pg_roles WHERE rolname=$1',R),'membership_restored':baseline==after};await a.close()
  (p/'cloud-doc-sql.json').write_text(json.dumps(events,default=str,ensure_ascii=False,indent=2));(p/'cloud-doc-sql-cleanup.json').write_text(json.dumps(cleanup,indent=2));print(json.dumps(events,default=str,ensure_ascii=False));print(cleanup)
  assert cleanup=={'databases':0,'roles':0,'membership_restored':True}
asyncio.run(main())
