import os,sys,json,pathlib,subprocess,time,secrets
b=pathlib.Path(__file__).resolve().parents[1]
p=b/'clients-work/openclaw-profile';p.mkdir(exist_ok=True)
if sys.argv[1]=='stop':
 pid_file=p/'gateway.pid'
 if not pid_file.exists():print('No dedicated gateway PID recorded');sys.exit(0)
 pid=int(pid_file.read_text())
 proc=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
 if proc.returncode!=0 or not proc.stdout.strip():print('Dedicated gateway already stopped');sys.exit(0)
 if str(b/'clients-work/openclaw-runtime') not in proc.stdout or 'gateway run --port 18879' not in proc.stdout:raise SystemExit('PID identity mismatch; no process stopped')
 import signal
 os.kill(pid,signal.SIGTERM);print('SIGTERM sent to dedicated gateway',pid);sys.exit(0)
s=json.loads((pathlib.Path.home()/'.claude/settings.json').read_text())['env']
env=os.environ.copy();env.update({'OPENCLAW_STATE_DIR':str(p),'OPENCLAW_CONFIG_PATH':str(p/'openclaw.json'),'ROUND2_MODEL_API_KEY':s['ANTHROPIC_AUTH_TOKEN'],'ROUND2_MODEL_BASE_URL':s['ANTHROPIC_BASE_URL']})
custom_headers={}
for i,line in enumerate(s.get('ANTHROPIC_CUSTOM_HEADERS','').splitlines()):
 if ':' in line:
  name,value=line.split(':',1);key='ROUND2_MODEL_HEADER_'+str(i);env[key]=value.strip();custom_headers[name.strip()]='${'+key+'}'
env['PATH']=str(b/'clients-work/node24/bin')+':'+env['PATH']
secret_file=p/'gateway-token.private'
if not secret_file.exists():
 secret_file.write_text(secrets.token_urlsafe(32));secret_file.chmod(0o600)
env['ROUND2_GATEWAY_TOKEN']=secret_file.read_text().strip()
model=s.get('ANTHROPIC_MODEL','glm-5.3-flash')
config={'gateway':{'mode':'local','port':18879,'bind':'loopback','auth':{'mode':'token','token':'${ROUND2_GATEWAY_TOKEN}'}},'agents':{'defaults':{'workspace':str(b/'clients-work/codex-project'),'model':{'primary':'round2/'+model}}},'models':{'providers':{'round2':{'baseUrl':'${ROUND2_MODEL_BASE_URL}','apiKey':'${ROUND2_MODEL_API_KEY}','api':'anthropic-messages','authHeader':True,'headers':custom_headers,'models':[{'id':model,'name':model,'contextWindow':128000,'maxTokens':4096}]}}},'tools':{'deny':['*']},'plugins':{'allow':['hindsight-openclaw'],'load':{'paths':[str(b/'clients-work/openclaw')]},'slots':{'memory':'hindsight-openclaw'},'entries':{'hindsight-openclaw':{'enabled':True,'hooks':{'allowConversationAccess':True},'config':{'hindsightApiUrl':'http://127.0.0.1:8888','dynamicBankId':False,'bankId':'round2-client-openclaw','autoRecall':True,'recallTypes':['world','observation','experience'],'retainQueuePath':str(p/'retain-queue.jsonl'),'logLevel':'debug','logSummaryIntervalMs':0}}}}}
(p/'openclaw.json').write_text(json.dumps(config,indent=2))
phase=sys.argv[1]
if phase=='start':
 out=(b/'clients-work/openclaw-gateway.log').open('a')
 proc=subprocess.Popen([str(b/'clients-work/node24/bin/node'),str(b/'clients-work/openclaw-runtime/node_modules/openclaw/openclaw.mjs'),'gateway','run','--port','18879'],cwd=b/'clients-work/codex-project',env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
 (p/'gateway.pid').write_text(str(proc.pid));print('started PID',proc.pid);sys.exit(0)
prompt=('Synthetic acceptance fact: project CDB-CLAW-634 uses approval code FIR-8193 and pool limit 39. Reply acknowledged only. Do not use tools.' if phase=='retain' else 'What approval code and pool limit are recorded for project CDB-CLAW-634? Answer only from supplied memory. Do not use tools. If no memory exists say unknown.')
args=[str(b/'clients-work/node24/bin/node'),str(b/'clients-work/openclaw-runtime/node_modules/openclaw/openclaw.mjs'),'agent','--session-key','agent:main:webchat:direct:round2-claw-'+phase,'--message',prompt,'--json','--timeout','180']
with (b/f'evidence/clients-openclaw-runtime-{phase}.jsonl').open('w') as out,(b/f'evidence/clients-openclaw-runtime-{phase}.stderr').open('w') as err:
 start=time.time();r=subprocess.run(args,cwd=b/'clients-work/codex-project',env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=240)
(b/f'evidence/clients-openclaw-runtime-{phase}-status.json').write_text(json.dumps({'exit':r.returncode,'seconds':time.time()-start}))
