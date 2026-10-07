#!/usr/bin/env python3
"""Authenticated native MCP tenancy checks on disposable banks, no LLM required."""
import asyncio,json,uuid
from pathlib import Path
import httpx,httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'round2/evidence/mcp-auth-probe.json'; records=[]
def check(name,ok,**details):
    records.append(dict(name=name,passed=bool(ok),**details));OUT.write_text(json.dumps(records,indent=2,ensure_ascii=False));assert ok,name
async def main():
    keys=json.loads((ROOT/'.secrets/cell-b-keys.json').read_text()); bank='round2-mcp-'+uuid.uuid4().hex[:10]
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8890',trust_env=False,timeout=60) as h:
        for who in ['team_a','team_b']:
            hdr={'Authorization':'Bearer '+keys[who]}
            r=await h.put('/v1/default/banks/'+bank,headers=hdr,json={'retain_extraction_mode':'chunks','enable_observations':False})
            check('prepare-'+who,r.status_code==200)
            r=await h.post('/v1/default/banks/'+bank+'/memories',headers=hdr,json={'items':[{'document_id':'same-doc','content':f'Synthetic MCP private marker {who} {bank}.'}]})
            check('retain-'+who,r.status_code==200)
        for name,hdr in [('missing',{}),('invalid',{'Authorization':'Bearer invalid-round2'})]:
            r=await h.post('/mcp/'+bank+'/',headers={**hdr,'Accept':'application/json, text/event-stream'},json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'round2','version':'1'}}})
            check('mcp-'+name+'-key-denied',r.status_code==401,status=r.status_code)
    a_session=None
    for who,other in [('team_a','team_b'),('team_b','team_a')]:
        async with httpx2.AsyncClient(headers={'Authorization':'Bearer '+keys[who]},trust_env=False,timeout=60) as h:
            async with streamable_http_client('http://127.0.0.1:8890/mcp/'+bank+'/',http_client=h) as streams:
                async with ClientSession(streams[0],streams[1]) as s:
                    await s.initialize(); ts=await s.list_tools()
                    check('authenticated-tool-discovery-'+who,any(t.name=='recall' for t in ts.tools),tool_count=len(ts.tools))
                    result=await s.call_tool('recall',{'query':f'Synthetic MCP private marker {bank}','budget':'low','max_tokens':500})
                    obj=result.model_dump(mode='json'); body=json.dumps(obj)
                    check('mcp-isolation-'+who,not result.is_error and who in body and other not in body)
    print(f'PASS {len(records)} native MCP HTTP/SDK checks; no proof of custom cloud MCP authorization.')
asyncio.run(main())
