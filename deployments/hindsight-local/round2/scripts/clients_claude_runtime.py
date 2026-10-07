import os,sys,json,pathlib,subprocess,time
b=pathlib.Path(__file__).resolve().parents[1]
s=json.loads((pathlib.Path.home()/'.claude/settings.json').read_text())['env']
env=os.environ.copy();env.update({k:str(v) for k,v in s.items() if k.startswith('ANTHROPIC_') or k in ['API_TIMEOUT_MS','MCP_TOOL_TIMEOUT']})
c=b/'clients-work/claude-hook-config.json';c.write_text(json.dumps({'apiUrl':'http://127.0.0.1:8888','bankId':'round2-client-claude','autoInject':'recall','recallOptions':{'types':['world','observation']},'manageBankConfig':False,'autoSeed':False,'codebaseSurvey':False,'gitIngest':'none','retainSessions':True}))
env['HINDSIGHT_CONFIG']=str(c);env['HINDSIGHT_LOG_FILE']=str(b/'evidence/clients-claude-hook.log');env['HINDSIGHT_DIAG_FILE']=str(b/'evidence/clients-claude-hook-diag.jsonl')
d=b/'clients-work/hindsight-integrations/coding-agents/dist'
settings={'hooks':{'UserPromptSubmit':[{'hooks':[{'type':'command','command':'node '+str(d/'claude-hook.js'),'timeout':30}]}],'Stop':[{'hooks':[{'type':'command','command':'node '+str(d/'claude-stop-hook.js'),'timeout':60}]}]}}
phase=sys.argv[1]
prompt=('Synthetic acceptance fact: project CDB-CLAUDE-468 uses approval code BIRCH-6937 and pool limit 57. Reply acknowledged only. Do not use tools.' if phase=='retain' else 'What approval code and pool limit are recorded for project CDB-CLAUDE-468? Answer only from supplied memory. Do not use tools. If no memory exists say unknown.')
args=['claude','-p','--setting-sources','','--settings',json.dumps(settings),'--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--tools','','--output-format','stream-json','--verbose',prompt]
with (b/f'evidence/clients-claude-auto-{phase}.jsonl').open('w') as out,(b/f'evidence/clients-claude-auto-{phase}.stderr').open('w') as err:
 start=time.time();r=subprocess.run(args,cwd=b/'clients-work/codex-project',env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=240)
(b/f'evidence/clients-claude-auto-{phase}-status.json').write_text(json.dumps({'exit':r.returncode,'seconds':time.time()-start,'credentials':'existing user settings env copied in memory; no original changed'}))
