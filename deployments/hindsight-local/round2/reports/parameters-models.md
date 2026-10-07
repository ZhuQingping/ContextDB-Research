# 参数与模型核验（2026-10-04）

基线：本机 Hindsight `f7dd3f4fd7420f7beec60c32c965e5e5cf7be066`。本报告区分“实测”“源码事实”“建议”，不把建议默认值或本地模拟接口写成华为云已验收。

## 结论

1. 服务端 `HindsightConfig` 有 **493 个字段**；干净环境执行 `from_env()` 取得默认值。`_CONFIGURABLE_FIELDS` 只有 **51 个**可通过租户/Bank 层覆盖的行为参数；**不包含模型供应商、模型名、模型密钥、模型地址**。仓库 CLAUDE.md 仍举这些为 hierarchical 的示例，与当前代码不一致，应以代码和测试为准。
2. 不应对客户公开 493 个环境变量，也不应把 51 项全部原样开放。客户使用“记忆用途、抽取方式、是否自动整理、输出语言/说明、召回预算”等受控产品配置；平台持有模型凭据、数据库地址、扩展类、线程/连接/并发、物理存储和原始配置写接口。
3. 本机 Embedding 是本地 ONNX `intfloat/multilingual-e5-small`（384维）；Reranker 是 `rrf`（排序融合，不是神经重排模型）；LLM 是远端 `openai-codex / gpt-6.1-sol`。因此“本机有GPT凭据”不等于本机运行GPT推理。
4. 本地 Embedding 与本地 Rerank 均已实际执行成功；同一真实模型通过 loopback HTTP 适配返回的向量和重排分数与进程内结果一致。本地还是MaaS本身不能判断准确率，必须固定模型/版本/预处理再比。没有华为MaaS凭据，未验证其效果、时延、限流或价格。

## 完整清单与验证入口

- [493字段清单 JSON](../evidence/parameters-inventory.json)、[CSV](../evidence/parameters-inventory.csv)：类型、干净环境默认值、环境变量映射、Bank可覆盖性、云产品管理分类建议、源码行、from_env表达式。
- [493个ENV常量清单](../evidence/parameters-env-inventory.csv)：包括未直接成为dataclass字段的参数；不是与字段一一对应。
- [动态参数族](../evidence/parameters-dynamic-families.json)：多LLM链、reranker故障转移链、Worker任务类型预留槽位及旧别名。插件自己的环境前缀取决于所选插件，不能声称存在一个有限的“所有插件参数总数”。
- [提取脚本](../scripts/parameters_inventory.py)，执行退出码0；[执行日志](../evidence/parameters-inventory.log)。它清空子进程内 HINDSIGHT 环境后读取默认值，不读取或输出用户凭据。
- [配置/模型接口测试结果](../evidence/parameters-tests-result.json)、[JUnit](../evidence/parameters-tests.xml)：**354 passed、14 skipped，退出码0**。16个原样复制的上游测试模块，包括配置校验、层级覆盖、类型、各操作LLM配置、ONNX、TEI真实HTTP传输/重试、前缀、候选数量。不是全仓回归，也不是真实MaaS测试。 14项跳过中，10项Bank配置PG集成测试和1项MemoryEngine测试缺local-ml依赖，3项TEI性能测试缺真实服务地址；[逐项原因](../evidence/parameters-skips.json)。因此这里只证明已执行的配置/接口测试，不证明全部Bank配置集成通过。
- 初次复制漏辅助模块、遗漏pytest asyncio配置，均为测试环境搭建错误；补齐原文件并设置上游的auto模式后通过。日志保留为 `parameters-tests-initial-*.log`，未修改上游测试断言。

源码锚点（均位于源码仓库 `hindsight-api-slim/hindsight_api/`）：`config.py:2963`字段、`:3755`可覆盖白名单、`:3919`排除provider/model/credential的说明、`:4161`环境读取；`config_resolver.py:572`写入类型校验、`:863`类型校验实现。

## 云默认与客户配置建议

下表“云默认”是待实现并压测的服务配置基线，**不是实测得出的生产最优值**。未列出的行为参数先继承锁定版本的默认值，不随上游升级静默改变。

