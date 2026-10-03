# Cognee / Hindsight / Graphiti 三选一对比分析

华为云 ContextDB 选型，PG/MySQL 强团队，小团队快速上线。

- **Hindsight / Cognee**：本地源码 + 运行容器实证。
- **Graphiti**：本地克隆快照（2026-09-21）+ Cognee eval 中 `graphiti-core==0.17.8` 调用。环境无外网，存在 ≤8 天新鲜度窗口，文末列待复核项。
- 社区数据：Hindsight stars/forks = 41.6k/5.6k（用户校正）；Cognee/Graphiti 来自 2026-09-22 GitHub API 快照。

日期：2026-09-29

---

## 结论

| 维度 | Cognee | Hindsight | Graphiti |
|------|--------|----------|----------|
| 后端 | PG（pgvector+图谱同库） | PG（pgvector，深度依赖 PG 专属能力） | Neo4j，不用 PG |
| PG 集成深度 | 深 | **最深** | 无 |
| 写扩展 | 单 PG；**已有 `tenant_pg_routing` 骨架** | 单 PG，schema 隔离；**无路由骨架，需自建** | — |
| 图谱 | demo-only（官方注释明示非生产） | 生产级邻接表图，融合进 recall | 时序 KG 最强，跑在 Neo4j |
| 多租户/管控 | **数据模型完整**（User/Role/Permission/ACL/Tenant）+ HTTP 端点；OSS 写入路径未打通、缺管理 UI | schema 隔离已生产化；**无 user/role/permission/audit/billing 模型**，仅留扩展钩子 | 仅 `group_id` 分区 |
| 社区 | 30.9k stars，882 测试，100+ 贡献者 | 41.6k stars / 5.6k forks（三者最大） | 31.1k stars |
| 许可证 | Apache-2.0 | MIT | Apache-2.0 |

**给本场景的建议：首期主底座选 Hindsight。**

逻辑链（与证据对应）：

1. **核心能力 Hindsight 全面领先且生产级**。ContextDB 的核心是记忆+检索+图谱+PG 集成+多租户隔离。Hindsight 这五项都是生产级、已实测；Cognee 的图谱是 `postgres_demo`（官方注释明示 demo/非生产），其余几项 Hindsight 也更深。底座该看核心能力，Hindsight 核心齐。

2. **两者都要补管控面，Cognee 并不更省事**。Cognee 有 RBAC 数据模型是纸面优势——OSS 版多租户**写入路径没和租户身份打通**（SDK 默认 `default_user`）、**缺管理 UI**（你自己文档已实测），还是要二次开发打通。Hindsight 缺 RBAC/计费/审计，但留了扩展钩子（`get_tenant_config`/`get_allowed_config`/metering 已埋 tenant_id），是增量补。这一项两者都得投入，不构成选 Cognee 的决定性理由。

3. **关键差异在"要补的是什么性质的工作"**：
   - Cognee 要补**图谱**——这是核心功能改造（动检索核心，高风险）。
   - Hindsight 要补**RBAC/计费/审计/横向扩展**——都是正交增量（不碰记忆/检索核心，低风险，钩子已留）。
   补图谱（高风险核心改造）比补 RBAC（低风险增量）致命得多。

4. **横向扩展验证了 Hindsight 的设计正交性**。Hindsight 横向扩展是正交扩展（一处 backend 选择层、不碰核心），恰恰说明它难的部分都做好了、可补的都是外围增量。Cognee 的横向扩展骨架虽在，但补图谱是核心改造——正交性反过来更差。

5. **社区** Hindsight 最大（41.6k stars），MIT License，Vectorize.io backing。

**唯一可能倾向 Cognee 的场景**：首期确定不需要图谱、先把记忆+向量检索跑起来，且接受上线即半成品（图谱 demo）、后续补图谱承担高风险核心改造。本场景的约束是"快速上线 + PG 强耦合 + 后续增强竞争力"，**Hindsight 更契合**：核心生产级能快速上线，PG 原生契合团队优势，竞争力增强走 PG 上启用 AGE（正交增强图谱，团队强项）。

