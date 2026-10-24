import asyncio,asyncpg,os,secrets,json,re
from pathlib import Path
P=Path(__file__).resolve().parent; ROOT=Path('/Users/zhuqingping/Work/Database/Context/hindsight')
PREFIX='iso_20261024'; S=PREFIX+'_service_cx';B=PREFIX+'_biz_cx';C=PREFIX+'_customer_cx'; D=PREFIX+'_ctxdb_cx';BD=PREFIX+'_bizdb_cx';SC=PREFIX+'_rls_cx'
roles=[S,B,C];dbs=[D,BD]; passwords={r:'Cx!9aZ'+secrets.token_hex(10) for r in roles};events=[]
def safe(sql):
 return re.sub(r"PASSWORD\s+'[^']*'","PASSWORD '<generated-secret>'",sql,flags=re.I)
async def connect(user='root',db='postgres',password=None):
 return await asyncpg.connect(host='124.71.227.243',port=5432,user=user,password=password if password is not None else os.environ['PGPASSWORD'],database=db,timeout=10,server_settings={'statement_timeout':'20000','lock_timeout':'3000'})
async def probe(c,label,sql,expect=None,fetch=True):
 try:
  v=[dict(r) for r in await c.fetch(sql)] if fetch else await c.execute(sql)
  item={'id':label,'sql':safe(sql),'result':v,'sqlstate':'00000'}
 except asyncpg.PostgresError as e:item={'id':label,'sql':safe(sql),'error':str(e).splitlines()[0],'sqlstate':e.sqlstate}
 item['expected']=expect;events.append(item)
 P.joinpath('cloud-validation.json').write_text(json.dumps(events,ensure_ascii=False,default=str,indent=2))
 return item
async def setup(c,label,sql):
 x=await probe(c,label,sql,fetch=False)
 if x['sqlstate']!='00000':raise RuntimeError(label+' '+x['sqlstate'])
async def connprobe(user,db,label):
 try:
  c=await connect(user,db,passwords[user]); await c.close();events.append({'id':label,'sql':f'CONNECT database={db} user={user}','sqlstate':'00000'})
 except asyncpg.PostgresError as e:events.append({'id':label,'sql':f'CONNECT database={db} user={user}','sqlstate':e.sqlstate,'error':str(e).splitlines()[0]})
