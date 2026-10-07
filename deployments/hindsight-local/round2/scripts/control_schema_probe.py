import asyncio,json,time,uuid
from pathlib import Path
import asyncpg
base=Path(__file__).resolve().parents[1]
async def main():
    c=await asyncpg.connect('postgresql://hindsight:hindsight@127.0.0.1:55433/contextdb_round2_control')
    schema='round2_design_'+str(int(time.time()));rows=[]
    await c.execute(f'CREATE SCHEMA {schema}');await c.execute(f'SET search_path TO {schema}')
    await c.execute((base/'scripts/control_schema_reference.sql').read_text())
    async def reject(label,sql,expected):
        try:
            async with c.transaction(): await c.execute(sql)
        except expected as exc: rows.append({'check':label,'result':'pass','sqlstate':exc.sqlstate})
        else: raise AssertionError(label+' unexpectedly accepted')
    def ok(label): rows.append({'check':label,'result':'pass'})
    await c.execute("INSERT INTO model_profiles VALUES('p',1,'synthetic-llm','synthetic-e',384,'rrf','hash'); INSERT INTO cells VALUES('c','r','p','http://internal.invalid','READY','f7dd3f4fd','sha256:synthetic','head'); INSERT INTO workspaces VALUES('a','project-a','r','READY',1),('b','project-b','r','READY',1); INSERT INTO memberships VALUES('a','alice','owner','ACTIVE'),('b','bob','owner','ACTIVE'); INSERT INTO banks VALUES('ka','a','same','same','kb','alice','READY',1),('kb','b','same','same','kb','bob','READY',1)")
    ok('same-public-bank-name-in-different-workspaces')
    await reject('cross-workspace-bank-grant',"INSERT INTO bank_grants VALUES('a','kb','alice',ARRAY['read'])",asyncpg.ForeignKeyViolationError)
    await reject('cross-workspace-subject-grant',"INSERT INTO bank_grants VALUES('a','ka','bob',ARRAY['read'])",asyncpg.ForeignKeyViolationError)
    await c.execute("INSERT INTO placements VALUES('a','c','tenant_a',1,'READY')")
    await reject('one-placement-per-workspace',"INSERT INTO placements VALUES('a','c','tenant_other',2,'READY')",asyncpg.UniqueViolationError)
    await reject('one-workspace-per-cell-schema',"INSERT INTO placements VALUES('b','c','tenant_a',1,'READY')",asyncpg.UniqueViolationError)
    await c.execute("INSERT INTO api_keys(key_id,digest,pepper_version,workspace_id,subject_id,scopes,bank_constraints,expires_at) VALUES('k',decode(repeat('01',32),'hex'),1,'a','alice',ARRAY['read'],'{\"bank_ids\":[\"ka\"]}',now()+interval '1 day')")
    r=await c.fetchrow('SELECT pepper_version,scopes,bank_constraints,expires_at>created_at AS expiry_valid FROM api_keys WHERE key_id=\'k\'')
    assert r['pepper_version']==1 and r['scopes']==['read'] and r['expiry_valid'];ok('key-scope-pepper-expiry-roundtrip')
    await reject('invalid-key-expiry',"UPDATE api_keys SET expires_at=created_at-interval '1 second' WHERE key_id='k'",asyncpg.CheckViolationError)
    await reject('empty-key-scopes',"UPDATE api_keys SET scopes=ARRAY[]::text[] WHERE key_id='k'",asyncpg.CheckViolationError)
    await reject('invalid-pepper-version',"UPDATE api_keys SET pepper_version=0 WHERE key_id='k'",asyncpg.CheckViolationError)
    await c.execute("INSERT INTO request_ledger VALUES('a','ka','retain','idem','hash',$1,'PREPARED','alice','k',now())",uuid.uuid4())
    await reject('request-idempotency-unique',"INSERT INTO request_ledger VALUES('a','ka','retain','idem','other','00000000-0000-0000-0000-000000000001','PREPARED','alice','k',now())",asyncpg.UniqueViolationError)
    await reject('request-cross-workspace-bank',"INSERT INTO request_ledger VALUES('a','kb','retain','idem','hash','00000000-0000-0000-0000-000000000002','PREPARED','alice','k',now())",asyncpg.ForeignKeyViolationError)
    await reject('ledger-cross-workspace-subject',"INSERT INTO request_ledger VALUES('a','ka','retain','bad-subject','hash','00000000-0000-0000-0000-000000000003','PREPARED','bob','k',now())",asyncpg.ForeignKeyViolationError)
    await c.execute("INSERT INTO api_keys(key_id,digest,pepper_version,workspace_id,subject_id,scopes,expires_at) VALUES('other-key',decode(repeat('02',32),'hex'),1,'b','bob',ARRAY['read'],now()+interval '1 day')")
    await reject('ledger-cross-workspace-key',"INSERT INTO request_ledger VALUES('a','ka','retain','bad-key','hash','00000000-0000-0000-0000-000000000004','PREPARED','alice','other-key',now())",asyncpg.ForeignKeyViolationError)
    await reject('referenced-key-delete-restricted',"DELETE FROM api_keys WHERE key_id='k'",asyncpg.ForeignKeyViolationError)
    await c.execute("UPDATE api_keys SET revoked_at=now() WHERE key_id='k'")
    assert await c.fetchval("SELECT count(*) FROM request_ledger l JOIN api_keys k ON l.key_id=k.key_id WHERE k.revoked_at IS NOT NULL")==1
    ok('revoked-key-tombstone-preserves-ledger-identity')
    await c.execute("INSERT INTO source_revisions VALUES('a','s',1,'hash','immutable:synthetic','alice','APPROVED')")
    await reject('source-revision-unique',"INSERT INTO source_revisions VALUES('a','s',1,'new','immutable:new','alice','APPROVED')",asyncpg.UniqueViolationError)
    try:
        async with c.transaction():
            await c.execute("UPDATE banks SET state='PUBLISHING',content_epoch=content_epoch+1 WHERE id='ka'; INSERT INTO jobs(job_id,workspace_id,kind,resource_id,phase) VALUES('rollback','a','publish','ka','QUEUED')")
            raise RuntimeError('synthetic precommit failure')
    except RuntimeError: pass
    assert await c.fetchval("SELECT state FROM banks WHERE id='ka'")=='READY'
    assert await c.fetchval("SELECT count(*) FROM jobs WHERE job_id='rollback'")==0;ok('publication-state-and-job-rollback-atomic')
    async with c.transaction():
        await c.execute("UPDATE banks SET state='PUBLISHING',content_epoch=content_epoch+1 WHERE id='ka'; INSERT INTO jobs(job_id,workspace_id,kind,resource_id,phase) VALUES('j','a','publish','ka','QUEUED'); INSERT INTO publications VALUES('pub','a','ka','s',1,'alice','doc','PUBLISHING','j')")
    assert await c.fetchval("SELECT state FROM banks WHERE id='ka'")=='PUBLISHING' and await c.fetchval("SELECT count(*) FROM publications WHERE job_id='j'")==1;ok('publication-state-job-reference-commit')
    await reject('publication-cross-workspace-source',"INSERT INTO publications VALUES('bad','b','kb','s',1,'bob','doc','PUBLISHING','j')",asyncpg.ForeignKeyViolationError)
    await reject('embedding-dimension-positive',"UPDATE model_profiles SET embedding_dimension=0 WHERE id='p'",asyncpg.CheckViolationError)
    r=await c.fetchrow('SELECT upstream_sha,image_digest,schema_version FROM cells');assert all(r.values());ok('cell-artifact-version-fields')
    fsync=await c.fetchval('SHOW fsync');await c.close()
    result={'exit_code':0,'schema':schema,'database':'contextdb_round2_control','checks':len(rows),'results':rows,'fsync':fsync,'scope':'reference DDL/constraints/transaction logic; not production migration or power-loss durability; fixtures retained for review'}
    (base/'evidence/control-schema-results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
asyncio.run(main())
