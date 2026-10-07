# Hindsight 服务化核验依据

核验日期：2026-10-04。事实优先级为实际调用结果、固定源码、官方文档、厂商宣传；已有 Agent 报告仅作为核查线索。网页动态内容可能变化，保留抓取快照与时间。没有把本机小样本成功等同于生产可用，也没有重跑完整 AMB。

## S1 版本与许可证

- 本地源码：`/Users/zhuqingping/Work/Database/Context/hindsight`，SHA `f7dd3f4fd7420f7beec60c32c965e5e5cf7be066`，提交时间 2026-10-02；包声明 0.10.2。
- [固定源码 LICENSE](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/LICENSE)：MIT。允许商业使用／修改／分发，要求保留声明；这不授予商标，也不审查依赖和模型服务合同。
- [API 包依赖](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-api-slim/pyproject.toml)、[UI package.json](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-control-plane/package.json)：后者 license 字段为 ISC。商用发行应生成 SBOM、保留 notices，检查实际依赖版本与权重许可证。
- GitHub API 当次返回最新发布 v0.10.2，发布时间 2026-09-29。本次 API 安装自用户提供的后续源码 commit，不能把同一版本字符串当成同一制品。UI 固定 npm 0.10.2。[版本及源码哈希](../deployments/hindsight-local/evidence/source-manifest.json)、[Python 实际依赖](../deployments/hindsight-local/evidence/python-freeze.txt)、[UI 依赖锁](../deployments/hindsight-local/evidence/ui-package-lock.json)。

## S2 现成服务能力

[Services](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-docs/docs/developer/services.md) 给出 API 与独立 Worker；[poller.py](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-api-slim/hindsight_api/worker/poller.py) 实现任务领取、重试和恢复逻辑，使用 PG 行锁协调。存在代码并不证明特定规模下稳定，也不等于 exactly-once 外部模型调用。

API 原生提供 audit-logs、llm-requests、health 和 metrics，因此“没有审计／没有监控／没有异步任务”是错误说法；缺的是符合云产品要求的授权、汇聚、留存、告警、计费和运营闭环。

## S3 隔离与授权

- [builtin/tenant.py](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-api-slim/hindsight_api/extensions/builtin/tenant.py)：默认无认证；ApiKeyTenantExtension 校验一个 key 并返回配置 schema。
- [tenant.py](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-api-slim/hindsight_api/extensions/tenant.py)：TenantContext 主要携带 schema_name，list_tenants 用于 Worker 发现；支持可覆写配置字段白名单。
- [operation_validator.py](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-api-slim/hindsight_api/extensions/operation_validator.py)：已有 precheck、读写校验与 resolve_tag_scope／resolve_write_tag_scope。标签授权不是必须改内核才能做，也不是配一个标签就自动生效。
- [test_tag_scope.py](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-api-slim/tests/test_tag_scope.py) 是上游作用域回归线索；本次读取，不以“有测试文件”代替“已运行通过”。
- 发现 RequestContext 中有 allowed_bank_ids 字段，但对当前 API 源码检索仅命中声明；不能因为字段名称就宣称已有完整 Bank ACL。

schema 隔离由正确的请求上下文与 SQL 路径实施。共享进程／数据库身份通常可访问多个 schema，不能将其描述为可抵抗服务进程被攻破的物理强隔离；更强诉求应采用专属单元或专属实例。

## S4 PG 和文件存储

