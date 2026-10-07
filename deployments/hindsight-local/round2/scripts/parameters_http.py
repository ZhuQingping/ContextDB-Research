import json,time,httpx
from pathlib import Path
base=Path(__file__).resolve().parents[1];keys=json.loads((base.parent/'.secrets/cell-b-keys.json').read_text());records=[];bank='round2-params-'+str(int(time.time()));path='/v1/default/banks/'+bank
client=httpx.Client(base_url='http://127.0.0.1:8890',trust_env=False,timeout=40)
def call(label,method,suffix,who='team_a',body=None,expected=200):
    r=client.request(method,path+suffix,headers={'Authorization':'Bearer '+keys[who]},json=body)
    try: data=r.json()
    except Exception: data={'text':r.text}
    records.append({'label':label,'method':method,'bank':bank,'suffix':suffix,'actor':who,'status':r.status_code,'response':data})
    (base/'evidence/parameters-http-results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    assert r.status_code in ([expected] if isinstance(expected,int) else expected),(label,r.status_code)
    return data
for who in keys:
    if who in ['team_a','team_b']:call('create-'+who,'PUT','',who,{'name':bank})
a=call('initial-a','GET','/config');b=call('initial-b','GET','/config',who='team_b');assert a['overrides']==b['overrides']
call('write-allowlisted-a','PATCH','/config',body={'updates':{'retain_mission':'ROUND2_ALPHA','enable_auto_consolidation':False,'recall_max_tokens':777}})
a=call('readback-a','GET','/config');assert a['config']['retain_mission']=='ROUND2_ALPHA' and a['config']['recall_max_tokens']==777
call('write-env-name-b','PATCH','/config',who='team_b',body={'updates':{'HINDSIGHT_API_RETAIN_MISSION':'ROUND2_BETA'}})
b=call('same-name-isolated-b','GET','/config',who='team_b');assert b['config']['retain_mission']=='ROUND2_BETA' and b['config']['recall_max_tokens']==2048
for key,value in [('llm_provider','openai'),('llm_model','fake-model'),('llm_api_key','synthetic-not-a-secret'),('llm_output_language','zh'),('database_url','synthetic-invalid'),('unknown_field_123',True),('enable_auto_consolidation','not-a-boolean'),('recall_max_tokens','not-an-integer')]:
    call('reject-'+key,'PATCH','/config',body={'updates':{key:value}},expected=[400,422])
a=call('rejected-writes-did-not-mutate','GET','/config');assert a['config']['retain_mission']=='ROUND2_ALPHA' and a['config']['recall_max_tokens']==777
assert not {'llm_provider','llm_model','llm_api_key','database_url'} & set(a['config'])
call('mixed-valid-invalid-rejected','PATCH','/config',body={'updates':{'retain_mission':'BAD_ATOMICITY','llm_provider':'openai'}},expected=[400,422])
a=call('atomic-readback','GET','/config');assert a['config']['retain_mission']=='ROUND2_ALPHA'
call('clear-one-override','PATCH','/config',body={'updates':{'retain_mission':None}})
a=call('clear-readback','GET','/config');assert 'retain_mission' not in a['overrides'] and a['config']['recall_max_tokens']==777
b=call('other-tenant-still-unmodified','GET','/config',who='team_b');assert b['config']['retain_mission']=='ROUND2_BETA'
summary={'exit_code':0,'checks':len(records),'bank':bank,'scope':'real authenticated HTTP with two tenant schemas, no LLM call; not every configurable field','retained_empty_test_banks':True}
(base/'evidence/parameters-http-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
