# Huawei ContextDB Service Develop

## 1. 阅读范围

本文保留本机进程/模块说明，并补充本轮服务化开发问题的结论。参数和上游实现以本地源码 `f7dd3f4fd7420f7beec60c32c965e5e5cf7be066` 为基线；建议配置和产品设计不等于已实现能力。

| 问题 | 结论位置 |
|---|---|
| 核心进程与职责 | §2 |
| 全量参数、云默认、客户配置 | §3及完整CSV/JSON |
| 完整测试与流水线 | §4及实际测试报告 |
| 四客户端端到端 | §5及真实客户端证据 |
| API Key与简化接入 | §6 |
| Embedding/Rerank/LLM | §7 |
| 差异化、HLD/LLD、开发计划 | §8及两份配套文档 |

## 2. Hindsight 核心进程与模块

本节仅说明 Hindsight 的进程组成、模块职责和调用关系，不涉及华为云服务化方案。依据本机部署及源码 `f7dd3f4fd7420f7beec60c32c965e5e5cf7be066` 核查；以下 PID 是核查时的快照，重启后会变化。

### 2.1 本机实际运行的进程

当前采用非容器部署：**API 与 Worker 合并运行，Web UI 和 PostgreSQL 独立运行。** 逻辑组件数量不等于操作系统进程数量。

| 组件 | 本机进程与端口 | 提供的服务 |
|---|---|---|
| API + 内置 Worker | Python，PID `53586`，端口 `8888` | HTTP API、MCP、记忆引擎和后台任务处理 |
| Web UI | Node 启动器 PID `18210`；Next.js 服务 PID `18213`，端口 `9999` | 浏览器管理界面，调用 API 展示和管理数据 |
| PostgreSQL | 主进程 PID `53645`，端口 `55432`；另有多个子进程 | 业务数据存储、检索、任务队列及运行状态 |

```text
浏览器 → Web UI :9999 ─┐
                      ↓
Agent / SDK / MCP → Python API :8888
                    ├─ HTTP / MCP 请求处理
                    ├─ 记忆引擎
                    ├─ 内置 Worker：后台异步任务
                    └─ 本地 Embedding 模型
                           │
                           ├─ PostgreSQL :55432
                           └─ 远端 GPT 服务
```

### 2.2 API 与记忆引擎

API 是客户端入口，同时执行实际业务逻辑，不只是请求转发：

- 接收 Retain（保存记忆）、Recall（检索记忆）、Reflect（基于记忆生成回答）请求。
- 管理 Bank、文档、记忆等对象，提供任务状态查询。
- 提供 MCP 工具接口、健康检查及 API 文档。
- 调用记忆引擎，完成检索编排、向量生成、结果合并及必要的模型调用。

记忆引擎是 Python 内部模块，不是单独的服务进程。Recall、Reflect 的请求处理不必经过后台任务队列，不能将 API 理解为“只接单，全部计算交给 Worker”。

源码默认 HTTP worker 数为 1，本机也只有一个 API Python 进程。[默认配置](../../hindsight/hindsight-api-slim/hindsight_api/config.py)

### 2.3 Worker：内置后台任务与独立进程

Worker 负责异步写入、批量处理、记忆整合、Mental Model 刷新等任务，并更新任务状态、处理失败与重试。

默认启用内置 Worker：API 在同一个 Python 进程中，通过 `asyncio.create_task(poller.run())` 启动后台轮询。因此 `ps` 中不会看到额外的 `hindsight-worker` 进程。[启动实现](../../hindsight/hindsight-api-slim/hindsight_api/api/http.py)

```text
任务写入 PG 的 async_operations 表
                ↓
Worker 从 PG 领取待处理任务
                ↓
调用模型、处理内容、写入结果
                ↓
更新 PG 中的任务状态
```

本机设置 2 个并发槽位，是任务并发额度，不代表两个进程；上游该版本默认槽位为 10。任务机制使用 PG，不要求额外启动 Redis、Kafka 或 RabbitMQ。[任务后端](../../hindsight/hindsight-api-slim/hindsight_api/engine/task_backend.py)

两个容易混淆的名称：

| 名称 | 含义 |
|---|---|
| Uvicorn / HTTP worker | 处理 HTTP 请求的服务器进程 |
| Hindsight Worker | 从数据库领取并执行后台任务的组件，可内置或独立运行 |

Hindsight 也支持独立进程模式：API 设置 `HINDSIGHT_API_WORKER_ENABLED=false`，另行启动 `hindsight-worker`。API 与独立 Worker 连接同一业务数据库；Worker 自带健康检查和指标接口。这是上游支持的另一种运行方式，本机当前未采用。[独立 Worker 入口](../../hindsight/hindsight-api-slim/hindsight_api/worker/main.py)

本轮进一步实测了独立API/Worker模式：独立schema、API端口8892、Worker端口8893，12项检查通过。API关闭内置Worker后任务保持pending；独立Worker启动后完成；Worker停止时API仍能Recall；重启Worker后积压任务完成，健康与指标可读。测试进程已停止，原演示服务未改变。[脚本](../deployments/hindsight-local/round2/scripts/split_worker_probe.py)、[结果](../deployments/hindsight-local/round2/evidence/split-worker-probe.json)。该测试不覆盖执行中模型调用被强杀或PG断电。

### 2.4 PostgreSQL：独立实例及其子进程

本机 PG 是真正的独立 PostgreSQL 实例。`pg0` 负责本地实例的安装、启动和管理，不代表 PG 数据库引擎嵌入 Python 进程。

| PG 进程 | 职责 |
|---|---|
| 主进程 | 接收连接、管理子进程 |
| 连接后端进程 | 执行 API / Worker 发来的 SQL |
| WAL writer | 写入 WAL |
| Checkpointer、background writer | 检查点及脏页写回 |
| Autovacuum launcher 及按需启动的 worker | 自动清理、统计信息维护 |
| IO worker、logger 等 | 异步 IO、日志等辅助工作 |

这些 PG 后台进程与 Hindsight Worker 无关。数据库连接数变化时，PG 连接后端进程数量也会变化。

PG 保存文档、记忆、向量、关联关系以及任务运行状态。运行状态与临时内存状态的区别如下：

