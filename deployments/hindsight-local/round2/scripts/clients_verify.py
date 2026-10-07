from pathlib import Path
import json,urllib.request,xml.etree.ElementTree as ET
b=Path(__file__).resolve().parents[1]
e=b/'evidence'
def records(name):return [json.loads(x) for x in (e/name).read_text().splitlines() if x.strip()]
checks=[]
def check(name,ok,detail):
 checks.append({'name':name,'passed':bool(ok),'detail':detail})
for suite in ['coding-tests-layout-fixed','openclaw-tests']:
 d=json.loads((e/f'clients-{suite}.json').read_text());check(suite,d['success'] and d['numFailedTests']==0,{'passed':d['numPassedTests'],'total':d['numTotalTests']})
r=ET.parse(e/'clients-hermes-tests.xml').getroot();s=r.find('testsuite');check('hermes-plugin-unit',s.get('failures')=='0' and s.get('errors')=='0',dict(s.attrib))
d=records('clients-codex-auto-recall.jsonl');answer=' '.join(x.get('item',{}).get('text','') for x in d);check('codex-real-auto-recall','WILLOW-3815' in answer and not any(x.get('item',{}).get('type') in ['mcp_tool_call','command_execution'] for x in d),answer)
d=records('clients-claude-auto-recall.jsonl');result=next(x for x in reversed(d) if x.get('type')=='result');check('claude-real-auto-recall','BIRCH-6937' in result['result'] and '57' in result['result'] and not result['is_error'],result['result'])
d=json.loads((e/'clients-hermes-runtime-recall.json').read_text());check('hermes-real-runtime-auto-recall',d['completed'] and 'LARCH-2074' in d['final_response'] and '47' in d['final_response'],d)
d=json.loads((e/'clients-openclaw-runtime-recall.jsonl').read_text());answer=' '.join(x.get('text','') for x in d['result']['payloads']);check('openclaw-real-cli-auto-recall',d['status']=='ok' and 'FIR-8193' in answer and '39' in answer,answer)
markers={'codex':'WILLOW-3815','claude':'BIRCH-6937','hermes':'LARCH-2074','openclaw':'FIR-8193'}
for client,marker in markers.items():
 req=urllib.request.Request('http://127.0.0.1:8888/v1/default/banks/round2-client-'+client+'/memories/recall',data=json.dumps({'query':'synthetic project approval code and pool limit','max_tokens':4000,'budget':'mid'}).encode(),headers={'Content-Type':'application/json'})
 d=json.load(urllib.request.urlopen(req,timeout=60));texts=' '.join(x['text'] for x in d.get('results',[]));check(client+'-bank-recall',marker in texts and all(v not in texts for k,v in markers.items() if k!=client),{'count':len(d.get('results',[])),'texts':texts});(e/f'clients-{client}-final-recall.json').write_text(json.dumps(d,indent=2,ensure_ascii=False))
out={'passed':all(c['passed'] for c in checks),'checks':checks,'scope':'synthetic smoke, localhost Hindsight, real clients/models; not full enterprise acceptance'}
(e/'clients-verdict.json').write_text(json.dumps(out,indent=2,ensure_ascii=False));print(json.dumps({'passed':out['passed'],'checks':len(checks)}));raise SystemExit(0 if out['passed'] else 1)
