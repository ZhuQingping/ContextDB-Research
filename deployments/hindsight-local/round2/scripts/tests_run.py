#!/usr/bin/env python3
"""Run a test command with UTC timestamps, exit code, and durable log; no secret env dump."""
import argparse,datetime,json,os,pathlib,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--cwd',required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];out=root/'evidence'/a.name;out.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env.update({'PYTHONDONTWRITEBYTECODE':'1','PYTEST_ADDOPTS':'','UV_PYTHON':'3.12'})
for k in list(env):
 if k.startswith('HINDSIGHT_API_'):del env[k]
start=datetime.datetime.now(datetime.timezone.utc);t=time.monotonic()
with (out/'run.log').open('w') as f:r=subprocess.run(a.command,cwd=a.cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
meta={'command':a.command,'cwd':a.cwd,'started_utc':start.isoformat(),'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':round(time.monotonic()-t,3),'exit_code':r.returncode}
(out/'command.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta));raise SystemExit(r.returncode)