| 状态 | 保存位置 |
|---|---|
| 任务状态、任务参数、领取者、领取时间、重试次数、错误信息等 | PG 的 `async_operations` 表 |
| 正在执行的 Python 协程、并发计数、进程内锁 | Worker 所在进程的内存 |

任务字段有实际数据库迁移定义，完成和失败状态通过 SQL 更新。[字段迁移](../../hindsight/hindsight-api-slim/hindsight_api/alembic/versions/l7g8h9i0j1k2_add_worker_columns.py)、[任务状态更新](../../hindsight/hindsight-api-slim/hindsight_api/worker/poller.py)

### 2.5 Web UI 与模型模块

| 模块 | 本机形态 | 是否有独立服务进程 |
|---|---|---|
| Web UI | Next.js，展示 Bank、文档、记忆与任务等 | 有；Agent 直接调用 API 不需要经过 UI |
| Embedding | Python 进程中加载 ONNX `multilingual-e5-small` | 没有独立模型服务；底层可使用计算线程 |
| Rerank | 本次采用 RRF | 没有独立 CrossEncoder 服务 |
| LLM | 使用本机登录凭据调用远端 GPT | 本机没有 GPT 推理进程 |

上表描述本机实际配置，不代表 Embedding 必须本地运行，或所有部署都使用相同模型。API 与 Worker 按业务需要调用模型；模型本地加载还是远程调用取决于配置。

包名 `hindsight-control-plane` 在本机对应 Web 管理 UI，不能据此认为还有一个独立的租户、计费或资源调度服务。

### 2.6 本机查看方式

在调研仓库根目录执行：

```bash
# 查看本次 API / UI 状态
python3 deployments/hindsight-local/scripts/service.py status

# 查看三个服务入口的监听进程
lsof -nP -iTCP:8888 -iTCP:9999 -iTCP:55432 -sTCP:LISTEN

# 查看进程与父进程；机器上的其他项目可能也有同名进程
ps -axo pid,ppid,comm | rg 'python|postgres|node|next-server|hindsight'
```

完整启动说明、部署配置及验证记录参见 [Hindsight 本地体验与验收](../deployments/hindsight-local/README.md)。

## 3. 参数配置：平台持有底层参数，客户选择受控能力

**结论：不能直接把 Hindsight 的所有配置项开放给客户。** 当前源码有493个 `HindsightConfig` 字段、493个ENV常量（两者并非一一对应），另有动态参数族；只有51个字段可按租户/Bank覆盖。模型名、provider、base_url、密钥和PG连接不在这51项中。仓库部分说明与当前代码不一致，以运行时清单、源码及HTTP验证为准。

完整字段、类型、原生默认值、环境变量、Bank可覆盖性及管理分类见 [参数CSV](../deployments/hindsight-local/round2/evidence/parameters-inventory.csv)、[参数JSON](../deployments/hindsight-local/round2/evidence/parameters-inventory.json)、[ENV清单](../deployments/hindsight-local/round2/evidence/parameters-env-inventory.csv)、[动态参数族](../deployments/hindsight-local/round2/evidence/parameters-dynamic-families.json)。这些是锁定commit的API服务端清单；UI参数另见下文，不包括任意第三方插件的所有参数。

### 3.1 云配置起点

以下“云配置”是**建议的开发基线，不是生产压测最优值**；模型、连接数、任务并发随目标规格验收后定版。未显式调整的字段保留锁定版本默认值。

| 参数/类别 | 当前原生默认 | 云配置起点 | 客户权限 |
|---|---|---|---|
| `DATABASE_URL` | 本地pg0路径 | 受管PG；生产启用fsync和既定复制策略 | 不开放 |
| `DB_POOL_MIN_SIZE/MAX_SIZE` | 5/100，每池 | 小规格2/10起测；总量按所有API/Worker进程计算 | 平台运维 |
| `WORKER_ENABLED` | true | API false，独立Worker执行 | 不开放 |
| `WORKER_MAX_SLOTS` / `WORKER_CONSOLIDATION_RESERVED_SLOTS` | 10/2 | 小规格2/1起测，不能把全部槽位留给整合 | 平台运维 |
| `LLM_MAX_CONCURRENT` | 32，每进程范围 | 小规格2起测，另限制Cell/租户总并发 | 平台运维 |
| LLM / Embedding / Reranker provider与model | 详见清单 | 固定经验证的模型profile；一个Cell固定向量空间 | 客户仅选择已验收套餐，不传URL/密钥 |
| `ENABLE_BANK_CONFIG_API` | true | 内部保留，外部只开放字段白名单 | 禁止任意原生配置写入 |
| `RETAIN_EXTRACTION_MODE` | concise | 记忆concise；规范KB chunks | 以“记忆/知识库用途”呈现 |
| `ENABLE_OBSERVATIONS` / `ENABLE_AUTO_CONSOLIDATION` | true/true | 记忆按预算提供自动整理；已审核KB关闭自动整理 | 管理员选择受限产品选项 |
| `RETAIN_CHUNK_SIZE` | 3000 | 先保持，再按模型上下文验证 | 首期隐藏 |
| `RETAIN_MAX_COMPLETION_TOKENS` | 64000 | 必须按拟上线LLM支持上限校验，不直接照搬 | 平台固定 |
| HTTP Recall `max_tokens` | **4096** | 产品可默认2048、设置最大档位，属于新增限制 | 客户选档，不能突破上限 |
| Bank `recall_max_tokens` | **2048** | 内部刷新等使用；不能当HTTP请求硬上限 | 首期隐藏 |
| `RERANKER_MAX_CANDIDATES` | 300 | 质量/时延测量后调整 | 平台运维 |
| `STORE_DOCUMENT_TEXT` | true | 首期保留来源；关闭前明确溯源损失 | 空间管理员受控设置 |
| mission / custom instructions | 各操作默认说明 | 长度限制、模板化；不是授权边界 | 空间管理员 |
| `AUDIT_LOG_ENABLED` | false | 平台审计开启且不可被客户关闭 | 不开放关闭平台审计 |
| `LLM_TRACE_ENABLED` / retention | true / 1天 | 关闭原文trace或仅受控诊断；用量指标独立保留 | 平台管理 |
| 中文全文相关配置 | native english | 不宣称中文分词已解决；单独验收精确词与错误码 | 平台固定 |

