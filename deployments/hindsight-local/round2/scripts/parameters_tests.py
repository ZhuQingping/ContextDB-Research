import json,os,shutil,subprocess,time
from pathlib import Path
base=Path(__file__).resolve().parents[1]; source=Path('/Users/zhuqingping/Work/Database/Context/hindsight/hindsight-api-slim'); dest=base/'.parameters-tests/tests'; dest.mkdir(parents=True,exist_ok=True)
site=base/'.venv-parameters/lib/python3.12/site-packages'
(site/'deployment-base.pth').write_text(str(base.parent/'.venv/lib/python3.12/site-packages')+'\n')
names=['config_validation','config_env_readers','hierarchical_config','bank_config_value_types','config_resolution_shape','recall_budget_config','per_operation_llm_config','onnx_embeddings','tei_embeddings','tei_cross_encoder','reranker_max_candidates_budget','embeddings_openai_batch_size','embeddings_asymmetric_prefixes','reranker_score_normalization','embedding_retry','reranker_retry']
for name in names: shutil.copy2(source/'tests'/f'test_{name}.py',dest/f'test_{name}.py')
for name in ['__init__.py','conftest.py','aiohttp_stub.py']:
    if (source/'tests'/name).exists(): shutil.copy2(source/'tests'/name,dest/name)
env=os.environ.copy();env['PYTHONPATH']=str(source);env['PYTHONDONTWRITEBYTECODE']='1';env['HINDSIGHT_TEST_PG_PORT']='55439'
cmd=[str(base/'.venv-parameters/bin/python'),'-m','pytest',str(dest),'-q','-o','asyncio_mode=auto','--tb=short','--junitxml='+str(base/'evidence/parameters-tests.xml')]
t=time.monotonic()
with (base/'evidence/parameters-tests.log').open('w') as log: r=subprocess.run(cmd,cwd=dest.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
result={'command':cmd,'exit_code':r.returncode,'seconds':time.monotonic()-t,'copied_unmodified_upstream_tests':names};(base/'evidence/parameters-tests-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
