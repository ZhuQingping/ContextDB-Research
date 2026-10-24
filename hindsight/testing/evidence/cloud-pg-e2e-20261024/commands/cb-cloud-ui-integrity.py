from pathlib import Path
import os,json,signal,time,socket,subprocess,shutil
p=Path(Path('/tmp/cb-cloud-e2e-path').read_text().strip());root=Path.cwd();build=p/'source';process=json.loads((p/'processes.json').read_text());os.kill(process['ui'],signal.SIGTERM)
for n in range(30):
 s=socket.socket();s.settimeout(.1);alive=s.connect_ex(('127.0.0.1',9991))==0;s.close()
 if not alive:break
 time.sleep(1)
else:raise RuntimeError('UI did not stop; no cache mutation')
cache=build/'hindsight-control-plane/standalone/.next/server/route-cache';backup=p/'runtime-cache-backup';backup.mkdir(exist_ok=False);shutil.move(str(cache),str(backup/'route-cache'))
env={k:v for k,v in os.environ.items() if not k.startswith(('HINDSIGHT_','CONTEXTBASE_','CONTEXTDB_')) and k!='PGPASSWORD'};env.update(PYTHON_DOTENV_DISABLED='1',PYTHONPATH=str(build/'hindsight-extensions/contextdb-service')+':'+str(build/'hindsight-api-slim'),CONTEXTDB_DEPLOY_DIR=str(p/'runtime'),CONTEXTDB_PYTHON=str(root/'.venv/bin/python'))
code='from pathlib import Path;import json;from hindsight_ext_contextdb.artifacts import verify_ui_build,source_fingerprint,bundle_fingerprint;p=Path('+repr(str(build))+');verify_ui_build(p);print(json.dumps({"verified":True,"source_sha256":source_fingerprint(p),"bundle_sha256":bundle_fingerprint(p/"hindsight-control-plane/standalone")}))'
r=subprocess.run([str(root/'.venv/bin/python'),'-c',code],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(p/'ui-build-proof.json').write_text(r.stdout);assert r.returncode==0,r.stdout
with (p/'ui-restart.log').open('a') as log:proc=subprocess.Popen(['bash',str(build/'hindsight-extensions/contextdb-service/scripts/service.sh'),'ui'],cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
process['ui']=proc.pid;(p/'processes.json').write_text(json.dumps(process,indent=2));(p/'ui-cache-finding.json').write_text(json.dumps({'source_unchanged':True,'runtime_generated_files':'.next/server/route-cache/**','restart_guard_false_positive':True,'compiled_files_modified':False,'manifest_rewritten':False,'cache_backed_up':True,'verified_after_cache_removed':True,'ui_restart_pid':proc.pid,'code_fix_applied':False},indent=2));print('Original manifest matches after moving only generated cache; UI restarted',proc.pid)
