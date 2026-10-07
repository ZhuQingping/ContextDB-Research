import os,sys,json,pathlib,time
b=pathlib.Path(__file__).resolve().parents[1]
os.environ['HERMES_HOME']=str(b/'clients-work/hermes-profile')
os.environ['TERMINAL_CWD']=str(b/'clients-work/codex-project')
sys.path.insert(0,str(b/'clients-work/hermes-runtime'))
from run_agent import AIAgent
secret=json.loads((b.parent/'.secrets/codex/auth.json').read_text())['tokens']['access_token']
phase=sys.argv[1]
a=AIAgent(model='gpt-6.1-sol',provider='openai-codex',api_mode='codex_responses',api_key=secret,base_url='https://chatgpt.com/backend-api/codex',enabled_toolsets=[],max_iterations=2,quiet_mode=True,skip_context_files=True,skip_background_review=True,save_trajectories=False,cwd=str(b/'clients-work/codex-project'))
prompt=('Synthetic acceptance fact: project CDB-HERMES-862 uses approval code LARCH-2074 and pool limit 47. Reply acknowledged only, do not call tools.' if phase=='retain' else 'What approval code and pool limit are recorded for project CDB-HERMES-862? Answer only from supplied memory. Do not call tools. If no memory exists say unknown.')
start=time.time()
r=a.run_conversation(prompt)
a.close()
result={k:r.get(k) for k in ['final_response','completed','api_calls','error']}
result['seconds']=time.time()-start
(b/f'evidence/clients-hermes-runtime-{phase}.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps(result,ensure_ascii=False))