API关闭Worker并不等于关闭所有MaintenanceLoop。部署清单应明确谁执行整合发现、保留清理和向量索引维护，不能把维护全部关闭；API角色按源码支持的维护间隔配置停止对应周期任务，Worker/专责进程保留维护职责。

客户最少需要配置 endpoint、API key、Bank；高级选项仅包括用途、自动整理、任务说明、召回预算、允许的保留/来源选项。输出语言 `llm_output_language` 不是当前Bank白名单字段，不可直接包装成原生逐库配置。更换Embedding需要重算向量和切换验收，不是重启时换一个MODEL值。

### 3.2 UI与数据库权限：两项需要单独处理的配置

UI的 `HINDSIGHT_CP_DATAPLANE_API_URL` / `HINDSIGHT_CP_DATAPLANE_API_KEY` 是服务端共用的后端地址/凭据；`HINDSIGHT_CP_ACCESS_KEY` 是可选共享登录口令，不是客户IAM或逐Bank授权。本机现有UI未设访问口令，匿名读取Bank列表返回200；隔离UI设置口令后，匿名401、错误口令401、正确登录及cookie访问200，共5项检查通过。[本机边界](../deployments/hindsight-local/round2/evidence/ui-local-auth-boundary.json)、[受控UI验证](../deployments/hindsight-local/round2/evidence/ui-access-probe.json)。云上原生UI先用于内部运维；客户控制台需通过产品服务传递成员身份并校验权限，不能直接共享管理员后端key。

`RUN_MIGRATIONS_ON_STARTUP=false` 和独立 `MIGRATION_DATABASE_URL` **不足以分离全部DDL权限**。真实PG预迁移后，仅有DML权限的运行账号能健康启动，但创建Bank返回500：`must be owner of table memory_units`。原因是建Bank同步创建向量索引。改为特权身份预建Bank后，降权运行的配置、chunks写入和Recall均200，合成事实召回成功。[失败证据](../deployments/hindsight-local/round2/evidence/parameters-privilege-results.json)、[预建后验证](../deployments/hindsight-local/round2/evidence/parameters-privilege-prebank.json)。因此首期由受控开通job完成Bank/索引创建；删除、索引维护和完整后台链路的最小权限仍需逐项验收，不能据这条读写链路宣称全部接口已支持无DDL运行。

UI源码：[共享后端客户端](../../hindsight/hindsight-control-plane/src/lib/hindsight-client.ts)、[访问中间件](../../hindsight/hindsight-control-plane/src/middleware.ts)。建索引源码和复验命令见参数报告。

### 3.3 验证结果

- 配置与模型接口专项：354 passed、14 skipped；包括类型、覆盖、provider接口、重试等，非完整回归。跳过项及环境搭建失败日志均保留。[JUnit](../deployments/hindsight-local/round2/evidence/parameters-tests.xml)
- 真实Cell B HTTP/PG配置：22项检查通过，覆盖允许字段写读、错误类型、未知字段、模型/provider/key拒绝、非法混合更新不部分生效、清除覆盖及跨租户同名Bank隔离。[结果](../deployments/hindsight-local/round2/evidence/parameters-http-results.json)
- Recall默认值通过运行时模型与live OpenAPI确认：HTTP 4096，Bank字段2048；两者作用域不同。[证据](../deployments/hindsight-local/round2/evidence/parameters-http-recall-default.json)

**权限故障实测：** 真实 `ConfigResolver.update_bank_config` 在权限扩展抛出 `TimeoutError/RuntimeError` 时仍继续写配置；返回空允许集合或抛 `ValueError` 才拒绝。使用记录后端fixture复现，未修改上游。云扩展必须把权限依赖故障转为明确拒绝，外层也要白名单校验。[复现结果](../deployments/hindsight-local/round2/evidence/parameters-failopen.json)

详细证据和复验脚本见 [参数与模型报告](../deployments/hindsight-local/round2/reports/parameters-models.md)。

## 4. 开发测试与流水线：分层验证，不能用一个命令证明完备

**结论：复用上游测试，但必须另外补云产品权限、可靠受理、删除、恢复和真实客户端验收。** “不带LLM标记”的测试也可能调用真实模hhh型；CI job因无secret跳过不能算功能通过。

| 流水线层 | 主要入口 | 什么时候执行 |
|---|---|---|
| 静态检查 | `ruff check hindsight_api`、`ty check hindsight_api` | 每PR |
| 单元/PG机制 | `hindsight-api-slim/tests` | 每PR，按依赖分类执行 |
| 系统黑盒 | `hindsight-system-tests/tests` | 每PR完整执行；真实API/PG/SDK，模型是stub |
| 真模型行为 | API tests的`hs_llm_core`、`hs_llm_mat` | 夜间及模型/提示词变更；选获准provider矩阵 |
| SDK/UI/插件 | 对应包tests、build、接口覆盖检查 | 改动触发；公开承诺的客户端必须覆盖 |
| 质量评测 | `hindsight-system-evals`、固定领域金标 | 候选发布；记录模型、提示词、预算与原始结果 |
| 升级/恢复 | migration、upgrade tests、备份恢复 | 每次上游升级和生产候选 |
| 云层契约 | 租户/Bank ACL、key撤销、幂等、额度、发布/删除 | 产品新增功能必须纳入每PR/夜间门禁 |

最小可复现系统测试命令（在**隔离源码副本**中执行）：

```bash
(cd hindsight-api-slim && uv sync --frozen --extra embedded-db)
(cd hindsight-system-tests && uv sync --frozen)
(cd hindsight-system-tests && PYTEST_ADDOPTS='' uv run pytest tests -v --junitxml=system.xml)
```

系统suite会启动独立PG，不能改指向演示库或客户库。API suite读取`.env`可能覆盖环境变量；测试环境需独立。真LLM、S3/Docker、各厂商凭据、不同平台依赖按上游CI分别准备，不以填入假key绕过依赖。

本轮关键结果如下；各行存在重叠，不能相加成覆盖总数。

| 验证范围 | 实际结果 | 结论边界 |
|---|---|---|
| API过滤suite，补齐本地模型依赖 | **10477通过、2失败、185跳过、5预期失败** | 26分06秒，非全绿；显式排除的外部依赖见报告 |
| 两个失败所在完整文件，独立PG串行重跑 | 24通过 | 不抹去全套失败；跨事件循环锁及列表共享数据需目标CI复核 |
| 系统黑盒 | 321通过/1跳过；跳过ONNX例随后单独通过 | 真实HTTP/PG/SDK；主要模型是stub |
| UI完整单元测试 | UTC环境286通过；构建与i18n通过 | 上海时区首次有1失败；未做完整浏览器E2E |
| Python SDK选定文件 | 73通过；TS构建通过 | 不是全部语言SDK集成通过 |
| API静态检查 | ruff、ty通过 | 不代替运行验证 |

