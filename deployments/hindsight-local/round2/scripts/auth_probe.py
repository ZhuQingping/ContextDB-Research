#!/usr/bin/env python3
"""Local design probe, NOT a production gateway. Synthetic keys stay in memory.
Exercises opaque-key lifecycle and bank ACL against real PG and Hindsight Cell B.
"""
import asyncio, hashlib, hmac, json, secrets, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import asyncpg
from aiohttp import ClientSession, web
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'round2/evidence/auth-probe.json'
DSN = 'postgresql://hindsight:hindsight@127.0.0.1:55433/'
records=[]

def check(name, ok, **detail):
    records.append(dict(name=name,passed=bool(ok),**detail))
    OUT.write_text(json.dumps(records,ensure_ascii=False,indent=2))
    assert ok, name

async def main():
    admin=await asyncpg.connect(DSN+'hindsight')
    if not await admin.fetchval("SELECT 1 FROM pg_database WHERE datname='contextdb_round2_control'"):
        await admin.execute('CREATE DATABASE contextdb_round2_control')
    await admin.close()
    pool=await asyncpg.create_pool(DSN+'contextdb_round2_control',min_size=1,max_size=4)
    await pool.execute('''CREATE TABLE IF NOT EXISTS api_keys (
        key_id text PRIMARY KEY, secret_digest bytea NOT NULL,
        workspace_id text NOT NULL, subject_id text NOT NULL,
        expires_at timestamptz NOT NULL, revoked boolean NOT NULL DEFAULT false);
        CREATE TABLE IF NOT EXISTS bank_grants (
        workspace_id text NOT NULL, subject_id text NOT NULL, bank_id text NOT NULL,
        actions text[] NOT NULL, PRIMARY KEY(workspace_id,subject_id,bank_id));''')
    # Each probe run has fresh IDs; no existing key or grant is overwritten.
    run=uuid.uuid4().hex[:10]; pepper=secrets.token_bytes(32)
    upstream_keys=json.loads((ROOT/'.secrets/cell-b-keys.json').read_text())
    routes={f'{run}-a':'team_a',f'{run}-b':'team_b'}
    private=f'round2-private-{run}'; shared=f'round2-shared-{run}'
    async def issue(ws,subject,expired=False):
        kid=uuid.uuid4().hex
        token=f'ctx_{kid}_{secrets.token_urlsafe(32)}'
        digest=hmac.digest(pepper,token.encode(),'sha256')
        await pool.execute('INSERT INTO api_keys VALUES($1,$2,$3,$4,$5,false)',kid,digest,ws,subject,
            datetime.now(timezone.utc)+timedelta(days=-1 if expired else 7))
        return kid,token
    async def grant(ws,subject,bank,actions):
        await pool.execute('INSERT INTO bank_grants VALUES($1,$2,$3,$4)',ws,subject,bank,actions)
    async with ClientSession(trust_env=False) as session:
        # Prepare native banks without an LLM, only local real embeddings.
        for ws,who in routes.items():
            hdr={'Authorization':'Bearer '+upstream_keys[who]}
            for bank in [private,shared]:
                async with session.put(f'http://127.0.0.1:8890/v1/default/banks/{bank}',headers=hdr,json={
                    'retain_extraction_mode':'chunks','enable_observations':False}) as r:
                    check(f'prepare-{who}-{bank}',r.status==200,status=r.status)
            async with session.post(f'http://127.0.0.1:8890/v1/default/banks/{shared}/memories',headers=hdr,json={
                'items':[{'document_id':'canary','content':f'Synthetic ownership marker {run} {who}.'}]}) as r:
                check(f'prepare-canary-{who}',r.status==200,status=r.status)
        wa,wb=routes
        kid,token=await issue(wa,'alice'); _,reader=await issue(wa,'bob')
        _,other=await issue(wb,'alice'); _,expired=await issue(wa,'alice',True)
        await grant(wa,'alice',private,['read','write'])
        await grant(wa,'alice',shared,['read','write'])
        await grant(wa,'bob',shared,['read'])
        await grant(wb,'alice',shared,['read'])
        # Narrow exact method/path allowlist. No arbitrary upstream admin/config proxy.
        async def handler(request):
            auth=request.headers.get('Authorization','')
            if not auth.startswith('Bearer '): return web.json_response({'error':'unauthorized'},status=401)
            presented=auth[7:]; parts=presented.split('_',2)
            if len(parts)!=3 or parts[0]!='ctx': return web.json_response({'error':'unauthorized'},status=401)
            row=await pool.fetchrow('SELECT * FROM api_keys WHERE key_id=$1',parts[1])
            if not row or row['revoked'] or row['expires_at']<=datetime.now(timezone.utc) or not hmac.compare_digest(
                row['secret_digest'],hmac.digest(pepper,presented.encode(),'sha256')):
                return web.json_response({'error':'unauthorized'},status=401)
            bank=request.match_info['bank']; suffix=request.match_info['tail']
            action={('GET','memories/list'):'read',('POST','memories'):'write',('POST','memories/recall'):'read'}.get((request.method,suffix))
            if not action: return web.json_response({'error':'not_exposed'},status=403)
            actions=await pool.fetchval('SELECT actions FROM bank_grants WHERE workspace_id=$1 AND subject_id=$2 AND bank_id=$3',
                row['workspace_id'],row['subject_id'],bank)
            if not actions or action not in actions: return web.json_response({'error':'forbidden'},status=403)
            # Explicit server-owned route: no client tenant/header/query routing.
            who=routes[row['workspace_id']]
            async with session.request(request.method,f'http://127.0.0.1:8890/v1/default/banks/{bank}/{suffix}',
                data=await request.read(),headers={'Authorization':'Bearer '+upstream_keys[who],
                'Content-Type':'application/json'}) as upstream:
                data=await upstream.read()
                return web.Response(body=data,status=upstream.status,content_type='application/json')
        app=web.Application(client_max_size=1024*1024)
        app.router.add_route('*','/v1/default/banks/{bank}/{tail:.*}',handler)
        runner=web.AppRunner(app,access_log=None); await runner.setup()
        site=web.TCPSite(runner,'127.0.0.1',0); await site.start()
        port=site._server.sockets[0].getsockname()[1]
        async def probe(name,key,bank=shared,method='GET',tail='memories/list',expected=200,body=None,extra=None):
            headers={'Authorization':'Bearer '+key} if key else {}
            headers.update(extra or {})
            async with session.request(method,f'http://127.0.0.1:{port}/v1/default/banks/{bank}/{tail}',headers=headers,json=body) as r:
                data=await r.json()
                check(name,r.status==expected,status=r.status,expected=expected)
                return data
        try:
            await probe('missing-key',None,expected=401)
            await probe('unknown-key','ctx_unknown_invalid',expected=401)
            await probe('tampered-secret',token+'x',expected=401)
            await probe('expired-key',expired,expected=401)
            a=await probe('valid-owner',token)
            check('owner-gets-only-team-a','team_a' in json.dumps(a) and 'team_b' not in json.dumps(a))
            b=await probe('same-bank-name-other-workspace',other)
            check('other-workspace-gets-only-team-b','team_b' in json.dumps(b) and 'team_a' not in json.dumps(b))
            spoof=await probe('spoof-tenant-header-ignored',token,extra={'X-Tenant-Id':wb,'X-Schema':'public'})
            check('spoof-does-not-change-route','team_a' in json.dumps(spoof) and 'team_b' not in json.dumps(spoof))
            await probe('team-reader-can-read-shared',reader)
            await probe('team-reader-denied-private-bank',reader,bank=private,expected=403)
            await probe('team-reader-denied-write',reader,method='POST',tail='memories',body={'items':[]},expected=403)
            await probe('native-config-not-public',token,tail='config',expected=403)
            await probe('unknown-bank-denied',token,bank='does-not-exist',expected=403)
            _,newtoken=await issue(wa,'alice')
            await probe('rotated-new-key-works',newtoken)
            await pool.execute('UPDATE api_keys SET revoked=true WHERE key_id=$1',kid)
            await probe('revoked-old-key-next-request-denied',token,expected=401)
            await probe('new-key-survives-old-revocation',newtoken)
            await pool.execute('DELETE FROM bank_grants WHERE workspace_id=$1 AND subject_id=$2 AND bank_id=$3',wa,'alice',shared)
            await probe('grant-revocation-next-request-denied',newtoken,expected=403)
            stored=await pool.fetch('SELECT * FROM api_keys WHERE workspace_id=ANY($1)',list(routes))
            check('database-stores-no-plaintext-key',all(token not in str(dict(r)) and newtoken not in str(dict(r)) for r in stored))
            check('generated-secret-256-bits',len(token.split('_',2)[2])>=43)
            print(f'PASS {len(records)} checks; real local PG + HTTP Hindsight, no production gateway claim.')
        finally:
            await runner.cleanup()
            # Revoke test credentials; retained metadata is safe for review.
            await pool.execute('UPDATE api_keys SET revoked=true WHERE workspace_id=ANY($1)',list(routes))
    await pool.close()

asyncio.run(main())
