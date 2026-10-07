import asyncio,json,os,time,sys
from pathlib import Path
base=Path(__file__).resolve().parents[1]
sys.path.insert(0,'/Users/zhuqingping/Work/Database/Context/hindsight/hindsight-api-slim')
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
from hindsight_api.engine.embeddings import OnnxEmbeddings
from hindsight_api.engine.cross_encoder import FlashRankCrossEncoder
import numpy as np
cfg=json.loads((base.parent/'config.json').read_text())
docs=['订单库连接数耗尽，应用发布后连接池配置过大，将连接池上限从200降到50恢复。','数据库慢查询来自缺少订单时间索引，建立索引后恢复。','主库磁盘空间不足，清理过期归档日志并扩容。','数据库复制延迟来自长事务，结束长事务后追平。','连接数据库失败，安全组没有开放5432端口，修改规则解决。','备份恢复演练成功，恢复时间为12分钟。']
queries=['应用发布以后连接被耗尽了，之前怎么处理？','订单查询很慢应该增加什么？','主库磁盘满了怎么办？','备库一直落后于主库怎么办？','网络不通导致无法连接数据库怎么排查？','上次恢复备份用了多久？']
async def main():
    result={'dataset':'6 synthetic Chinese DB incident docs and 6 manually mapped queries; not benchmark','expected_ids':list(range(6)),'models':{}}
    model=OnnxEmbeddings(model_id='intfloat/multilingual-e5-small',model_path=cfg['HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_PATH'],tokenizer_name_or_path=cfg['HINDSIGHT_API_EMBEDDINGS_ONNX_TOKENIZER_NAME_OR_PATH'])
    t=time.monotonic();await model.initialize();init=time.monotonic()-t
    t=time.monotonic();dv=np.array(await model.encode_documents(docs));qv=np.array(await model.encode_query(queries));secs=time.monotonic()-t
    ranks=np.argsort(-(qv@dv.T),axis=1).tolist();hits=sum(r[0]==i for i,r in enumerate(ranks))
    result['models']['embedding']={'id':model.model_id,'dimension':model.dimension,'init_seconds':init,'encode_12_texts_seconds':secs,'ranks':ranks,'hit_at_1':hits/6,'norms':np.linalg.norm(dv,axis=1).tolist(),'real_model':True,'outbound_inference_calls':0}
    (base/'evidence/models-local.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    rerank=FlashRankCrossEncoder(model_name='ms-marco-TinyBERT-L-2-v2',cache_dir=str(base/'.models-cache'))
    try:
        t=time.monotonic();await rerank.initialize();ri=time.monotonic()-t
        t=time.monotonic();scores=await rerank.predict([(q,d) for q in queries for d in docs]);rs=time.monotonic()-t
        rr=np.argsort(-np.array(scores).reshape(6,6),axis=1).tolist()
        result['models']['rerank']={'id':rerank.model_name,'init_seconds':ri,'36_pairs_seconds':rs,'ranks':rr,'hit_at_1':sum(r[0]==i for i,r in enumerate(rr))/6,'real_model':True,'outbound_inference_calls':0,'note':'small English reranker used only to verify local execution; not recommended for Chinese product'}
    except Exception as e: result['models']['rerank']={'status':'failed','error':str(e),'type':type(e).__name__}
    if result['models'].get('rerank',{}).get('real_model'):
        from aiohttp import web
        from aiohttp.test_utils import TestServer
        from hindsight_api.engine.embeddings import RemoteTEIEmbeddings
        from hindsight_api.engine.cross_encoder import RemoteTEICrossEncoder
        from hindsight_api.engine.aiohttp_session import close_loop_sessions
        calls=[]
        async def handle(req):
            data=await req.json() if req.method=='POST' else {}
            calls.append({'method':req.method,'path':req.path,'input_count':len(data.get('inputs',data.get('texts',[])))})
            if req.path=='/info': return web.json_response({'model_id':'same-local-artifacts-test-wrapper'})
            if req.path=='/embed': return web.json_response(await model.encode(data['inputs']))
            values=await rerank.predict([(data['query'],d) for d in data['texts']])
            return web.json_response([{'index':i,'score':float(v)} for i,v in enumerate(values)])
        app=web.Application();app.router.add_route('*','/{tail:.*}',handle);server=TestServer(app);await server.start_server()
        try:
            url=str(server.make_url('')).rstrip('/')
            remote=RemoteTEIEmbeddings(url,query_prefix='query: ',passage_prefix='passage: ')
            await remote.initialize();t=time.monotonic();rd=np.array(await remote.encode_documents(docs));rq=np.array(await remote.encode_query(queries));elapsed=time.monotonic()-t
            remote_r=RemoteTEICrossEncoder(url);await remote_r.initialize();rscores=await remote_r.predict([(q,d) for q in queries for d in docs])
            result['http_parity']={'note':'real local models behind loopback TEI-contract wrapper, NOT real TEI deployment or MaaS','embedding_max_abs_error':float(max(np.max(np.abs(rd-dv)),np.max(np.abs(rq-qv)))),'rerank_max_abs_error':float(np.max(np.abs(np.array(rscores)-np.array(scores)))),'embedding_12_texts_seconds':elapsed,'requests':calls}
            assert result['http_parity']['embedding_max_abs_error']<1e-6
            assert result['http_parity']['rerank_max_abs_error']<1e-6
        finally: await close_loop_sessions();await server.close()
    (base/'evidence/models-local.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
asyncio.run(main())