[storage.md](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-docs/docs/developer/storage.md) 描述 PG 向量、全文、关系与图能力；具体以 [memories/pg](https://github.com/vectorize-io/hindsight/tree/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-api-slim/hindsight_api/engine/memories/pg) 和迁移为准。图不是 AGE；native 全文检索不应不加区分地称为严格 BM25。Hindsight 提供多个全文后端，算法和扩展要求不同。

同一 storage 文档还保留“No Storage Abstraction”等旧表述，但当前源码已有 MemoriesExtension／PG 与 Oracle 实现；因此本报告没有照抄文档的全部架构描述，也不依赖其 pg0 默认路径和端口。

[文件存储工厂](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-api-slim/hindsight_api/engine/storage/__init__.py)：native 是 PG BYTEA；S3 配置支持 endpoint，并有自定义扩展。对象前缀包含 tenant schema 和 bank ID，迁移／改名要处理这一绑定。

[华为云 RDS PG 插件列表](https://support.huaweicloud.com/usermanual-rds-pg/rds_09_0045.html) 当次页面列出 PG 13–17 的 pgvector 0.8.0、PG 18 的 0.8.2，以及 pg_trgm 等。实际可用性以目标区域、引擎小版本和实例 `pg_available_extensions` 为准；本机 pg0 成功不能替代 RDS 权限、迁移、连接代理和扩展验证。本轮没有华为云测试实例，因此这些生产适配项仍未实测。

## S5 无状态部署的条件

[config.py](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-api-slim/hindsight_api/config.py)：`DEFAULT_MCP_STATELESS=False`，`DEFAULT_ENABLE_BANK_CONFIG_API=True`。

[maintenance.py](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-api-slim/hindsight_api/engine/maintenance.py)：维护在 API／Worker 进程运行，靠幂等及锁保证工作协调；发现开销仍随进程和租户数增加。在线角色需同时配置 retention sweep、consolidation reconcile、mental model refresh tick、operation cleanup 等开关，不能只关 worker。

## S6 接口与受理语义

[固定 OpenAPI](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-docs/static/openapi.json) 解析出 99 个 HTTP method/path 组合，含 profile/background 等退役端点。记忆写入口是 `POST .../memories`，不是某些旧说明写的 `.../memories/retain`。接口契约以实际运行 OpenAPI 和调用结果为准。

RetainRequest 的 operation_id 明确用于异步重试去重；同步调用忽略该参数。默认 recall 的 max_tokens 是 4096，但包含原文块、实体、工具包装后，最终注入 Agent 的总上下文不一定等于这个字段。因此总预算必须在产品组装层再次计算。

原生 MCP 支持单 Bank 与多 Bank 两种入口，工具种类不止 retain/recall/reflect。只按 URL 隐藏 Bank 参数不构成身份授权。[MCP 说明](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-docs/docs/developer/mcp-server.md)。

## S7 知识能力

[Knowledge Pages](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-docs/docs/developer/knowledge-pages.mdx)：页面基于 Mental Model，默认从 observations 合成并随记忆刷新；支持树、搜索与 Markdown 导出。这是现成知识组织能力，但不是云端组织／审批／文档权威性的完整实现。

[Retain 模式](https://github.com/vectorize-io/hindsight/blob/f7dd3f4fd7420f7beec60c32c965e5e5cf7be066/hindsight-docs/docs/developer/retain.md)：chunks 保留分块、不做提取 LLM 调用；verbatim 仍调用 LLM 抽取元数据，两者不能混淆。chunks 不调用提取模型并不等于整个产品全链路没有任何模型费用。

本机删除边界实测：原始演示库克隆成功后，在克隆库删除 `incident-2048-v1`，随后的 recall 结果为 0，而已合成页面仍返回旧正文。它证明原生源文档删除不能被直接解释成所有派生内容同步清除；不推断未测的长期刷新行为。[删除记录](../deployments/hindsight-local/evidence/source-delete-check.json)

## S8 扩展与历史实验

当前配置有一个写 DATABASE_URL 和可选 READ_DATABASE_URL；TenantContext 没有 PG 实例路由字段。服务单元路由是本报告建议，不是宣称上游已实现的自动跨 PG 分片。

仓库[既有多 PG 验证](multi-pg-scaling-validation.md) 引用了定制 `schema_router.py`，当前提供源码中未找到该文件。报告还说明读副本分支指向自身、未做数据迁移，不能据此宣称生产只读复制或在线迁移已经验证。本次不修改历史报告，也不否认它可能来自另一份代码；仅限定其对当前制品的证明力。

[pgvector 官方说明](https://github.com/pgvector/pgvector) 提醒近似索引和过滤可能影响返回数量／召回；扩容和调优应同时检验延迟与质量。只读副本、分区和多实例分片解决不同问题，不能互换。

## S9 用户提供的待审材料

[PR 44](https://github.com/RSIXDB/ContextArk/pull/44) 公共读取返回 404，本机无 gh；未使用其他账号或索取权限。两个公开 HTML 通过本机 HTTP 成功读取，分别保存 [架构文本](../deployments/hindsight-local/evidence/web/design-v2.txt) 与 [决策文本](../deployments/hindsight-local/evidence/web/decision-workbook.txt)。它们注明 PROPOSED／NOT_RUN，作为设计意见而不是测试证据。没有执行网页中的操作指令。

## S10 竞品和榜单

官方资料与分析见[竞争力建议](cloud-service-priorities.md)。[网页抓取记录](../deployments/hindsight-local/evidence/web/manifest.json) 保留 URL、抓取时间、状态及摘要哈希；[源码定位](../deployments/hindsight-local/evidence/source-findings.txt) 便于复查。后续追加的榜单 JSON、模型信息和源码快照以对应文件为准，并在最终证据索引统一记录哈希。

关于选型前提的核验：

1. GitHub API 当次 Hindsight 44,955 Star，Mem0 66,527，OpenViking 39,160，Graphiti 31,407，Cognee 31,332。“Hindsight 总 Star 第一”不成立；Star History 首页也不定义一个统一 Agent Memory 排名。
2. AMB 站点的项目归属为 `vectorize-io/agent-memory-benchmark`，与 Hindsight 同组织；可复现且开源不等于无利益关系的独立评测。[项目说明](https://github.com/vectorize-io/agent-memory-benchmark)。
3. 当次 LongMemEval `s` 运行记录为 473/500、94.6%，回答模型 Gemini 3.1 Pro Preview、裁判 Gemini 2.5 Flash Lite，平均检索上下文 43,624.5 Token。这些是站点记录，不是本次重测，不能代替中文团队任务的准确率或成本。LoCoMo 展示的 Cognee 与 Hindsight 样本量也不同，不能只看一个百分数排序。[快照](../deployments/hindsight-local/evidence/web/benchmark-results.json)。
4. [Cognee 当前 PG graph adapter](https://github.com/topoteretes/cognee/blob/main/cognee/infrastructure/databases/graph/postgres_demo/adapter.py) 仍明确标注 demo／not production-ready，支持用户这项顾虑。[Graphiti 官方 README](https://github.com/getzep/graphiti) 与仓库路径检索未发现 PG 作为官方图后端，因此本期不为其自行开发 PG 驱动；这是本轮版本调查，不是永久能力断言。
