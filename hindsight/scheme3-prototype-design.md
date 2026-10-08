# ContextDB 方案 3 原型设计

日期：2026-10-08
状态：PARTIAL（T01-T08 PASS；T09 真实模型 Recall 唯一标识检查 FAIL）

## 1. 目标和证据口径

本原型验证“Gateway 选择固定 Data Cell，Cell 内共享 Hindsight API/Worker/PG”的短期架构，不评价模型质量。证据按以下标签记录：

- **当前源码确认**：直接核对 Hindsight `a77c1f3412a7b82f36588dffce1a8d7480e99cc7`。
- **本机重新验证**：2026-10-08 本轮实际启动、请求或数据库查询。
- **历史证据**：来自较早本机实验，只用于选择复验路径。
- **推断**：由源码或运行现象推导、尚未直接验证。
- **已过时**：历史结论与当前源码或本轮环境不一致。

运行基线为 Hindsight `0.10.2`、分支 `prototype/scheme3-cell-poc-20261008`、独立 worktree：

`/Users/zhuqingping/Work/Database/Context/.local/worktrees/hindsight-scheme3-prototype`

原始 checkout 在开始时为干净的 `main@a77c1f3412a7b82f36588dffce1a8d7480e99cc7`。

## 2. High Level Design

```text
Client
  |
Gateway 127.0.0.1:18080
  |-- tenant1, tenant2 -> Cell1
  |      |-- API1 :18101  API2 :18102
  |      |-- Worker1 :18111  Worker2 :18112
  |      `-- PostgreSQL container :55434
  `-- tenant3 -> Cell2
         |-- API1 :18201  API2 :18202
         |-- Worker1 :18211  Worker2 :18212
         `-- PostgreSQL container :55435

All API/Worker processes -> loopback TEI-compatible embedding service :18081
```

Cell1 是共享型：tenant1、tenant2 共用两套 API、两套 Worker 和同一 PostgreSQL 容器，但分别使用 `scheme3_tenant1`、`scheme3_tenant2` schema。Cell2 是独享型：只注册 tenant3，使用独立 PostgreSQL 容器和 `scheme3_tenant3` schema。共享与独享只改变 placement 和 Cell 资源归属，不改变 Hindsight 入口或原型代码。

PostgreSQL 镜像固定为 `pgvector/pgvector:0.8.1-pg17@sha256:3e8b3adfd27b5707128f60956f62a793c3c9326ea8cfaf0eab7adccb5d700b21`。两个容器使用不同命名卷、端口和进程，因此本轮目标是物理本机实例隔离，而不是同实例双数据库替代。容器仅绑定 loopback，并为本机原型使用 trust 认证；这不是生产安全配置。

## 3. Low Level Design

### 3.1 Gateway

Gateway 是原型目录中的独立 aiohttp 服务，不导入 `hindsight_api` 或任何 Hindsight 内部模块。请求流程：

1. 读取 `Authorization: Bearer <key>`，计算 SHA-256；
2. 用哈希在 SQLite 查找 `tenant_id`，再经 `placements` 找到 `cell_id`；
3. 在该 Cell 启用的 API backend 中用进程内、每 Cell 独立的 `asyncio.Lock` 保护 round-robin 计数器；
4. 删除客户端传入的 `X-ContextDB-*` 等内部诊断头；
5. 原样转发方法、路径、查询参数、请求体以及必要头；
6. 响应增加 `X-ContextDB-Cell`、`X-ContextDB-Upstream` 和 request ID；
7. JSONL 日志只记录 request_id、tenant_id、cell_id、backend_id、状态码和耗时，不记录 Key 或 Authorization。

GET/HEAD 在连接失败时可以选择同 Cell 的下一健康节点重试一次并短暂摘除失败节点；POST/PUT/PATCH/DELETE 不做隐藏重试。`/health` 和 `/prototype/routes` 是 Gateway 自身的只读诊断接口，后者只暴露脱敏 placement 与 backend 状态。

### 3.2 SQLite 元数据

SQLite 位于专用运行目录，仅供单 Gateway 原型使用：

- `tenants(tenant_id, service_type)`；
- `cells(cell_id, service_type)`；
- `placements(tenant_id, cell_id)`；
- `api_backends(cell_id, backend_id, base_url, enabled)`；
- `api_keys(key_hash, key_id, tenant_id)`；
- `schemas(tenant_id, schema_name)`。

SQLite 不保存明文 API Key、PostgreSQL 密码、模型凭据或 OBS 凭据。随机测试 Key 明文只写入权限 `0600` 的 `/Users/zhuqingping/Work/Database/Context/.local/runtime/hindsight-scheme3-prototype/secrets/tenant-keys.json`。生产必须替换为高可用元数据库、KMS/Secret 和有版本的配置发布机制。

### 3.3 Hindsight API/Worker

**当前源码确认**：API 和 Worker 使用官方 `hindsight-api`、`hindsight-worker` 入口。API 设置 `HINDSIGHT_API_WORKER_ENABLED=false`；Worker 使用固定 ID `cellN-workerM`。同一 Cell 的 API 和 Worker使用相同：

- `HINDSIGHT_API_DATABASE_URL`；
- `HINDSIGHT_API_TENANT_EXTENSION=hindsight_ext_static_keys_tenant:StaticKeysTenantExtension`；
- `HINDSIGHT_API_TENANT_USERS` 和 `HINDSIGHT_API_TENANT_SCHEMA_PREFIX=scheme3`；
- LLM、Embedding、RRF 和维护开关。

StaticKeysTenantExtension 的 `authenticate()` 将 Bearer Key 映射为 schema，并在首次访问时迁移 schema；`list_tenants()` 返回同一配置中的全部租户。当前 Worker Poller 会对这些 schema 轮询 `async_operations`，通过后端 `claim_tasks()` 使用 `FOR UPDATE SKIP LOCKED` 竞争领取任务。当前提交还把启动恢复放到后台，并用数据库时间边界避免稳定 worker ID 在重启时误回收新领取任务。

异步链路是：

```text
Client -> Gateway -> selected API -> batch_retain parent operation (pending)
                                      |
                           retain child task in tenant schema
                                      |
                         Worker claim (processing, worker_id)
                                      |
                    child completed -> parent completed in PG
