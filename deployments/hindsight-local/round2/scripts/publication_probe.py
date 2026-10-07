#!/usr/bin/env python3
"""Executable PG contract for gated publication; no claim of full cloud integration."""
import asyncio,json,uuid
from pathlib import Path
import asyncpg
ROOT=Path(__file__).resolve().parents[2]; out=ROOT/'round2/evidence/publication-probe.json'; checks=[]
def check(n,ok,**v):
    checks.append({'name':n,'passed':bool(ok),**v});out.write_text(json.dumps(checks,ensure_ascii=False,indent=2));assert ok,n
async def main():
    p=await asyncpg.create_pool('postgresql://hindsight:hindsight@127.0.0.1:55433/contextdb_round2_control',min_size=1,max_size=5)
    await p.execute('''CREATE TABLE IF NOT EXISTS kb_resources (
        kb_id text PRIMARY KEY, state text NOT NULL, epoch bigint NOT NULL,
        active_revision text, pending_revision text);
        CREATE TABLE IF NOT EXISTS kb_jobs (
        job_id uuid PRIMARY KEY, kb_id text NOT NULL REFERENCES kb_resources,
        kind text NOT NULL, state text NOT NULL, revision text NOT NULL);''')
    k='round2-'+uuid.uuid4().hex[:10]
    await p.execute("INSERT INTO kb_resources VALUES($1,'ready',1,'v1',null)",k)
    async def read_ticket():
        r=await p.fetchrow('SELECT * FROM kb_resources WHERE kb_id=$1',k)
        return r['epoch'] if r['state']=='ready' else None
    async def finish_read(ticket):
        r=await p.fetchrow('SELECT * FROM kb_resources WHERE kb_id=$1',k)
        return ticket is not None and r['state']=='ready' and r['epoch']==ticket
    ticket=await read_ticket();check('ready-read-authorized',await finish_read(ticket))
    async def begin_publish(rev):
        async with p.acquire() as c:
            async with c.transaction():
                r=await c.fetchrow("UPDATE kb_resources SET state='publishing',epoch=epoch+1,pending_revision=$2 WHERE kb_id=$1 AND state='ready' RETURNING epoch",k,rev)
                if not r:return False
                await c.execute("INSERT INTO kb_jobs VALUES($1,$2,'publish','pending',$3)",uuid.uuid4(),k,rev)
                return True
    results=await asyncio.gather(begin_publish('v2'),begin_publish('v3'))
    check('concurrent-publish-only-one-winner',sum(results)==1)
    check('exactly-one-durable-job',await p.fetchval('SELECT count(*) FROM kb_jobs WHERE kb_id=$1',k)==1)
    check('publishing-blocks-new-read',await read_ticket() is None)
    check('publishing-invalidates-inflight-read',not await finish_read(ticket))
    # Coordinator restart: close/reopen pool; durable gate and job remain.
    await p.close();p=await asyncpg.create_pool('postgresql://hindsight:hindsight@127.0.0.1:55433/contextdb_round2_control',min_size=1,max_size=5)
    check('restart-keeps-query-gate-closed',await read_ticket() is None)
    check('restart-keeps-pending-job',await p.fetchval("SELECT count(*) FROM kb_jobs WHERE kb_id=$1 AND state='pending'",k)==1)
    # Failure must not reopen a partially modified KB. Recovery remains explicit.
    await p.execute("UPDATE kb_resources SET state='failed_closed' WHERE kb_id=$1",k)
    check('failed-publication-remains-closed',await read_ticket() is None)
    # Simulate audited retry after upstream indexing confirmation; one local commit.
    async with p.acquire() as c:
        async with c.transaction():
            await c.execute("UPDATE kb_jobs SET state='completed' WHERE kb_id=$1",k)
            await c.execute("UPDATE kb_resources SET state='ready',active_revision=pending_revision,pending_revision=null,epoch=epoch+1 WHERE kb_id=$1",k)
    check('verified-publication-reopens',await finish_read(await read_ticket()))
    check('old-ticket-never-becomes-valid-again',not await finish_read(ticket))
    # Reject/retract bumps epoch before background deletion.
    old=await read_ticket();await p.execute("UPDATE kb_resources SET state='deleting',epoch=epoch+1 WHERE kb_id=$1",k)
    check('retract-blocks-new-read',await read_ticket() is None)
    check('retract-blocks-inflight-result',not await finish_read(old))
    # A transaction crash must leave neither gate change nor orphan job.
    k2=k+'-rollback';await p.execute("INSERT INTO kb_resources VALUES($1,'ready',1,'v1',null)",k2)
    try:
        async with p.acquire() as c:
            async with c.transaction():
                await c.execute("UPDATE kb_resources SET state='publishing' WHERE kb_id=$1",k2)
                await c.execute("INSERT INTO kb_jobs VALUES($1,$2,'publish','pending','v2')",uuid.uuid4(),k2)
                raise RuntimeError('synthetic crash before commit')
    except RuntimeError:pass
    check('rollback-restores-resource-state',await p.fetchval('SELECT state FROM kb_resources WHERE kb_id=$1',k2)=='ready')
    check('rollback-leaves-no-job',await p.fetchval('SELECT count(*) FROM kb_jobs WHERE kb_id=$1',k2)==0)
    await p.close();print(f'PASS {len(checks)} PG contract checks; indexing confirmation is simulated, not a deployed publication service.')
asyncio.run(main())