| 参数/类别 | 当前上游默认 | 首期云配置建议 | 客户是否可配 |
|---|---|---|---|
| DATABASE_URL | pg0 | 受管PG连接；关闭本地pg0路径 | 否 |
| DB_POOL_MIN_SIZE / MAX_SIZE | 5 / 100（每个连接池） | 起始2 / 10；按API与Worker进程数及其他连接预留计算PG总预算，压测后调 | 否 |
| WORKER_ENABLED | true | API关闭；独立Worker承担后台任务 | 否 |
| WORKER_MAX_SLOTS | 10 | 小规格起始2；CONSOLIDATION_RESERVED_SLOTS=1；扩容前验证任务公平性 | 否 |
| LLM_MAX_CONCURRENT | 32 | 小规格起始2，且网关限制整个租户/cell总并发；此参数本身不是集群全局额度 | 否 |
| EMBEDDINGS_PROVIDER | local / bge-small-en-v1.5 | 首期锁定一套经中文样本验收的模型；本地演示保持onnx多语e5，不直接作为生产质量结论 | 否，不允许用户就地换向量空间 |
| RERANKER_PROVIDER | local / ms-marco-MiniLM-L-6-v2 | 基础档可用rrf；神经重排档必须质量/费用验证后启用 | 产品档位，不暴露原始provider |
| LLM_PROVIDER / MODEL / KEY / BASE_URL | openai / gpt-4o-mini / 无密钥 | 平台固定获准模型profile和密钥引用；优先同地域华为模型，兼容性待实测 | 可选已验收profile；不是Bank原生字段 |
| ENABLE_BANK_CONFIG_API | true | 不直接公开原生写接口；内部保留，由控制服务白名单转发 | 否 |
| RETAIN_EXTRACTION_MODE | concise | concise；知识库原文场景评估chunks模式 | 可，创建空间时提供用途选项 |
| RETAIN_CHUNK_SIZE | 3000 | 先维持；由模型上下文及抽取测试决定 | 首期不暴露原始数值 |
| RETAIN_MAX_COMPLETION_TOKENS | 64000 | 不盲目继承，须按所选LLM支持的上限配置并通过chunk/token校验 | 否 |
| STORE_DOCUMENT_TEXT | true | true便于溯源；客户选项需明确不可恢复影响 | 空间管理员可控 |
| ENABLE_OBSERVATIONS / ENABLE_AUTO_CONSOLIDATION | true / true | 默认保留主产品能力；提供省成本关闭选项与预算保护 | 可，产品解释为自动整理 |
| RETAIN_MISSION / RETAIN_CUSTOM_INSTRUCTIONS / OBSERVATIONS_MISSION / REFLECT_MISSION | 清单中的原生默认 | 受控长度，禁止当成权限边界 | 空间管理员可配 |
| RECALL_MAX_TOKENS（内部刷新检索） | 2048；HTTP RecallRequest.max_tokens默认4096 | 两者分开配置；云层另设每请求上限，Bank参数不是HTTP硬上限 | 产品分档，统一上限由服务层执行 |
| RERANKER_MAX_CANDIDATES | 300 | 先维持，质量/时延测量后调；不可宣称改小必定不降质 | 否 |
| AUDIT_LOG_ENABLED | false | 平台审计必开；客户无权关闭平台审计 | 否 |
| LLM_TRACE_ENABLED / RETENTION_DAYS | true / 1 | 生产默认关闭原始模型内容追踪或受控短期开启；指标计量独立保留 | 否 |
| TEXT_SEARCH_EXTENSION_NATIVE_LANGUAGE | english | 不宣称已解决中文全文召回；保持已支持扩展，中文检索单独验收 | 否 |
| MCP_ENABLED | true | 只公开网关鉴权后的MCP端点，按角色限制工具 | 客户选接入方式，不能修改平台鉴权 |

注意：输出语言 `llm_output_language` 是服务级字段，**当前不在51项Bank白名单中**；清单的产品分类仅表示可提供产品入口的建议，不代表能原样转发Bank config。首期可用受控mission指令约束，若要严格每Bank语言字段，需要新增适配及测试。审计开关虽属于原生Bank白名单，云产品也不应让客户关闭平台审计。

