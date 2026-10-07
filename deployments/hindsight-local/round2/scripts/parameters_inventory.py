import ast,csv,dataclasses,json,os,sys
from pathlib import Path
ROOT=Path('/Users/zhuqingping/Work/Database/Context/hindsight/hindsight-api-slim')
OUT=Path(__file__).resolve().parents[1]/'evidence'
for key in list(os.environ):
    if key.startswith('HINDSIGHT_'): del os.environ[key]
sys.path.insert(0,str(ROOT))
from hindsight_api.config import HindsightConfig
src=ROOT/'hindsight_api/config.py'; tree=ast.parse(src.read_text())
constants={n.targets[0].id:n.value.value for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant)}
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='HindsightConfig')
fields={n.target.id:n for n in cls.body if isinstance(n,ast.AnnAssign)}
fromenv=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='from_env')
expressions={k.arg:k.value for n in ast.walk(fromenv) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='cls' for k in n.keywords}
config=HindsightConfig.from_env(); rows=[]
customer={'llm_output_language','retain_mission','retain_custom_instructions','observations_mission','reflect_mission','retain_extraction_mode','enable_auto_consolidation','enable_observations','store_document_text'}
fixed_terms=('database','extension','schema','api_key','base_url','provider','host','port','auth','extension','mcp','headers','codex','credential','secret','path','directory')
for f in dataclasses.fields(config):
    expr=expressions.get(f.name)
    envs=sorted({constants[n.id] for n in ast.walk(expr) if isinstance(n,ast.Name) and n.id in constants and isinstance(constants[n.id],str) and constants[n.id].startswith('HINDSIGHT_')}) if expr else []
    val=getattr(config,f.name)
    secret=any(x in f.name for x in ('api_key','secret','password','default_headers'))
    if secret: val='<redacted: unset>' if not val else '<redacted>'
    category='customer_allowlist_proposal' if f.name in customer else 'platform_fixed_proposal' if any(x in f.name for x in fixed_terms) else 'operations_tunable_proposal'
    rows.append({'field':f.name,'type':ast.unparse(fields[f.name].annotation),'upstream_default':val,'env_names':envs,'upstream_bank_overridable':f.name in config._CONFIGURABLE_FIELDS,'cloud_owner_proposal':category,'source_line':fields[f.name].lineno,'from_env_expression':ast.unparse(expr) if expr else 'derived; see source'})
(OUT/'parameters-inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2,default=str))
with (OUT/'parameters-inventory.csv').open('w') as fp:
    w=csv.DictWriter(fp,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
allenv=sorted({v for k,v in constants.items() if k.startswith('ENV_') and isinstance(v,str)})
(OUT/'parameters-env-constants.json').write_text(json.dumps(allenv,indent=2))
import hindsight_api.config as config_module
envrows=[]
for node in tree.body:
    if not isinstance(node,ast.Assign) or not isinstance(node.targets[0],ast.Name): continue
    name=node.targets[0].id
    if not name.startswith('ENV_') or name not in constants or not isinstance(constants[name],str): continue
    env=constants[name];matched=[r for r in rows if env in r['env_names']]
    default_name='DEFAULT_'+name[4:]
    default=getattr(config_module,default_name,'<derived/provider-dependent; see expressions>')
    if any(x in name for x in ('API_KEY','SECRET','PASSWORD','HEADERS')): default='<secret: do not export>'
    envrows.append({'environment_variable':env,'constant':name,'default_constant':default_name,'default_constant_value':default,'config_fields':[r['field'] for r in matched],'line':node.lineno})
with (OUT/'parameters-env-inventory.csv').open('w') as fp:
    w=csv.DictWriter(fp,fieldnames=list(envrows[0]));w.writeheader();w.writerows(envrows)
(OUT/'parameters-dynamic-families.json').write_text(json.dumps({'LLM':{'pattern':'HINDSIGHT_API_{OP_}LLM_{n}_{FIELD}','operations':['','RETAIN','REFLECT','CONSOLIDATION','MENTAL_MODEL_REFRESH'],'source_line':2613},'reranker':{'pattern':'HINDSIGHT_API_RERANKER_{n}_{FIELD}','source_line':2819},'worker_reservations':{'pattern':'HINDSIGHT_API_WORKER_{TYPE}_RESERVED_SLOTS','legacy':'HINDSIGHT_API_WORKER_{TYPE}_MAX_SLOTS','source_line':962},'extension':'Extension-specific environment prefixes depend on configured plugin; not a closed global list.'},indent=2))

summary={'fields':len(rows),'bank_overridable':len(config._CONFIGURABLE_FIELDS),'env_constants':len(allenv),'source':str(src),'note':'Runtime clean-env from_env defaults, not shell credential values. Indexed LLM chain and extension prefix parameters are dynamic families; see docs/source.'}
(OUT/'parameters-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