- **Graphiti**：时序 KG 最强，但强依赖 Neo4j、不用 PG，不符合"PG 强耦合"约束。作为后续时序图谱 adapter 储备，不当首期主底座。

> 结论修正记录：此前版本曾建议"Cognee 为主底座"，依据是"Cognee 管控面省事"。该依据不成立——Cognee OSS 管控写入未打通、缺管理 UI，并不省事；且该判断忽略了 Cognee 图谱 demo-only 是比补 RBAC 更硬的核心短板。按"核心能力生产级 + 可补部分低风险正交"两条标准，Hindsight 优于 Cognee。

---

## Q1~Q5 逐问

### Q1 Hindsight 多租户？
✅ 支持，schema-per-tenant，API key → schema，**本机已实测两租户隔离**（`zhuqingping_hindsight`/`hindsight-mt`）。机制见 `extensions/tenant.py` + `static-keys-tenant/extension.py`。但 stock 镜像默认单租户，多租户扩展需自定义 Dockerfile 叠加（`.deploy-hindsight-mt/` 已示范）。

### Q2/Q3 Hindsight 后端 PG 与横向扩展、PG 支持深度
- PG（pgvector）默认主后端，Oracle 次之，**MySQL 不支持**。
- PG 集成最深：pgvector + pg_trgm + 原生 FTS（或 ParadeDB/pgroonga/vchord）+ JSONB，104 个 Alembic 版本化迁移（可追溯回滚、多租户 schema 并发迁移），asyncpg + pgbouncer 事务模式适配。
- 横向扩展：**读副本一等公民**（`HINDSIGHT_API_READ_DATABASE_URL`）；**无分片/Citus/分区，写路径单节点 PG**。多租户靠 schema 隔离，不是分片。

### Q4 Hindsight 图谱 vs Cognee
✅ Hindsight 优于 Cognee。Hindsight 建真实邻接表图（`memory_links`/`unit_entities`/`entity_cooccurrences`），LLM 抽取实体+因果边，融合进 recall，2 个图 REST 端点，生产代码。Cognee `postgres_demo` 官方注释明示 demo/非生产。**两者都不用 AGE**。

### Q5 Graphiti 对 PG
❌ Neo4j 为主后端，不用 PG、不用 AGE（证据：`graphiti/README.md:631-633` 后端列表 + Cognee eval 中 `graphiti-core==0.17.8` 实际调 Neo4j driver）。时序 KG 最强（边带 `valid_at/invalid_at/expired_at`），但绑死 Neo4j。Apache-2.0，OSS 独立可用，多租户仅 `group_id` 分区无控制面。

### Q6 社区
Hindsight 41.6k stars / 5.6k forks（三者最大，用户校正）；Cognee 30.9k（882 测试、100+ 贡献者，工程细项最厚）；Graphiti 31.1k。三者都有商业公司 backing（Cognee.ai / Vectorize.io / Zep）。

### Q7 综合建议见上文"结论"。

---

## 重点：管控集成工作量对比（Cognee vs Hindsight）

从管控面六个维度逐项对比开发工作量。

### 1. 租户隔离

| | Cognee | Hindsight |
|--|--------|----------|
| 机制 | **database 级**隔离（per-dataset 一个 PG database，`DatasetDatabase` 表登记） | **schema 级**隔离（per-tenant 一个 PG schema） |
| 现状 | 已实现、已验证（你的文档已实证） | 已实现、已验证（本机两租户实测） |
| 工作量 | ≈ 0 | ≈ 0 |

两者隔离都现成。Hindsight schema 隔离粒度更细、Cognee database 隔离更重（物理库级）。**Cognee database 隔离对"按租户分 PG 实例扩展"更天然**——见下。

### 2. 横向扩展（写路径，PG 层面）