各阶段完整入口、前置和上游CI位置见 [流水线执行手册](../deployments/hindsight-local/round2/reports/tests-ci-runbook.md)，包含API、真模型、SDK/UI、质量评测及升级；未执行阶段明确标记，不能仅复制命令就视为验收。

本轮执行明细、命令、退出码、失败/skip原因和流水线草案见 [测试报告](../deployments/hindsight-local/round2/reports/tests.md)。当前环境为macOS arm64/Python3.12；不能代替目标Linux/Python3.11或云镜像验收。**本轮没有证明“完整功能全部通过”，未通过项必须进入修复或不支持范围。**

## 5. Claude、Codex、Hermes、OpenClaw 的端到端验收

**结论：Hindsight 原生支持远程服务，不需要为了远程接入重做客户端。** 但支持某个插件不等于该客户端在当前版本和模型下已经验收。

按三层记录证据：①插件单元测试；②真实协议/HTTP/MCP；③真实客户端在独立会话中自动写入和召回。只有第三层能证明用户期待的会话连续性；显式让模型调用MCP不等于自动记忆。

统一验收步骤：

1. 临时项目与新Bank，设置服务URL/key，不修改用户全局配置。
2. 第一会话输入独特合成事实，通过实际hook或工具保存；确认PG operation完成。
3. 启动第二个独立会话，不把答案带入prompt，验证取回事实与来源。
4. 区分自动注入和显式工具调用；记录真实CLI版本、插件版本、模型、Bank和操作ID。
5. 再测错误key、跨Bank权限、服务超时、重复结束hook、后台写入失败与客户端升级。

特别注意：新版统一 `coding-agents` 的自动注入默认包含Reflect/Knowledge Pages，并非必然每轮Recall；云端若采用经济档，需客户端与服务共同配置，不能仅在服务端假设省掉Reflect。Hermes的observation筛选、异步召回选项会影响刚写入数据何时可见。关闭自动整理时，应选择可召回world/experience的客户端配置，不能继续只查observation。

本轮真实自动链结果（均为独特合成事实、两次独立会话、实际模型调用）：

| 客户端 | 实际版本/模型 | 实测结果与限制 |
|---|---|---|
| Codex | CLI 0.160.0；GPT-6.1-sol；coding-agents 0.8.0 | Stop自动保存+新会话自动注入通过；`--ephemeral`缺transcript时hook退出0但不保存，不能用该模式验收自动记忆 |
| Claude Code | 2.1.289；既有兼容服务GLM-5.3-flash；coding-agents 0.8.0 | 自动保存/召回通过；是Claude Code宿主测试，不是Anthropic官方模型验收 |
| Hermes | 真AIAgent runtime `af90026...`；插件1.2.1；Python3.14；GPT-6.1-sol | 独立进程自动链通过；未测完整交互CLI/Desktop/消息渠道 |
| OpenClaw | 2026.9.8；Node24.16；插件0.13.0；GLM-5.3-flash | 真CLI+Gateway自动链通过；需`allowConversationAccess=true`及稳定session-key；合成webchat身份，未测真实消息渠道 |

插件普通测试另有：coding-agents 1288/1288、OpenClaw 389/389、Hermes 38/38通过。其中Hermes插件单测使用fake core，与上表真实runtime证据分开。

**四条链均连接本机HTTP Hindsight和PG；不等于华为云公网TLS/IAM/跨地域已通过。**OpenClaw回报cost=0源于自定义模型未填价格，不代表调用免费。

本轮实际客户端记录与未通过项见 [客户端报告](../deployments/hindsight-local/round2/reports/clients.md)。四客户端分别判定，不因一个通过就给其他三个盖章。不能借用mock Hermes core的测试结果证明真实Hermes会话通过。

## 6. API Key：一个客户凭据足够，身份与权限由服务端解析

**结论：客户只需 endpoint + key + Bank。key不需要包含全部租户资料，更不能包含PG或模型密钥。** Hindsight默认租户扩展不鉴权；内置单key扩展把所有有效请求映射到同一schema；static-keys扩展可把不同key映射到不同schema，但不等于完整的客户凭据生命周期和团队Bank权限系统。

拟采用 `ctx_<key_id>_<随机secret>`：使用256-bit安全随机secret，创建时完整显示一次；服务端保存摘要、workspace、subject、有效期和撤销状态。key可以包含非敏感的格式版本或查找ID，授权不能相信客户能自行改写的tenant字段。JWT可携带签名声明，但普通签名JWT不隐藏内容，并会增加撤权/过期管理；首期不必为了少传tenant_id改成JWT。

服务流程：管理身份创建key → 客户复制配置 → 每请求校验key → 查主体与Bank授权 → 服务端选择Cell/schema → 调Hindsight。轮换发新key，确认客户切换后撤旧key；删除成员需撤销其主体授权，而不是只删页面上的key显示。原生内部服务凭据与客户key分开。

本地原型验证：**27项检查通过**，真实PG+Hindsight HTTP覆盖有效/伪造/过期/撤销key、同名跨租户Bank、团队只读与私有库、伪造tenant头、轮换、不存明文key。[结果](../deployments/hindsight-local/round2/evidence/auth-probe.json)、[脚本](../deployments/hindsight-local/round2/scripts/auth_probe.py)。它不是生产IAM/KMS网关，未证明产品MCP或分布式缓存撤权。另有10项原生MCP检查通过：真实MCP SDK在Cell B中验证缺失/错误key拒绝、有效key工具发现及同名Bank跨租户召回隔离；仍不等于云产品的按成员MCP授权已实现。[MCP证据](../deployments/hindsight-local/round2/evidence/mcp-auth-probe.json)