async def main():
 a=await connect(); conns=[]; created_roles=[];created_dbs=[];sup=None
 baseline=[dict(r) for r in await a.fetch("SELECT roleid,member,grantor,admin_option,inherit_option,set_option FROM pg_auth_members ORDER BY 1,2,3")]
 existing=await a.fetch("SELECT rolname FROM pg_roles WHERE rolname=ANY($1::text[])",roles)
 existingdb=await a.fetch("SELECT datname FROM pg_database WHERE datname=ANY($1::text[])",dbs)
 assert not existing and not existingdb,'Temporary names already exist; stop rather than adopt'
 try:
  for r in roles:
   await setup(a,'role-'+r,f"CREATE ROLE {r} LOGIN PASSWORD '{passwords[r]}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS")
   created_roles.append(r)
  await probe(a,'non-super-create-db-without-set',f'CREATE DATABASE {D} OWNER {S} TEMPLATE template0 ENCODING \'UTF8\'',expect='42501',fetch=False)
  # Do not retry/adopt if the provider allowed the preceding CREATE unexpectedly.
  if await a.fetchval('SELECT EXISTS(SELECT FROM pg_database WHERE datname=$1)',D):created_dbs.append(D)
  for r,db in [(S,D),(B,BD)]:
   await setup(a,'temporary-owner-membership-'+r,f'GRANT {r} TO root')
   if db not in created_dbs:
    await setup(a,'create-database-'+db,f"CREATE DATABASE {db} OWNER {r} TEMPLATE template0 ENCODING 'UTF8'");created_dbs.append(db)
   await setup(a,'database-acl-'+db,f'REVOKE ALL ON DATABASE {db} FROM PUBLIC; GRANT CONNECT,CREATE,TEMPORARY ON DATABASE {db} TO {r}')
   q=await connect(db=db);conns.append(q)
   await setup(q,'public-create-revoke-'+db,'REVOKE CREATE ON SCHEMA public FROM PUBLIC')
   if db==D:
    for ext in ['vector','pg_trgm','btree_gin']:await setup(q,'extension-'+ext,f'CREATE EXTENSION {ext} WITH SCHEMA public')
   await setup(a,'temporary-owner-membership-revoke-'+r,f'REVOKE {r} FROM root')
  service=await connect(S,D,passwords[S]);conns.append(service)
  biz=await connect(B,BD,passwords[B]);conns.append(biz)
  await probe(service,'service-flags',f"SELECT current_user,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user")
  await setup(service,'service-schema','CREATE SCHEMA meta_cx; CREATE SCHEMA bank_cx; CREATE TABLE meta_cx.users_cx(id int primary key, name text); INSERT INTO meta_cx.users_cx VALUES(1,\'protected\'); CREATE TABLE bank_cx.memories_cx(id int,body text); INSERT INTO bank_cx.memories_cx VALUES(1,\'memory\')')
  await probe(service,'vector-works',"SELECT '[1,2,3]'::public.vector AS vector")
  await probe(service,'hash-denied','SELECT rolname FROM pg_authid LIMIT 1',expect='42501')
  for label,sql in [('self-super',f'ALTER ROLE {S} SUPERUSER'),('self-bypass',f'ALTER ROLE {S} BYPASSRLS'),('create-role','CREATE ROLE denied_role_cx'),('create-db','CREATE DATABASE denied_db_cx'),('switch-root','SET ROLE root'),('change-biz-password',f"ALTER ROLE {B} PASSWORD 'Cx!ExampleNotUsed99'")]:
   await probe(service,label,sql,expect='42501',fetch=False)
  for user,db,label in [(B,D,'biz-cannot-connect-service'),(S,BD,'service-cannot-connect-biz')]:await connprobe(user,db,label)
  # Read-only probes of Supabase via restricted customer/service accounts.
  for r in [S,B]:
   try:
    q=await connect(r,'supabase_db',passwords[r]);conns.append(q)
    await probe(q,r+'-supabase-connect','SELECT current_user,current_database()')
    await probe(q,r+'-supabase-read','SELECT 1 FROM auth.users LIMIT 1',expect='42501')
   except asyncpg.PostgresError as e:events.append({'id':r+'-supabase-connect','sql':f'CONNECT supabase_db AS {r}','sqlstate':e.sqlstate})
  await setup(biz,'biz-own-schema','CREATE SCHEMA own_biz_cx;CREATE TABLE own_biz_cx.notes_cx(body text);INSERT INTO own_biz_cx.notes_cx VALUES(\'mine\')')
  await probe(biz,'biz-own-select','SELECT * FROM own_biz_cx.notes_cx')
  await probe(biz,'biz-public-create','CREATE TABLE public.customer_table_cx(id int)',expect='00000',fetch=False)
  # Customer SQL role coexisting inside service database.
  await setup(a,'customer-connect',f'GRANT CONNECT,TEMPORARY ON DATABASE {D} TO {C};GRANT {C} TO root;GRANT {S} TO root')
  dbroot=await connect(db=D);conns.append(dbroot)
  await setup(dbroot,'customer-own-schema',f'CREATE SCHEMA own_customer_cx AUTHORIZATION {C}')
  await setup(a,'customer-membership-revoke',f'REVOKE {C} FROM root;REVOKE {S} FROM root')
  for sch in ['meta_cx','bank_cx']:
   await service.execute("SELECT set_config('contextdb.boundary_owner',$1,false)",S);await service.execute("SELECT set_config('contextdb.boundary_customer',$1,false)",C);await service.execute("SELECT set_config('contextdb.boundary_schema',$1,false)",sch)
   await setup(service,'boundary-'+sch,(ROOT/'hindsight-extensions/contextdb-service/deployment/pg-role-boundary.sql').read_text())
  await setup(service,'future-table','CREATE TABLE bank_cx.future_cx(id int)')
  customer=await connect(C,D,passwords[C]);conns.append(customer)
  attacks=['SELECT * FROM meta_cx.users_cx',"UPDATE meta_cx.users_cx SET name='changed'",'SELECT * FROM bank_cx.memories_cx',"INSERT INTO bank_cx.memories_cx VALUES(2,'changed')",'TRUNCATE bank_cx.memories_cx','DROP TABLE bank_cx.memories_cx','CREATE TABLE bank_cx.inject_cx(id int)','DROP SCHEMA bank_cx CASCADE',f'SET ROLE {S}',f'GRANT {S} TO {C}','SELECT * FROM bank_cx.future_cx',f'ALTER ROLE {C} SUPERUSER']
  for n,sql in enumerate(attacks):await probe(customer,'customer-attack-'+str(n+1),sql,expect='42501',fetch=sql.startswith('SELECT'))
  await setup(customer,'customer-own-write',"CREATE TABLE own_customer_cx.notes_cx(body text);INSERT INTO own_customer_cx.notes_cx VALUES('mine')")
  await probe(customer,'customer-own-read','SELECT * FROM own_customer_cx.notes_cx')
  await probe(customer,'shared-vector-available',"SELECT '[1,2]'::public.vector")
  await probe(customer,'catalog-name-visible',"SELECT nspname FROM pg_namespace WHERE nspname='bank_cx'")
  # Document §7 SQL semantics: existing tables vs future defaults and search_path.
  await setup(dbroot,'doc-default-setup',f'CREATE SCHEMA doc_ext_cx;CREATE SCHEMA doc_data_cx;CREATE TABLE doc_data_cx.before_cx(id int);GRANT USAGE ON SCHEMA doc_data_cx TO {C};ALTER DEFAULT PRIVILEGES IN SCHEMA doc_data_cx GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO {C};CREATE TABLE doc_data_cx.after_cx(id int)')
  await probe(customer,'defaults-existing-table','SELECT * FROM doc_data_cx.before_cx',expect='42501')
  await probe(customer,'defaults-future-table','SELECT * FROM doc_data_cx.after_cx',expect='00000')
  await probe(customer,'schema-usage-not-create','CREATE TABLE doc_data_cx.no_create_cx(id int)',expect='42501',fetch=False)
  await setup(dbroot,'pgtrgm-schema-demo','DROP EXTENSION pg_trgm; SET search_path=doc_ext_cx,public; CREATE EXTENSION pg_trgm')
  await probe(dbroot,'unqualified-extension-schema',"SELECT extname,nspname FROM pg_extension JOIN pg_namespace ON extnamespace=pg_namespace.oid WHERE extname='pg_trgm'")
  await setup(dbroot,'restore-trgm-to-public','DROP EXTENSION pg_trgm;CREATE EXTENSION pg_trgm WITH SCHEMA public;RESET search_path')
  # Service owner can address all its schemas irrespective of search_path.
  await setup(service,'schema-routing-not-acl','SET search_path=meta_cx,public')
  await probe(service,'owner-cross-schema','SELECT * FROM bank_cx.memories_cx')
  await probe(a,'root-after-revoke-membership',f"SELECT r.rolname,a.admin_option,a.inherit_option,a.set_option FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.roleid WHERE a.member=(SELECT oid FROM pg_roles WHERE rolname='root') AND r.rolname=ANY(ARRAY['{S}','{B}','{C}'])")
  await probe(dbroot,'root-after-revoke-table-access','SELECT * FROM meta_cx.users_cx')
  # User authorized fresh synthetic tables inside Supabase DB; no existing objects changed.
  sup=await connect(db='supabase_db')
  await setup(sup,'supabase-test-schema',f'CREATE SCHEMA {SC};CREATE TABLE {SC}.rows_cx(tenant_id text,body text);INSERT INTO {SC}.rows_cx VALUES(\'alice\',\'alpha\'),(\'bob\',\'beta\');GRANT USAGE ON SCHEMA {SC} TO anon,authenticated,service_role;GRANT SELECT,INSERT,DELETE ON {SC}.rows_cx TO anon,authenticated,service_role;ALTER TABLE {SC}.rows_cx ENABLE ROW LEVEL SECURITY;ALTER TABLE {SC}.rows_cx FORCE ROW LEVEL SECURITY;CREATE POLICY mine_cx ON {SC}.rows_cx TO authenticated USING (tenant_id=current_setting(\'request.jwt.claim.sub\',true)) WITH CHECK (tenant_id=current_setting(\'request.jwt.claim.sub\',true))')
  for r,claim in [('anon','alice'),('authenticated','alice'),('authenticated','bob'),('service_role','alice')]:
   tr=sup.transaction();await tr.start()
   try:
    await sup.execute(f'SET LOCAL ROLE {r}')
    await sup.execute("SELECT set_config('request.jwt.claim.sub',$1,true)",claim)
    await probe(sup,'rls-'+r+'-'+claim,f'SELECT current_user,tenant_id,body FROM {SC}.rows_cx ORDER BY tenant_id')
    if r=='authenticated' and claim=='alice':
     await probe(sup,'rls-cross-tenant-write',f"INSERT INTO {SC}.rows_cx VALUES('bob','blocked')",expect='42501',fetch=False)
   finally:await tr.rollback()
  await probe(sup,'rls-root-owner-force',f'SELECT * FROM {SC}.rows_cx')
  await setup(sup,'rls-root-can-disable',f'ALTER TABLE {SC}.rows_cx DISABLE ROW LEVEL SECURITY')
  await probe(sup,'rls-root-after-disable',f'SELECT * FROM {SC}.rows_cx')
  # Password rotation test only changes a disposable role.
  new='Cx!9Az'+secrets.token_hex(10)
  await setup(service,'own-password-rotation',f"ALTER ROLE {S} PASSWORD '{new}'")
  try:
   old=await connect(S,D,passwords[S]);await old.close();events.append({'id':'old-password-reconnect','sql':'CONNECT with old generated password','sqlstate':'00000'})
  except asyncpg.PostgresError as e:events.append({'id':'old-password-reconnect','sql':'CONNECT with old generated password','sqlstate':e.sqlstate})
  passwords[S]=new;q=await connect(S,D,new);await q.close();events.append({'id':'new-password-reconnect','sql':'CONNECT with new generated password','sqlstate':'00000'})
 finally:
  if sup:
   await setup(sup,'cleanup-supabase-schema',f'DROP SCHEMA IF EXISTS {SC} CASCADE');await sup.close()
  for q in conns:
   if not q.is_closed():await q.close()
  for r,db in [(S,D),(B,BD)]:
   if db in created_dbs:
    await setup(a,'cleanup-membership-'+r,f'GRANT {r} TO root')
    await setup(a,'cleanup-db-'+db,f'DROP DATABASE {db} WITH (FORCE)')
  for r in reversed(created_roles):await setup(a,'cleanup-role-'+r,f'DROP ROLE {r}')
  final=[dict(r) for r in await a.fetch("SELECT roleid,member,grantor,admin_option,inherit_option,set_option FROM pg_auth_members ORDER BY 1,2,3")]
  cleanup={'databases':[r['datname'] for r in await a.fetch('SELECT datname FROM pg_database WHERE datname=ANY($1::text[])',dbs)],'roles':[r['rolname'] for r in await a.fetch('SELECT rolname FROM pg_roles WHERE rolname=ANY($1::text[])',roles)],'membership_restored':baseline==final}
  q=await connect(db='supabase_db');cleanup['supabase_schema_count']=await q.fetchval('SELECT count(*) FROM pg_namespace WHERE nspname=$1',SC);await q.close()
  P.joinpath('cloud-cleanup.json').write_text(json.dumps(cleanup,indent=2));await a.close()
  P.joinpath('cloud-validation.json').write_text(json.dumps(events,ensure_ascii=False,default=str,indent=2))
  print('cleanup',cleanup,flush=True)
  assert cleanup=={'databases':[],'roles':[],'membership_restored':True,'supabase_schema_count':0},'Residual objects or changed memberships'
 print('cases',len(events));print(json.dumps([x for x in events if x['id'].startswith(('rls-','root-after','unqualified','defaults','biz-public'))],ensure_ascii=False,default=str,indent=2))
asyncio.run(main())
