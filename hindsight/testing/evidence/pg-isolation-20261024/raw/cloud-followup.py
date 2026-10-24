from pathlib import Path
ns={};exec(Path(__file__).with_name('cloud-validation.py').read_text().split('asyncio.run(main())')[0].replace("P.joinpath('cloud-validation.json')", "P.joinpath('cloud-followup-live.json')"),ns)
globals().update(ns)
import ast
S='follow_service_20261024_cx';C='follow_customer_20261024_cx';D='follow_db_20261024_cx';roles=[S,C];dbs=[D];passwords={r:'Cx!9aZ'+secrets.token_hex(10) for r in roles};events=[]
ns['events']=events
async def follow():
 a=await connect();conns=[];made=[];dbmade=False
 baseline=[dict(r) for r in await a.fetch('SELECT * FROM pg_auth_members ORDER BY roleid,member,grantor')]
 assert not await a.fetchval('SELECT EXISTS(SELECT FROM pg_database WHERE datname=$1)',D)
 try:
  for r in roles:
   await setup(a,'role-'+r,f"CREATE ROLE {r} LOGIN PASSWORD '{passwords[r]}' NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS");made.append(r)
  await probe(a,'root-auto-membership-before-explicit-grant',f"SELECT r.rolname,m.admin_option,m.inherit_option,m.set_option FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid WHERE m.member=(SELECT oid FROM pg_roles WHERE rolname='root') AND r.rolname IN ('{S}','{C}')")
  await setup(a,'grant-temporary',f'GRANT {S} TO root;GRANT {C} TO root')
  await setup(a,'create-db',f'CREATE DATABASE {D} OWNER {S} TEMPLATE template0');dbmade=True
  await setup(a,'restrict-db',f'REVOKE ALL ON DATABASE {D} FROM PUBLIC;GRANT CONNECT ON DATABASE {D} TO {C}')
  q=await connect(db=D);conns.append(q)
  await setup(q,'customer-schema',f'CREATE SCHEMA own_customer_cx AUTHORIZATION {C};REVOKE CREATE ON SCHEMA public FROM PUBLIC')
  s=await connect(S,D,passwords[S]);conns.append(s)
  await setup(s,'representative-objects',"CREATE SCHEMA meta_cx;CREATE SCHEMA bank_cx;CREATE TABLE meta_cx.users(id int primary key,name text);INSERT INTO meta_cx.users VALUES(1,'protected');CREATE TABLE bank_cx.banks(id int primary key,content text);INSERT INTO bank_cx.banks VALUES(1,'memory');CREATE SEQUENCE bank_cx.seq;CREATE TABLE bank_cx.future(id int);CREATE TYPE bank_cx.future_type AS ENUM('protected');CREATE FUNCTION bank_cx.future_fn() RETURNS text LANGUAGE sql AS $$SELECT 'protected'$$")
  for sch in ['meta_cx','bank_cx']:
   await s.execute("SELECT set_config('contextdb.boundary_owner',$1,false)",S);await s.execute("SELECT set_config('contextdb.boundary_customer',$1,false)",C);await s.execute("SELECT set_config('contextdb.boundary_schema',$1,false)",sch)
   await setup(s,'boundary-'+sch,(ROOT/'hindsight-extensions/contextdb-service/deployment/pg-role-boundary.sql').read_text())
  await setup(a,'revoke-temporary',f'REVOKE {S} FROM root;REVOKE {C} FROM root')
  await q.close()
  q=await connect(db=D);conns.append(q)
  await probe(q,'root-fresh-connect','SELECT session_user,current_user,current_database()')
  await probe(q,'root-fresh-no-membership',f"SELECT r.rolname,m.admin_option,m.inherit_option,m.set_option FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid WHERE m.member=(SELECT oid FROM pg_roles WHERE rolname='root') AND r.rolname IN ('{S}','{C}')")
  await probe(q,'root-fresh-read-service-owned','SELECT * FROM meta_cx.users')
  await setup(s,'force-rls-owner-service',"ALTER TABLE meta_cx.users ENABLE ROW LEVEL SECURITY;ALTER TABLE meta_cx.users FORCE ROW LEVEL SECURITY;CREATE POLICY nobody_cx ON meta_cx.users USING(false) WITH CHECK(false)")
  await probe(s,'service-owner-force-rls','SELECT * FROM meta_cx.users')
  await probe(q,'root-fresh-force-rls','SELECT * FROM meta_cx.users')
  c=await connect(C,D,passwords[C]);conns.append(c)
  tree=ast.parse((ROOT/'hindsight-extensions/contextdb-service/tests/python/test_customer_pg_boundary.py').read_text())
  fn=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='test_customer_denied')
  statement_list=ast.literal_eval(fn.decorator_list[0].args[1])
  for n,statement in enumerate(statement_list):
   sql=statement.format(metadata_schema='meta_cx',bank_schema='bank_cx',owner_name=S,customer_name=C)
   await probe(c,f'full-attack-{n+1:02}',sql,expect='42501',fetch=sql.startswith('SELECT'))
  print('full attack cases',len(statement_list),flush=True)
  await probe(c,'own-schema-still-works',"CREATE TABLE own_customer_cx.notes_cx(body text);INSERT INTO own_customer_cx.notes_cx VALUES('mine')",fetch=False)
 finally:
  for q in conns:
   if not q.is_closed():await q.close()
  if dbmade:
   await setup(a,'cleanup-grant',f'GRANT {S} TO root');await setup(a,'cleanup-db',f'DROP DATABASE {D} WITH(FORCE)')
  for r in reversed(made):await setup(a,'cleanup-'+r,f'DROP ROLE {r}')
  final=[dict(r) for r in await a.fetch('SELECT * FROM pg_auth_members ORDER BY roleid,member,grantor')]
  cleanup={'databases':await a.fetchval('SELECT count(*) FROM pg_database WHERE datname=ANY($1::text[])',dbs),'roles':await a.fetchval('SELECT count(*) FROM pg_roles WHERE rolname=ANY($1::text[])',roles),'membership_restored':baseline==final}
  (P/'cloud-followup-cleanup.json').write_text(json.dumps(cleanup,indent=2));(P/'cloud-followup.json').write_text(json.dumps(events,default=str,indent=2,ensure_ascii=False));await a.close();print(cleanup,flush=True)
  assert cleanup=={'databases':0,'roles':0,'membership_restored':True}
 print(json.dumps([x for x in events if x['id'].startswith(('root-','service-owner'))],indent=2,ensure_ascii=False,default=str))
asyncio.run(follow())