源码依据：[默认/单key扩展](../../hindsight/hindsight-api-slim/hindsight_api/extensions/builtin/tenant.py)、[static-keys扩展](../../hindsight/hindsight-extensions/static-keys-tenant/hindsight_ext_static_keys_tenant/extension.py)。官方Hindsight Cloud也已有API key创建、过期与撤销体验，因此“一键发key”是基础体验，不是独有竞争力。[官方说明](https://docs.hindsight.vectorize.io/api-integration/)

## 7. 模型交互：支持本地和远程，效果由具体模型与配置决定

### 7.1 模块与调用位置

| 路径 | 模型工作 | 主要源码 |
|---|---|---|
| Retain | LLM抽取事实；内容/事实Embedding；图像可涉及VLM | `engine/retain/orchestrator.py`、`fact_extraction.py` |
| Recall | query Embedding、PG多路检索、候选重排 | `memory_engine.py`、`search/reranking.py` |
| Reflect | LLM多轮推理，可能继续调用Recall | `engine/reflect/agent.py` |
| 整合/知识刷新 | 后台LLM归纳、检索及新内容向量化 | Worker任务与对应engine路径 |
| provider适配 | LLM、Embedding、Rerank各自的本地/远端实现 | `llm_wrapper.py`、`embeddings.py`、`cross_encoder.py` |

请求数取决于分块、批次、候选量、工具循环与重试，不能按“一次Retain等于一次LLM”估算费用。后台整理可能在前台写入返回后继续消耗模型。

### 7.2 逐问题结论

| 问题 | 已确认结论 | 选择建议及验证边界 |
|---|---|---|
| Embedding必须本地吗？ | 不必须；支持本地SentenceTransformers/ONNX及远端TEI/OpenAI等 | 先固定模型/维度，再选择本地或MaaS部署；分别测网络、排队、批次和成本 |
| MaaS是否必然Token多、慢？ | 无此结论。Embedding处理输入token，不生成长文本；实际计费依供应商 | 统计写入/更新/query的全部向量请求与重试；没有MaaS实测不能报延迟/费用优劣 |
| Rerank必须本地吗？ | 不必须；有本地CrossEncoder/FlashRank/Jina-MLX和远端provider | 是否开启由领域质量增益、候选数、延迟与费用共同决定 |
| LLM用华为还是外部？ | 原生有多provider；本轮没有华为MaaS真实调用证据 | 优先验证符合区域要求的华为模型；外部仅在客户授权且允许数据处理的范围使用 |
| 本机实际用什么？ | Embedding：多语言e5-small ONNX，384维；Rerank：RRF；LLM：远端GPT-5.6-Luna | RRF是排序融合，不是神经重排模型；GPT使用本机凭据但不在本机推理 |
| 本地比MaaS准确吗？ | 部署位置本身不决定准确率 | 必须固定权重、版本、前缀、截断、精度和候选集才能比较；不同模型不能混成“本地/云”结论 |

2026-10-04 23:06按用户成本要求切换运行时：`gpt-5.6-luna`、reasoning=low、LLM并发1、自动整合默认关闭。启动最小模型调用成功，API/UI健康；现有8个Bank的有效自动整合配置均为false。Embedding/RRF不消耗远端模型Token。并发限制不是总Token/费用硬上限，Retain/Reflect及手动后台任务仍可能调用模型。[运行证据](../deployments/hindsight-local/round2/evidence/runtime-cost-control.json)。前述四客户端完整验证使用切换前模型，不能据此宣称已对Luna重跑全部质量测试；为控制消耗，本轮不再重复真实模型验收。

### 7.3 本地实测与华为接入边界

真实本地ONNX Embedding与FlashRank Rerank都执行成功。同一模型通过本轮自建的loopback TEI协议HTTP包装调用，与进程内输出的向量/重排分数最大误差均为0。证明该受控条件下两种调用方式可保持结果一致；**不等于正式TEI服务或华为MaaS验收通过**。[实验JSON](../deployments/hindsight-local/round2/evidence/models-local.json)

6条中文合成数据库样本中，向量top1命中4/6，英文TinyBERT重排3/6。样本太小且模型用途不同，仅用于暴露模型选择影响；不能称为产品准确率，也不能推断Rerank普遍无益。没有执行完整AMB或竞品对照。

华为官方已有Chat OpenAI兼容接口、Embedding和Rerank接口，但向量化/重排文档当前注明仅支持西南-贵阳一。不能把Chat兼容推导为所有模型能力/区域都兼容。[API概览](https://support.huaweicloud.com/api-maas/api-maas-0002.html)、[Embedding](https://support.huaweicloud.com/model-call-maas/model-call-027.html)、[Rerank](https://support.huaweicloud.com/model-call-maas/model-call-028.html)

上线前必须在实际区域和模型下验证：结构化输出、工具调用、中文样例、向量维度/批次/截断、rerank响应映射、超时429/重试、用量统计与成本。当前没有MaaS凭据，以上不能标成“本地已验证通过”。

## 8. 差异化与开发落地

**修正此前定位：远程支持Coding Agent、跨会话记忆、插件接入本身都是Hindsight已有能力，不能算华为云差异化。** 也不能把PG、向量或简单托管列为客户可感知的独有优势。

本期值得验证的增量是：

1. **团队可控的知识复用：** 私有记忆→带来源草稿→审核发布→团队召回→撤权/撤回，完整权限和可见性有验收证据。
2. **数据库领域的正确性：** 按引擎/版本/适用条件组织复盘，避免把某次修复参数当通用规范；积累客户认可的领域金标。
3. **可解释的费用与失败：** 看得到后台任务、调用量、来源和失败原因，限制重复写入与不必要生成；节省比例需同任务同预算实测。

这些是待验证的产品价值假设，不是已经领先竞品的事实。具体差异、指标和取舍见 [竞争力文档](cloud-service-priorities.md)。

可开工设计已补至 [架构文档§9–11](cloud-service-architecture.md#9-可开工的设计基线本轮新增)：包含部署模块、最小控制表、公开接口合同、key/内部身份、幂等受理、知识发布/删除状态机、模型/费用、双Cell扩展与恢复；以及12个任务包、负责人角色、160人日估算、40人日缓冲、8周里程碑和发布门禁。参考控制DDL已在PG中执行，21项检查通过。[DDL](../deployments/hindsight-local/round2/scripts/control_schema_reference.sql)、[结果](../deployments/hindsight-local/round2/evidence/control-schema-results.json)。DDL仍是开发参考，生产角色、RLS和迁移流程尚未验收。

本轮额外完成两项设计验证：原生Retain与控制PG幂等账本11项通过；发布/撤回PG状态机14项通过。后者模拟索引完成通知，没有实现完整知识服务。[幂等证据](../deployments/hindsight-local/round2/evidence/idempotency-probe.json)、[发布合同证据](../deployments/hindsight-local/round2/evidence/publication-probe.json)

**持久性边界：** 两套本地pg0实例均实测 `fsync=off`，因此当前PG事务和进程重启检查不证明断电耐久性；上线必须在目标RDS配置和复制策略下验证。[PG参数](../deployments/hindsight-local/round2/evidence/pg-runtime.json)

### 8.1 开发第一周先解决的四件事

1. 固定上游SHA、目标Linux镜像和模型profile，接入分层流水线，保留失败与skip清单。
2. 实现身份/Bank白名单及授权依赖故障拒绝；原生配置扩展异常放行问题必须有负向测试。
3. 用目标RDS验证“特权开通Bank/索引→普通身份读写→维护/删除”完整权限矩阵；不能只验健康接口。
4. 验证获准区域的MaaS三类接口，再确定客户套餐与并发/预算。没有实际模型验收前，不承诺质量、成本或时延。

团队知识发布、客户UI和云MCP属于待开发的产品能力；当前通过的是局部合同与原生客户端链路。首期上线按架构文档门禁判定，不能把本轮研究报告当生产认证。

## 9. 本轮交付与复验

次日先打开本机管理页 `http://127.0.0.1:9999`，API健康检查 `http://127.0.0.1:8888/health`；演示API/Worker、UI与PG保留运行。测试创建了独立合成Bank及schema，未修改上游源码或原有客户配置。复验入口与环境限制见 [本轮README](../deployments/hindsight-local/round2/README.md)。


- 参数与模型：[报告](../deployments/hindsight-local/round2/reports/parameters-models.md)，含完整清单、专项测试、真实本地模型实验。
- 流水线：[报告](../deployments/hindsight-local/round2/reports/tests.md)，保留失败、skip与环境修正。
- 客户端：[报告](../deployments/hindsight-local/round2/reports/clients.md)，区分mock、协议测试和真实会话。
- API Key/幂等/发布：[验证脚本目录](../deployments/hindsight-local/round2/scripts)，结果见各JSON。
- 实施：[修正版High Level Design](contextdb-high-level-design.md)、[HLD/LLD与任务板](cloud-service-architecture.md)、[差异化取舍](cloud-service-priorities.md)。

每个结论按“源码确认、实际测试、设计建议、未验证依赖”区分。不能把拟开发的云产品设计写成已上线能力，也不能因缺少云资源凭据而用本地模拟替代生产验收。

交付检查：[源码/服务健康/文档链接/脚本语法](../deployments/hindsight-local/round2/evidence/delivery-checks.json)、[文件摘要清单](../deployments/hindsight-local/round2/evidence/delivery-manifest.json)。这些是研究验证结果，不是8小时持续负载或生产可用性测试。

## 10. 如何参与ContextArk与AgentStratum：负责质量和交付控制面

2026-10-07对两个私有仓做了只读检查：研究规划库[ContextArk](https://github.com/RSIXDB/ContextArk)基线`ba328844c5f145ee725182b192d718045553ac0c`，产品代码库[agentstratum](https://github.com/RSIXDB/agentstratum)基线`73021428307ba29b436fac987349aef1e40b912d`。本轮没有修改或推送这两个仓库。

### 10.1 现状判断

ContextArk已经具备较强的Agent协作治理：有`AGENTS.md`、证据等级、ADR、Issue/PR约定、单写入者规则和文档校验。AgentStratum也固定了Hindsight上游版本、依赖和任务写入边界，并已经存在K01/K02、A01、L01、Gateway与规划类测试。

当前主要缺口是**产品仓的自动化验收面明显小于已有代码和测试资产**：

- AgentStratum只有一个GitHub Actions工作流`.github/workflows/k01.yml`；
- 仓库有22个`test_*.py`文件，静态统计372个测试函数，但PR流水线只执行`tests/contextdb/test_kernel.py`；
- 复跑当前PR命令得到`35 passed / 1 deselected`，ruff和ty通过；这是当前门禁通过，不代表其余21个测试文件通过；
- 默认`pytest testpaths`只包含`tests/contextdb`，不会自动收集`tests/a01`、`tests/l01`、`tests/planning`和`tests/stage1/gateway`；
- 直接扩大收集会遇到真实PG DSN、固定Hindsight安装、L01输入目录等前置条件，说明需要测试分类和分层runner，不能简单把所有目录拼成一个命令；
- AgentStratum README明确写明当前没有分支保护，LongMemEval流水线和真实成绩仍为`NOT_RUN`。

这不是“现有代码不可用”的结论，而是：当前很多验证存在于任务记录或专项实跑中，尚未转化成每次PR自动、可复现、可追责的产品门禁。

### 10.2 推荐承担的角色

建议以“**AgentStratum质量、数据库可靠性与发布门禁负责人**”参与，而不是与现有Agent争抢业务实现。负责定义：

- 什么状态才算功能完成、可以合并、可以发布；
- AI生成改动是否符合公共API、数据状态机和架构合同；
- PG事务、权限、并发、升级、备份和恢复是否正确；
- 哪些命令和证据必须重放，哪些失败/skip可以接受；
- 真实模型质量、延迟和成本是否相对固定基线发生回归。

实现Agent不能同时成为唯一验收者。验收测试应来自产品合同和故障模型，关键路径由不同人员/Agent独立复核。

### 10.3 建议工作包

#### Q01：测试资产分类与PR快速门禁

给所有测试标记运行层次：

| 标记 | 含义 | PR策略 |
|---|---|---|
| `unit` | 无网络、数据库和模型的纯逻辑测试 | 每PR必跑 |
| `contract` | API、数据结构、状态机和错误合同 | 每PR必跑 |
| `integration_pg` | 需要独立PostgreSQL | 每PR或合并队列必跑 |
| `integration_obs` | 对象存储协议和故障 | 模拟协议每PR；真实OBS夜间/发布 |
| `native_hindsight` | 需要固定Hindsight源码或wheel | 固定版本构建后运行 |
| `e2e` | Gateway/API/Worker/PG完整链路 | 合并队列及夜间 |
| `cloud` | 需要华为云RDS/OBS/MaaS/IAM | 受控夜间和发布门禁 |
| `benchmark` | 质量、延迟、Token和费用 | 小样本PR、完整夜间 |

第一条流水线应完成：lint/type → wheel构建及干净安装 → 全部无外部依赖的unit/contract → 测试收集检查 → JUnit和失败证据上传。禁止未登记的skip，测试收集失败必须阻断。

#### Q02：真实PG可靠性门禁

利用数据库团队优势重点验证：初始化/重复初始化、schema升级、owner/API/Worker/Migrator权限、跨租户与跨Bank拒绝、幂等冲突、提交成功但响应丢失、Worker领取后崩溃、`FOR UPDATE SKIP LOCKED`竞争、连接耗尽、短暂断连、主备切换、撤权和删除后的旧任务。PR使用临时PG验证事务与权限；夜间运行API+独立Worker+PG故障恢复。

#### Q03：产品端到端验收

第一批场景至少覆盖：创建Bank、异步Retain、Operation完成、Recall命中、重复请求不重复写、API/Worker分别重启、跨租户拒绝、API Key撤销、Bank删除、OBS故障下纯文本Recall、模型故障及重试。维护“产品能力→API→数据状态→测试→证据”矩阵，AI PR必须声明影响了哪些合同和用例。

#### Q04：合并和发布门禁

配置GitHub Ruleset：禁止直接推main、必须PR、至少一位非作者评审、Fast CI和PG Integration必过、禁止force push；共享schema、Gateway、Worker和Hindsight适配层配置`CODEOWNERS`。保留当前subtree导入不能squash/rebase的约束。

#### Q05：质量评测与上游演进

把现有LongMemEval方案实现为固定数据、Hindsight commit、模型、Prompt和参数的可重放流水线，同时记录准确率、逐题结果、p50/p95、Token和费用。上游升级另建门禁：固定旧版数据→升级→读取/写入/删除→回滚或恢复，并检查vendor差异、依赖漏洞、许可证、SBOM和镜像来源。

推荐先创建三个独立Issue：Q01测试资产与分类、Q02 PR Fast Gate、Q03 PG可靠性门禁。前三项不需要先改业务核心，可以在独立分支完成，减少与正在工作的Agent冲突。

## 11. Hindsight测试资产、上游流水线和本机覆盖

### 11.1 统计口径

基线为Hindsight `f7dd3f4fd7420f7beec60c32c965e5e5cf7be066`（0.10.2）。以下数字分为三类：

1. **pytest collected**：由测试框架实际展开参数化后的准确用例数；
2. **源码文件/静态函数**：只用于盘点未安装的子项目，参数化后实际用例通常更多；
3. **本机实跑**：有命令、JUnit和退出码的结果。

不同套件会复用相同代码路径，本机也有失败后的重跑，不能把各行相加为“唯一测试总数”或“总通过率”。`xfail`、`skip`、缺凭据和`NOT_RUN`都不算验证通过。

### 11.2 上游测试集总览

| 测试集 | 源码规模/准确分母 | 覆盖内容 | 上游入口 | 本机状态 |
|---|---:|---|---|---|
| API核心机制 | 605个Python测试文件；**10,871 pytest收集项** | Retain/Recall/Reflect、配置、PG、Worker、任务、迁移、存储、模型provider、错误路径 | `hindsight-api-slim/tests`；CI `test-api`三shard | 已运行非LLM选择集，未全绿 |
| API真实LLM Core | 包含在10,871项中，marker=`hs_llm_core` | 核心事实抽取和提示词行为 | `test-api-llm-core` | 未按上游完整套件运行 |
| API真实LLM Acceptance Matrix | 包含在10,871项中，marker=`hs_llm_mat` | 多provider最低接受标准、独立judge | `test-api-llm-acceptance` | 未运行 |
| Oracle API | 包含在API测试文件中，marker=`oracle` | Oracle后端 | `test-api-oracle` | 未运行，不属于首期PG产品必需能力 |
| 系统黑盒 | 68个文件；**322项** | 真实API进程、PG、Python SDK；stub LLM/Embedding/Rerank | `hindsight-system-tests/tests`，CI `test-system` | 321通过/1跳过；跳过项随后单独通过 |
| 系统质量评测 | 1个目标测试文件+8个eval文件；静态23个测试函数 | 知识页收敛、Reflect回答、语言/忠实度、成本、来源优先级 | `hindsight-system-evals/tests`和`evals`；`perf-test.yml` | 未运行标准评测 |
| Python SDK | 32个文件；**241项可收集** | 同步/异步参数映射、重试、附件、Bank/KB/Recall/Reflect | CI `test-python-client`及Oracle变体 | 选定12文件73项通过；完整241项未跑 |
| TypeScript SDK | 20个测试文件，静态约134个`test/it`定义 | TS API映射、运行时行为、Deno | `test-typescript-client`、Oracle、Deno | build通过；完整测试未跑 |
| Rust CLI | 4个Rust测试文件，静态49个`#[test]` | CLI参数、profile、错误面和集成 | `test-rust-cli` | 未运行 |
| Rust客户端 | Cargo内单独测试入口 | Rust SDK | `test-rust-client` | 未运行，本轮未做准确收集 |
| Go客户端 | 8个`*_test.go`文件，静态8个顶层Test | Bank、Memory、Document、Operation等API | `test-go-client` | 未运行 |
| Control Plane UI | 39个TS测试文件；**286项实跑** | UI组件、状态与时间显示 | `build-control-plane`、npm test/build/i18n | UTC下286通过；build、i18n通过；无浏览器E2E |
| Hindsight Embed | 10个文件，静态231个测试函数 | 本地Embedding daemon、profile、锁、HTTP探测、控制页 | `test-embed`及Windows变体 | 未运行完整套件；系统ONNX路径已单测 |
| 租户扩展 | static-keys与Supabase各2文件；static-keys准确50项 | API Key、tenant/schema解析和扩展加载 | 两个extension CI job | static-keys 50通过；Supabase未跑 |
| 集成冒烟 | 3个文件，静态9个函数 | base path、Hermes embedded、MCP E2E | `test-integration` | 未按该套件运行 |
| 客户端/框架插件 | 约48个测试目录；154个Python+158个JS/TS测试文件 | Claude Code、Codex、Cursor、OpenClaw、Hermes、Aider、LangGraph等 | `test.yml`中每插件独立job | 本轮只做了四客户端专项验证；不能视为全部插件suite通过 |
| Coding Agents公共包 | 81个TS测试文件，静态约1,209个`test/it`定义 | hooks、配置、传输、多个coding agent共享逻辑 | `test-coding-agents`及少量显式E2E | 本轮未执行其完整suite |
| OpenClaw插件 | 20个TS测试文件，静态约410个`test/it`定义 | 插件、hook、协议和集成 | build、unit、integration job | 做过协议/真实客户端专项验证；未复跑完整上游suite |
| 聚合安装包 | `hindsight-all` 5个Python测试文件；`hindsight-all-npm` 2个TS测试文件 | 全量Python/NPM安装入口和聚合导出 | `test-hindsight-all`、`build-hindsight-all-npm` | 未运行完整suite |
| Interfig与Agent SDK工具 | Interfig 4个TS测试文件；Agent SDK工具1个TS测试文件 | 图形协议及Agent SDK工具 | `test-interfig`、`test-hindsight-agent-sdk` | 未运行 |
| 文档示例与独立启动 | 动态扫描文档代码和启动脚本 | 文档代码可执行性、standalone启动 | `test-doc-examples`、`test-standalone-start-script` | 未运行 |
| Dev工具与生成物 | 9个测试文件，静态58个函数 | coverage清单、生成物、发布注册、性能fixture | `test-dev`、generated/OpenAPI/coverage checks | SDK/CLI覆盖检查通过；完整dev suite未跑 |
| 历史升级 | 1个文件；**3项可收集** | v0.3.0→HEAD的memory、document、bank profile保存 | `test-upgrade` | 未运行 |
| Windows smoke | 独立workflow | Windows安装、API/SDK等冒烟 | `windows-smoke.yml` | 本机macOS未运行 |
| 性能/AMB | 动态数据集用例，不能用源码函数数表示 | LongMemEval/LoCoMo、效果、延迟和费用 | `perf-test.yml` | 未运行 |
| 安全/发布 | 非功能用例计数 | 安全扫描、镜像签名、构建来源证明、release集成 | `security-scan.yml`、`sign-images.yml`、release workflows | 本轮未执行云发布链 |

按统一文件名规则扫描，整个Hindsight仓库有约**1,124个Python/JS/TS测试源文件**；该数字不含Rust、Go以及命名不匹配的脚本，也不是测试用例数。上游`test.yml`准确包含**100个job**（包括条件检测、build、test、兼容性检查和汇总），说明“运行API pytest”只是完整上游验证的一部分。

### 11.3 本机已运行结果

| 验证 | 分母/本次结果 | 是否可作为通过结论 |
|---|---|---|
| API非LLM过滤集首次运行 | 收集选择10,660项；pytest摘要`8509 passed / 2138 skipped / 4 xfailed / 8 failed / 5 errors` | 否；保留了真实模型、Docker S3、Copilot、代理和CLI捕获问题 |
| API补齐local-ml后的离线运行 | `10477 passed / 185 skipped / 5 xfailed / 2 failed`，无error | 否；大部分机制通过，但仍有并行污染/事件循环问题及明确排除项 |
| API两个残余失败隔离复跑 | 两个节点通过；相关两个完整文件24通过 | 只证明隔离条件通过，不能抹去完整并行suite失败 |
| API核心20文件 | `548 passed / 134 skipped` | 局部通过；skip主要依赖local-ml |
| ruff / ty | 两者exit 0 | 静态检查通过 |
| 系统黑盒 | `321 passed / 1 skipped`；跳过的真实ONNX项单独`1 passed` | 322项在两次运行中均被覆盖；不是一次完整全绿，也不是质量评测 |
| static-keys租户扩展 | `50 passed` | 扩展机制通过；不等于华为IAM/ACL通过 |
| Python SDK选定集 | `73 passed`；完整SDK可收集241项 | 局部通过 |
| UI unit | 上海时区285通过/1失败；UTC重跑`286 passed` | UTC环境通过；暴露时区敏感；没有浏览器E2E |
| TS SDK和UI生产构建 | 两者build exit 0；UI i18n exit 0 | 构建通过，不等于SDK/UI端到端通过 |
| SDK覆盖清单 | Python 67/67、TS 89/89参数；各51个Bank配置 | 清单闭合，不是API实际执行通过 |
| CLI覆盖清单 | 99操作中73实现/26显式跳过；126参数中67覆盖/59跳过 | 清单检查通过，不是所有CLI功能通过 |

按具备准确分母的主要套件看：系统黑盒322/322项在两次运行中都得到通过结果，static-keys 50/50通过，UI 286/286在UTC环境通过；Python SDK只运行73/241项（约30.3%）。API虽然选择运行了10,660/10,871项（约98.1%），但其中存在失败、错误和大量skip，因此不能将98.1%写成通过率；最终local-ml运行的10,477个passed也来自带显式排除条件的第二次运行，不能替代上游完整三shard和真实LLM矩阵。

详细命令、JUnit、首次失败、复跑和清理证据见[测试报告](../deployments/hindsight-local/round2/reports/tests.md)及[CI执行手册](../deployments/hindsight-local/round2/reports/tests-ci-runbook.md)。

### 11.4 尚未完成的验证

- 上游`hs_llm_core`和`hs_llm_mat`完整真实模型矩阵；
- Hindsight System Evals、AMB和竞品同条件质量对照；
- Python SDK完整241项以及TS/Rust/Go SDK完整suite；
- 全部客户端插件原生测试和真实客户端升级回归；
- Supabase扩展、Oracle、Windows和CUDA；
- v0.3.0到当前基线的三项真实升级测试；
- 华为云RDS、OBS、IAM、APIG、MaaS真实协议、撤权、故障、恢复、容量和成本；
- API/Worker分进程下的kill、重试、任务恢复和长期积压；
- 浏览器关键任务E2E、压力测试和8小时以上稳定性测试。

因此，当前可以确认的是：Hindsight拥有规模较大、分层较全的上游测试资产，本机已经验证核心API机制、系统黑盒、租户扩展、部分SDK和UI；**不能确认“全部10,871个API用例通过”，也不能确认全部SDK、插件、真实模型和华为云服务层已经通过。**
