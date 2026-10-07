import asyncio,json,sys
from contextlib import asynccontextmanager
from pathlib import Path
sys.path.insert(0,'/Users/zhuqingping/Work/Database/Context/hindsight/hindsight-api-slim')
from hindsight_api.config_resolver import ConfigResolver
from hindsight_api import RequestContext
class RecordingBackend:
    def __init__(self): self.writes=[]
    @asynccontextmanager
    async def transaction(self): yield self
    async def fetchrow(self,*args): return {'config':{}}
    async def execute(self,sql,*args): self.writes.append({'updates':json.loads(args[0]),'bank':args[1]});return 'UPDATE 1'
class Extension:
    def __init__(self,mode): self.mode=mode
    async def get_allowed_config_fields(self,context,bank_id):
        if self.mode=='timeout': raise TimeoutError('synthetic policy dependency timeout')
        if self.mode=='runtime_error': raise RuntimeError('synthetic policy dependency unavailable')
        if self.mode=='value_error': raise ValueError('synthetic authorization denied')
        if self.mode=='empty_set': return set()
        return {'retain_mission'}
async def main():
    rows=[]
    for mode in ['timeout','runtime_error','empty_set','value_error','allow']:
        backend=RecordingBackend();resolver=ConfigResolver(backend,Extension(mode))
        outcome='allowed'
        try: await resolver.update_bank_config('round2-params-fault',{'retain_mission':'synthetic update'},RequestContext())
        except Exception as exc: outcome='rejected';error=type(exc).__name__+': '+str(exc)
        rows.append({'fault_or_policy':mode,'outcome':outcome,'persistence_called':bool(backend.writes),'writes':backend.writes,'error':error if outcome=='rejected' else None})
    assert [r['persistence_called'] for r in rows]==[True,True,False,False,True]
    result={'real_source':'ConfigResolver.update_bank_config and validate_bank_config_updates','database':'recording backend fixture, NOT PostgreSQL; validates whether real resolver invokes persistence','exit_code':0,'cases':rows}
    (Path(__file__).resolve().parents[1]/'evidence/parameters-failopen.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
asyncio.run(main())