| | Cognee | Hindsight |
|--|--------|----------|
| 现状 | **已有 `tenant_pg_routing` 骨架**：`cognee/infrastructure/databases/tenant_pg_routing/{routing,handlers}.py`，`tenant_id → PG instance`（host/port/user/pass/database）路由表，opt-in，未映射租户回退全局 .env | 无路由骨架；schema 隔离在**单 PG 实例内**，schema 不能跨实例 |
| 待做 | 路由表接通 dataset 创建路径 + 管控面写入路由表（骨架已有，主要是接线和 UI） | 加 schema→PG 实例路由 + `_get_backend()` 按 schema 选实例（**集中一处薄改动**）+ per-instance 连接池；迁移/worker 的 per-tenant 遍历加实例维度（同构扩展） |
| 工作量 | 中（骨架在，接通即可） | **中（正交扩展，不碰核心）** |

**估算**：两者相当，Hindsight 约 2~3 人周。关键修正：Hindsight 的 schema 隔离**已把租户做成一等公民**——所有查询 schema-scoped 无跨 schema join（`fq_table` 读 contextvar）、迁移与 worker 已 per-tenant 遍历。加 PG 实例只是在 `_get_backend()` 这一处集中按 schema 选 backend，记忆/检索/图谱核心代码一行不变。Cognee 的 `tenant_pg_routing` 路由层与 Hindsight 这层同构，工作量相当。详见《Hindsight 多 PG 实例横向扩展方案》。

> 此前"Hindsight 是 Cognee 2~3 倍工作量"的评估作废——错把"Cognee 改 `postgres_demo` 核心改造"与"Hindsight 正交扩展"混为一谈。两者性质不同：Cognee 把 demo 图谱改生产级是动检索核心（高风险），Hindsight 加 PG 实例是动连接选择层（低风险正交）。

### 3. 鉴权 / Token

| | Cognee | Hindsight |
|--|--------|----------|
| 现状 | `modules/users/authentication` + `api_key`（`UserApiKey` 表），fastapi-users 栈，有 HTTP 登录/发 token 端点 | `TenantExtension.authenticate()` 钩子；`StaticKeysTenantExtension` 从 env 读 key→schema（加/轮换/吊销 = 改 env 重启）；无 token 发放/轮换/吊销机制 |
| 待做 | 套用即可，按云服务包装 | 自写 DB-backed `TenantExtension`：key 存 PG、支持自助开户/轮换/吊销 |
| 工作量 | 小 | 中 |

### 4. 用户/角色/权限管理

| | Cognee | Hindsight |
|--|--------|----------|
| 现状 | **完整数据模型**：`User/Tenant/Role/Permission/ACL/Principal/UserTenant/UserRole/TenantDefaultPermissions/RoleDefaultPermissions` + `api/v1/{users,permissions}` HTTP 端点 | **无**。无 user/role/permission/ACL 概念，只有 bank（租户内路由键）和 schema |
| 待做 | 套用 + 按 RBAC 需求裁剪 | 从零建 user/role/permission 模型 + 端点 + 在 recall/retain/bank 操作上挂权限检查 |
| 工作量 | 小 | **大** |

这是 Hindsight 最大缺口。Cognee 的 RBAC 是开箱的数据模型；Hindsight 要从无到有设计实现。

### 5. 审计

| | Cognee | Hindsight |
|--|--------|----------|
| 现状 | `api/v1/activity` 端点，有用户活动记录基础 | metering 已埋 `RequestContext.tenant_id`/`api_key_id`（`static-keys extension.py:313-319`），**但无审计表/查询端点** |
| 待做 | 扩展 activity 为完整审计（操作/资源/时间/结果） | 从零建审计表 + 写入点 + 查询端点 |
| 工作量 | 小 | 中 |

### 6. 存储计费