参数配置需要版本化：`service_profile_version`固定上游commit、镜像摘要、模型名称/版本/维度/前缀、配置摘要。改Embedding不能仅改MODEL环境变量后继续读旧向量；应重建索引/重算向量并完成切换验收。此项是开发约束，尚未实现。

## 模型调用链与成本

| 路径 | 模型工作 | 次数为何不固定 |
|---|---|---|
| Retain | 抽取LLM、生成事实/片段Embedding；图像内容可涉及VLM | 分块数量、抽取模式、每批文本、重试改变请求数；不能按“一条写入一次LLM”计费 |
| Recall | 查询Embedding、PG多路检索、候选重排；rrf无需神经重排模型 | Embedding批次、候选数、不同query分组、reranker类型决定请求数 |
| Reflect | 多轮LLM，可调用记忆查询工具 | 工具循环会触发额外recall与模型调用，不能只计算最终回答token |
| Consolidation / Mental Model刷新 | 归纳LLM、相关记忆召回、生成新内容及向量 | 后台任务也有费用；写入返回后仍可能继续产生模型用量 |

源码：`engine/retain/orchestrator.py:1262`写入向量；`engine/memory_engine.py:9224`查询向量、`:9810`重排；`engine/search/reranking.py:418`成对打分；`engine/reflect/agent.py:839`跟踪LLM调用；`config.py:1896`reflect迭代上限10、`:1909`最大上下文100000、`:1910`wall timeout300秒。它们是上限配置而非每次实际用量。

远程Embedding不是生成式LLM，不会为了每个输入生成长段自然语言，但仍处理输入token并可能按token计费；写入事实和后续更新会再产生向量请求。MaaS总时延包括网络、排队、推理、序列化与重试；本地则消耗自有CPU/GPU和内存。不能仅凭“远程”断言成本高或慢，必须在相同质量目标下记录请求数、token、p50/p95、失败重试和单次任务成本。

## 真实本地实验

[脚本](../scripts/models_local.py)、[结构化结果](../evidence/models-local.json)、[日志](../evidence/models-local.log)。主服务配置未改变，独立测试进程和临时loopback端口，真实模型执行退出码0。

- ONNX e5：384维，6篇中文合成数据库故障资料、6个问题，人工指定对应文档；仅向量top1命中 **4/6**。
- FlashRank `ms-marco-TinyBERT-L-2-v2`：真实本地CPU推理，36组query/document打分，top1命中 **3/6**。它是用于验证本地可运行性的英文小模型，不推荐作为中文生产模型，也不能据此推出“rerank整体降低准确率”。
- 用同一已加载模型建立测试HTTP接口，Hindsight的 `RemoteTEIEmbeddings` 和 `RemoteTEICrossEncoder` 实际发起HTTP请求：与进程内模型的向量、分数最大绝对误差均为 **0**。实际HTTP不是mock分数，但服务是本轮自建TEI协议测试包装，**不是验证了正式TEI服务器或MaaS**。
- HTTP记录：Embedding初始化额外GET /info、POST /embed探测维度；6篇文档与6个问题分2批；Rerank按6个不同query发送6次请求，每次6文档。说明批处理与分组影响请求数。
- 仅单次暖机样本，时延保存在JSON；不用于容量、SLA或云端性能结论。6条样本不是标准benchmark，不能声称产品召回率66.7%。
- 初次专属测试venv装入tokenizers0.23.2与现有transformers要求冲突，固定0.22.2解决；测试HTTP包装首次漏将float32转JSON float，修正包装后通过。保留失败日志；均未改Hindsight代码或主服务依赖。

## 华为MaaS接入状态

