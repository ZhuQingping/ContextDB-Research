from pathlib import Path
import asyncio,json,httpx
from fastmcp import Client
p=Path(Path('/tmp/cb-cloud-e2e-path').read_text().strip());s=json.loads((p/'merged-private-state.json').read_text());admin=json.loads((p/'runtime/admin-key.json').read_text())['secret'];base='http://127.0.0.1:8891';url=base+'/v1/default/banks/'+s['bank_a']+'/config'
async def main():
 report={}
 async with httpx.AsyncClient(timeout=60,trust_env=False,headers={'Authorization':'Bearer '+admin}) as c:
  r=await c.get(url);r.raise_for_status();original=r.json()['overrides'];report['original_override_keys']=list(original)
  try:
   r=await c.patch(url,json={'updates':{'mcp_enabled_tools':['recall']}});r.raise_for_status();report['admin_rest_config_value']=r.json()['config'].get('mcp_enabled_tools');assert report['admin_rest_config_value']==['recall']
   for label,key in [('admin',admin),('business_rw',s['write_key'])]:
    async with Client(base+'/mcp/'+s['bank_a']+'/',auth=key) as m:
     names=sorted(x.name for x in await m.list_tools());report[label]={'listed_tools':names,'only_configured_recall':names==['recall']}
     if label=='business_rw':
      try:
       call=await m.call_tool('get_bank',{})
       report[label]['non_allowed_get_bank_call_succeeded']=not call.is_error
      except Exception as exc:
       report[label]['non_allowed_get_bank_call_succeeded']=False
       report[label]['non_allowed_call_error_type']=type(exc).__name__

  finally:
   r=await c.delete(url);r.raise_for_status()
   if original:
    r=await c.patch(url,json={'updates':original});r.raise_for_status()
   r=await c.get(url);r.raise_for_status();report['original_config_restored']=r.json()['overrides']==original;assert report['original_config_restored']
 (p/'mcp-bank-config-probe.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
asyncio.run(main())