| | Cognee | Hindsight |
|--|--------|----------|
| 现状 | `DatasetDatabase` 表可统计 per-dataset/per-tenant 库与表大小；`shared/usage_logger.py` 有用量埋点 | metering 埋了 tenant_id/api_key_id 归属字段；bank stats 端点可拿记忆条数；**无配额/计费模型** |
| 待做 | 把 dataset/库大小 + usage_logger 聚合成计费指标 + 配额门控 | 从零：建用量采集 + 配额 + 计费，基于已埋的 tenant_id |
| 工作量 | 中 | 中 |

### 工作量汇总

| 维度 | Cognee | Hindsight |
|------|--------|----------|
| 租户隔离 | 0 | 0 |
| 横向扩展 | 中（骨架在） | 中（正交扩展，不碰核心） |
| 鉴权/Token | 小 | 中 |
| 用户/角色/权限 | 小 | **大** |
| 审计 | 小 | 中 |
| 存储计费 | 中 | 中 |
| **合计** | **小~中** | **大** |

**总判断**：管控集成上，**Cognee 开发量显著小于 Hindsight**。核心差距在两块——① 横向扩展（Cognee 已有 `tenant_pg_routing`，Hindsight 从零）；② 用户/角色/权限（Cognee 完整模型，Hindsight 无）。这两块都是云服务化绕不开的硬投入。Hindsight 的优势在检索/图谱/PG 深度集成，但那是能力面，不是管控面。

---

## 重点：Hindsight 后端 PG 横向扩展工作量

你当前 Hindsight 是"单 PG 实例 + schema 隔离记忆库"。要改成"按租户分 PG 实例横向扩展"，对照 Cognee（已有 `tenant_pg_routing`）评估如下。

### 现状
- Hindsight：所有租户 schema 在**同一个 PG 实例**。`memory_engine.py` 的连接池、迁移 fan-out、worker 调度都假设单实例。
- Cognee：`tenant_pg_routing` 表 + handler 已就绪，租户→PG 实例映射可查，未映射租户回退默认实例。

### Hindsight 待做（从零）
1. **路由层**：加 schema_name（或 tenant_id）→ PG 实例映射表/配置；`TenantExtension` 暴露实例信息。
2. **连接管理**：`engine/db/postgresql.py` 从单 asyncpg pool 改为**多实例 pool 池**（每实例独立 pool + 健康检查 + 失败转移）。
3. **迁移 fan-out 跨实例**：`memory_engine.py:5176` 的并发多 schema 迁移要扩展成跨实例并发，且跟踪每个实例的迁移版本。
4. **worker 跨实例调度**：`list_tenants()` 要返回实例信息，poller 跨实例轮询、公平调度。
5. **读副本**：每实例的 `READ_DATABASE_URL` 独立配置。
6. **管控面**：写入路由表、新租户分配 PG 实例的策略（轮询/容量）。

### 估算（修正）
- Cognee：路由骨架已就绪，接通 dataset 路径 + 管控面，约 2~3 人周。
- Hindsight：集中改 `_get_backend()` 按 schema 选实例 + per-instance pool + 迁移/worker 加实例维度，**约 2~3 人周**，与 Cognee 相当。
- **两者工作量相当**（此前"Hindsight 2~3 倍 Cognee"的评估作废）。

### 为什么 Hindsight 不重（修正）
Hindsight 的 schema 隔离已把租户做成一等公民，不是"为单实例设计"：
- **查询全 schema-scoped、无跨 schema join**（`fq_table` 读 contextvar）→ 一个 schema 逻辑等价一个独立库，租户跨实例在 SQL 层天然成立。
- **迁移与 worker 已 per-tenant 遍历** → 加实例维度是同构扩展，非重构。
- **跨租户全局例程已独立**（`fq_routine` 注释自述）→ 设计者已划清单实例全局与 per-tenant 边界。

加 PG 实例的核心改动是**一处集中的 backend 选择层**，记忆/检索/图谱核心代码不变。Cognee 的 `tenant_pg_routing` 路由层与 Hindsight 这层同构，工作量相当。详见《Hindsight 多 PG 实例横向扩展方案》。

---

## 给小团队的落地建议