```

Gateway 从不调用 Worker。**本机重新验证**：API 返回的 batch 父操作通常对外呈现 `pending -> completed`；Worker 实际领取的 retain 子任务在 PostgreSQL 审计中呈现 `pending -> processing -> completed`。原型用只作用于测试数据库的状态审计触发器保存短暂的 processing 转换，没有修改 Hindsight。

### 3.4 模型配置

第一层（拓扑验证）：

- LLM：Hindsight 内置 `mock`；
- Embedding：原型提供的 `deterministic-test-embedding`，TEI `/info` 和 `/embed` 合同，384 维；
- Rerank：`rrf`；
- 自动 Consolidation 和 reconcile sweep 关闭；Worker LLM 并发 1。

第二层（最小真实模型复验）：

- **本机重新确认的候选 LLM**：当前 Codex CLI 登录有效，端到端调用使用 `gpt-5.6-sol`；Hindsight 使用 `openai-codex`、`low`，只引用 `/Users/zhuqingping/.codex`，不读取或复制认证内容；
- **历史证据并重新检查缓存存在**：ONNX `intfloat/multilingual-e5-small` 快照 `614241f...`，384 维；由 loopback TEI 合同包装一次加载、供多个 Hindsight 进程共享；
- Rerank：RRF；
- 每租户最多 2 次 Retain、2 次 Recall，不执行 Reflect。

真实复验实际使用 `gpt-5.6-sol`、low、ONNX 384 维和 RRF。ONNX 初始化通过复用已有 Hindsight 本地 Python 环境完成；API/Worker 仍运行当前 worktree 源码。两次允许的真实 Retain 均完成，至少一次 tenant1 Recall 请求成功，tenant2 独立 schema 对不存在 Bank 返回 404；最终 tenant1 Recall 响应未包含唯一 marker，因此 T09 为 FAIL，不形成模型效果结论。

## 4. 文件和运行位置

- 原型代码：`prototypes/contextdb-scheme3/**`；
- 运行目录：`/Users/zhuqingping/Work/Database/Context/.local/runtime/hindsight-scheme3-prototype/**`；
- 证据：`/Users/zhuqingping/Work/Database/Context/ContextDB-Research/hindsight/evidence/scheme3-prototype-2026-10-08/**`；
- 文档：本设计、同目录 runbook 和 validation。

启动器为每个进程保存角色、Cell、节点 ID、PID、端口、脱敏命令摘要和日志路径。停止操作只读取本原型 PID 清单并核对进程，不使用 `pkill`/`killall`。容器操作只针对 `contextdb-scheme3-poc-20261008-*` 精确名称。

## 5. 历史材料核对清单

| 历史信息 | 本轮判断 |
|---|---|
| Hindsight 0.10.2 支持 Static Keys schema 多租户 | 当前源码确认；本机重新验证 PASS |
| API 可关闭内置 Worker，独立 `hindsight-worker` 可运行 | 当前源码与 Helm 确认；本机重新验证 4 API/4 Worker PASS |
| API 写 PG operation、多个 Worker 竞争领取 | 当前源码确认；本机 PG 三态审计与两个 Worker claim PASS |
| 历史 LLM 为 `gpt-5.6-luna` | 历史证据；当前 Codex 健康检查实际模型为 `gpt-5.6-sol`，旧值不继承 |
| ONNX multilingual-e5-small 384 维可用 | 历史证据；本机重新验证初始化与真实请求成功 |
| RRF 可避免加载神经 Reranker | 当前源码确认 |
| 旧 Worker 启动恢复行号/时序 | 已过时；当前 `a77c1f...` 为后台恢复实现 |
| ContextArk/AgentStratum 的 Gateway 实现 | 未作为实现输入；完成后只读确认其 Stage1 Gateway 含 session/限流/封闭动作合同，而本原型是完整 Hindsight HTTP 反向代理和 Cell placement，改动边界与目标不同 |

## 6. 实际代码改动边界

新增 14 个可审文件，全部位于 `prototypes/contextdb-scheme3/**`：独立 Gateway、SQLite 元数据、Embedding 包装、进程/容器 supervisor、T01-T09 acceptance、CLI、README 和 3 个单测文件。`hindsight-api-slim/**`、`hindsight-extensions/**`、`helm/**` diff 为空；原始 checkout 保持干净。未复制或导入 ContextArk/AgentStratum 代码。

## 7. 已知生产差距

本原型没有实现组织/成员/账单、复杂 RBAC、生产密钥轮换、分布式 Gateway、配置发布、RDS HA/PITR、OBS、真实 MaaS、审计合规、跨 Cell 迁移、容量治理或性能/SLO。SQLite、loopback trust PostgreSQL 和静态 Key 只适合本机单节点验证。共享 Cell 的资源公平性、故障域容量和长期稳定性也不由本轮功能测试证明。