官方文档核查（2026-10-04）：[API概览](https://support.huaweicloud.com/api-maas/api-maas-0002.html)提供Chat OpenAI兼容接口、向量化与重排。

- [Embedding](https://support.huaweicloud.com/model-call-maas/model-call-027.html)：`/v1/embeddings`，Bearer API Key，OpenAI SDK示例；文档列BGE-M3并提到Qwen3-Embedding-8B自定义接入点；明确该功能仅支持西南-贵阳一。文档参数表对input类型写法与示例不一致，以真实请求验证为准。
- [Rerank](https://support.huaweicloud.com/model-call-maas/model-call-028.html)：`/v1/rerank`，query/documents/model，返回results[index,relevance_score]及usage；同样有地域限制。不能因为Chat兼容就认定rerank兼容现有provider。
- Hindsight已提供本地ST/ONNX与远程TEI/OpenAI等Embedding，以及本地ST/FlashRank/Jina-MLX与远程TEI/Cohere等Rerank。源码 `engine/embeddings.py:2155`、`engine/cross_encoder.py:2240`附近工厂分支可核对。
- 建议LLM优先使用符合客户部署区域的华为模型；必须验证结构化输出、工具调用、流式响应、超时、重试、token计量和中文任务质量。外部模型只作为客户明确选择且区域允许的方案。
- **没有MaaS凭据，本轮没有华为真实调用结果，不能给生产模型选择盖“验证通过”章。** 本地模型已验证可用，是开发/接口联调基线；云端正式模型选型是上线前必须完成的验证任务。

## 补充：真实Bank配置HTTP验证

[22项HTTP结果](../evidence/parameters-http-results.json)与[脚本](../scripts/parameters_http.py)，退出码0，覆盖两租户同名Bank隔离、允许字段读写、static/未知/错误类型拒绝、混合PATCH原子拒绝、None清除单个覆盖及配置不泄漏静态凭据。补充了前述单测缺少真实PG集成的部分覆盖，不等于14项skip全部补齐。Bank更新接口是PATCH，不是PUT。

原生HTTP Recall请求未传max_tokens时默认4096，已用运行时Request模型和实际OpenAPI验证；http.py:6144显式传入engine。Bank recall_max_tokens=2048主要用于内部刷新检索，不限制显式HTTP请求，不能当成云端客户配额。见[证据](../evidence/parameters-http-recall-default.json)。

当前pg0 fsync=off（由主代理核验），本轮数据库检查证明事务逻辑和隔离，不能作为断电持久性证明。正式环境必须在fsync=on及目标RDS配置下演练故障。

## 运行账号无DDL权限：重要失败边界

`RUN_MIGRATIONS_ON_STARTUP`原生默认true；`MIGRATION_DATABASE_URL`可提供迁移连接，但不能据此认为所有运行期DDL都已分离。

[权限实验](../scripts/parameters_privilege.py)在新schema预迁移，然后创建非superuser/非owner运行role，仅授schema USAGE、表DML与序列使用权限，确认schema CREATE=false。设置迁移启动开关false，单key认证明确指向该schema，不使用租户首次请求迁移。API健康200，但原生建Bank返回500 `must be owner of table memory_units`；Bank未创建，后续Recall404。[结果](../evidence/parameters-privilege-results.json)、[脱敏日志](../evidence/parameters-privilege-api.log)。脚本退出0代表证据采集完成，JSON的all_http_checks_passed=false才是业务判定。

原因是 `retain/bank_utils.py:406` 建Bank时同步建每Bank向量索引，`engine/db/ops_postgresql.py:1259`使用普通CREATE INDEX。启动迁移开关关闭不会关闭这个运行期DDL。

因此D04必须落实“特权开通/索引维护身份”和“普通DML运行身份”的实际分工；插件首次建Bank应由云控制层开通job处理，不能直接透传到无DDL运行账号。迁移连接分离只是其中一部分；删除Bank/索引重建/维护DDL还需逐项验证。此实验未修改Hindsight代码，也不证明RDS权限认证。

补充可行路径：[先特权预建Bank再降权运行](../scripts/parameters_privilege_prebank.py)的4步真实HTTP均200：管理身份预建Bank→停止管理API→同schema DML-only运行身份配置chunks→同步写入→Recall返回ZX8932合成内容（前两步合计为一个precreate检查）。[结果](../evidence/parameters-privilege-prebank.json)。说明已预建Bank的该条读写链路可无DDL运行，不代表全部接口和后台维护均可无DDL。

两个脚本都退出0，第一轮业务失败、第二轮4检查业务通过必须分别呈现。临时8894服务已停止，额外启动的Cell B PG也停止；新schema/role保留审阅，随机密码只存私有目录，证据日志已脱敏。
