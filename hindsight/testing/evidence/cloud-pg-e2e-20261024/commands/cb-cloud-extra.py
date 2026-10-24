from pathlib import Path
import asyncio,json,httpx
from hindsight_client import Hindsight
p=Path(Path('/tmp/cb-cloud-e2e-path').read_text().strip());admin=json.loads((p/'runtime/admin-key.json').read_text())['secret'];base='http://127.0.0.1:8891';events=[]
async def main():
 async with httpx.AsyncClient(timeout=60,trust_env=False) as c:
  h={'Authorization':'Bearer '+admin};s=json.loads((p/'merged-private-state.json').read_text());uid=s['user_id'];bank=s['bank_a']
  r=await c.post(base+f'/ext/contextdb/v1/users/{uid}/keys',headers=h,json={'name':'All workspaces readonly validation','authorization':{'mode':'all','permission':'read'}});assert r.status_code==201;issued=r.json();key=issued['secret']
  sdk=Hindsight(base_url=base,api_key=key)
  try:
   for b in ['cloud_merged_a','cloud_merged_b','cloud_split_a','cloud_split_b']:
    rr=await sdk.arecall(bank_id=b,query='Lighthouse');events.append({'case':'all-read-'+b,'passed':True,'result_count':len(rr.results)})
   r=await c.patch(base+f'/ext/contextdb/v1/users/{uid}/keys/{issued["key_id"]}',headers={**h,'If-Match':f'"{issued["version"]}"'},json={'authorization':{'mode':'selected','workspaces':[{'bank_id':bank,'workspace_id':s['workspace_id'],'permission':'read'}]}});assert r.status_code==200;events.append({'case':'key-authorization-all-to-selected','passed':True})
   r=await c.post(base+'/v1/default/banks/cloud_merged_b/memories/recall',headers={'Authorization':'Bearer '+key},json={'query':'Lighthouse'});assert r.status_code==403;events.append({'case':'updated-key-loses-other-space','passed':True,'status':403})
   headers={'Authorization':'Bearer '+s['write_key']}
   before=(await c.get(base+f'/v1/default/banks/{bank}',headers=headers)).json()
   r=await c.put(base+f'/v1/default/banks/{bank}',headers=headers,json={});assert r.status_code==200
   after=(await c.get(base+f'/v1/default/banks/{bank}',headers=headers)).json();assert before==after;events.append({'case':'existing-bank-empty-put-is-read-noop','passed':True,'status':200})
   r=await c.put(base+f'/v1/default/banks/{bank}',headers=headers,json={'name':'Forbidden rename probe'});assert r.status_code==403;events.append({'case':'native-bank-change-denied','passed':True,'status':403})
   r=await c.put(base+'/v1/default/banks/cloud_unregistered_e2e',headers=headers,json={});assert r.status_code==403;events.append({'case':'native-unregistered-bank-create-denied','passed':True,'status':403})
   r=await c.delete(base+f'/v1/default/banks/{bank}',headers={'Authorization':'Bearer '+s['write_key']});assert r.status_code==403;events.append({'case':'native-bank-delete-denied','passed':True,'status':403})
   r=await c.post('http://127.0.0.1:9991/api/auth/login',headers={'Origin':'http://127.0.0.1:9991'},json={'key':s['write_key']});assert r.status_code==401;events.append({'case':'business-key-not-ui-password','passed':True,'status':401})
   r=await c.delete(base+f'/ext/contextdb/v1/users/{uid}/keys/{issued["key_id"]}',headers=h);assert r.status_code==204
   r=await c.post(base+f'/mcp/{bank}/',headers={'Authorization':'Bearer '+key,'Accept':'application/json, text/event-stream'},json={'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}});assert r.status_code==401;events.append({'case':'revoked-key-mcp-denied','passed':True,'status':401})
  finally:await sdk.aclose()
 (p/'extra-e2e.json').write_text(json.dumps({'cases':events},indent=2));print('Extra passed',len(events))
asyncio.run(main())
