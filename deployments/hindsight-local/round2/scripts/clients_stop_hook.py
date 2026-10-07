import sys,subprocess,pathlib,json,os
b=pathlib.Path(__file__).resolve().parents[1]
data=sys.stdin.read()
(b/'evidence/clients-stop-payload.json').write_text(data)
p=subprocess.run(['node',str(b/'clients-work/hindsight-integrations/coding-agents/dist/codex-stop-hook.js')],input=data,text=True,capture_output=True)
(b/'evidence/clients-stop-hook-result.json').write_text(json.dumps({'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}))
print(p.stdout,end='')
sys.exit(p.returncode)
