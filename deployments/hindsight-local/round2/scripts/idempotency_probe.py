#!/usr/bin/env python3
"""Native async retain replay and a proposed PG request-ledger contract probe."""
import asyncio, hashlib, json, time, uuid
from pathlib import Path
import asyncpg, httpx
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'round2/evidence/idempotency-probe.json'
records=[]
def check(name,ok,**detail):
    records.append(dict(name=name,passed=bool(ok),**detail)); OUT.write_text(json.dumps(records,indent=2,ensure_ascii=False)); assert ok,name
async def main():
    keys=json.loads((ROOT/'.secrets/cell-b-keys.json').read_text())
    headers={'Authorization':'Bearer '+keys['team_a']}
    bank='round2-replay-'+uuid.uuid4().hex[:10]
    op=str(uuid.uuid4()); base='/v1/default/banks/'+bank
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8890',headers=headers,trust_env=False,timeout=60) as c:
        for b in [bank,bank+'-other']:
            r=await c.put('/v1/default/banks/'+b,json={'retain_extraction_mode':'chunks','enable_observations':False})
            check('create-'+b,r.status_code==200,status=r.status_code)
        payload={'async':True,'operation_id':op,'items':[{'document_id':'replay-doc','content':'Synthetic fixed original value ALPHA-901.'}]}
        rs=await asyncio.gather(*(c.post(base+'/memories',json=payload) for _ in range(8)))
        check('eight-concurrent-replays-same-operation',all(r.status_code==200 and r.json().get('operation_id')==op for r in rs),statuses=[r.status_code for r in rs])
        changed={**payload,'items':[{'document_id':'changed-doc','content':'Synthetic changed value BETA-902.'}]}
        r=await c.post(base+'/memories',json=changed)
        check('native-same-id-changed-payload-replays-not-conflicts',r.status_code==200 and r.json().get('operation_id')==op,status=r.status_code)
        r=await c.post('/v1/default/banks/'+bank+'-other/memories',json=payload)
        check('native-same-operation-other-bank-conflicts',r.status_code==409,status=r.status_code)
        for _ in range(120):
            r=await c.get(base+'/operations/'+op)
            if r.status_code==200 and r.json().get('status') in ['completed','failed']: break
            await asyncio.sleep(.25)
        check('async-task-completed',r.status_code==200 and r.json().get('status')=='completed',response=r.json())
        r=await c.get(base+'/documents/changed-doc')
        check('changed-payload-not-ingested',r.status_code==404,status=r.status_code)
        r=await c.get(base+'/documents/replay-doc')
        check('original-payload-present',r.status_code==200 and 'ALPHA-901' in r.text,status=r.status_code)
    pool=await asyncpg.create_pool('postgresql://hindsight:hindsight@127.0.0.1:55433/contextdb_round2_control',min_size=1,max_size=8)
    await pool.execute('''CREATE TABLE IF NOT EXISTS request_ledger (
        workspace_id text NOT NULL, bank_id text NOT NULL, action text NOT NULL,
        idem_key text NOT NULL, payload_sha256 text NOT NULL,
        operation_id uuid NOT NULL, state text NOT NULL,
        PRIMARY KEY(workspace_id,bank_id,action,idem_key));''')
    def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    async def reserve(obj):
        candidate=uuid.uuid4()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("INSERT INTO request_ledger VALUES($1,$2,'retain','client-key',$3,$4,'prepared') ON CONFLICT DO NOTHING",bank,bank,digest(obj),candidate)
                row=await conn.fetchrow("SELECT * FROM request_ledger WHERE workspace_id=$1 AND bank_id=$1 AND action='retain' AND idem_key='client-key'",bank)
                return (409,None) if row['payload_sha256']!=digest(obj) else (200,str(row['operation_id']))
    results=await asyncio.gather(*(reserve(payload) for _ in range(8)))
    check('proposed-ledger-concurrent-one-operation',all(r[0]==200 for r in results) and len({r[1] for r in results})==1)
    r=await reserve(changed)
    check('proposed-ledger-rejects-changed-payload',r[0]==409,status=r[0])
    check('proposed-ledger-one-row',await pool.fetchval('SELECT count(*) FROM request_ledger WHERE workspace_id=$1',bank)==1)
    await pool.close()
    print(f'PASS {len(records)} checks. Native replay does not compare body; product ledger is a local design probe only.')
asyncio.run(main())