1. **首期主底座选 Hindsight**：核心能力（记忆/检索/图谱/PG 深度/多租户隔离）全部生产级且已实测，PG 原生契合团队优势，社区最大。难的部分已做好，可补的都是正交增量。
2. **管控面增量补齐（低风险）**：Hindsight 已留扩展钩子——自写 DB-backed `TenantExtension`（key→schema 存 PG，支持自助开户/轮换/吊销）、在 `get_tenant_config()` 加 per-tenant LLM key/配额、基于已埋的 `tenant_id`/`api_key_id` 做审计与计费。都是增量，不碰记忆/检索核心。
3. **横向扩展按需启用（正交）**：单 PG 不满足时，加 schema→PG 实例路由（借鉴 Cognee `tenant_pg_routing` 的 opt-in+回退设计），改动集中在 `_get_backend()` 一处，详见《Hindsight 多 PG 实例横向扩展方案》。
4. **图谱竞争力后续增强**：Hindsight 现有邻接表图已生产级、够首期用；若要更强图谱，在 PG 上启用 **Apache AGE**（PG 原生扩展，契合团队优势）升级为属性图/Cypher，正交增强。借鉴 Graphiti 的时序边模型（事实有效期）。
5. **Graphiti 作后续时序图谱 adapter 储备**：若某场景需要强时序 KG（事实有效期/演化），再评估引入，PG 仍做主存储。
6. **Cognee 作为工程参考**：其 RBAC 数据模型（User/Role/Permission/ACL）、`tenant_pg_routing` 路由设计、多租户测试用例可反哺 Hindsight 管控面二次开发，不必整包引入。

一句话：**核心能力生产级、可补部分低风险正交，选 Hindsight**。图谱后续在 PG 上用 AGE 正交增强（团队强项），管控面增量补齐，都不动检索核心。

---

## 待联网复核（环境无外网）

1. **Graphiti 是否新增 AGE/PG 适配器**（2026-09-21→09-29 的 8 天）：拉 `getzep/graphiti` HEAD 的 `pyproject.toml` + `README.md` 后端列表 + driver 目录有无 `AgeDriver`。**若已加 AGE，Q5 翻转，需重评。**
2. Hindsight 的 contributors/30d commits/测试文件数/最新 release（stars/forks 已校正 41.6k/5.6k）。
3. Cognee/Graphiti 2026-09-29 最新提交/版本。
4. Cognee OSS 版"SDK 写入路径未和租户身份打通"是否在近期版本修复（影响首期写入实现方式）。

## 证据来源

| 问题 | 来源 |
|------|------|
| Q1 多租户 | `hindsight-api-slim/hindsight_api/extensions/tenant.py`、`static-keys-tenant/extension.py`、`.deploy-hindsight-mt/` + 本机容器实测 |
| Q2/Q3 PG | `alembic/versions/`（104 迁移）、`engine/db/{__init__,postgresql}.py`、`engine/memory_engine.py`、`.env.example`、`tests/test_db_abstraction.py` |
| Q4 图谱 | `alembic/.../5a366d414dce_initial_schema.py`、`engine/search/link_expansion_retrieval.py`、`retain/fact_extraction.py`、`api/http.py` + `cognee/.../postgres_demo/__init__.py` |
| Q5 Graphiti | 既有报告对 `graphiti/README.md`、`graphiti_core/edges.py` 引用 + 本地 `cognee/evals/.../qa_benchmark_graphiti.py`（graphiti-core==0.17.8） |
| Q6 社区 | Hindsight 用户校正 41.6k/5.6k；Cognee/Graphiti 来自既有报告 2026-09-22 GitHub API 快照 |
| 管控对比 | Cognee `modules/users/{models,authentication,api_key,roles,tenants,permissions}` + `api/v1/{users,permissions,api_keys,datasets,activity}` + `infrastructure/databases/tenant_pg_routing/`；Hindsight `TenantExtension` 接口 + `static-keys-tenant/extension.py` + `config_resolver.py` |
