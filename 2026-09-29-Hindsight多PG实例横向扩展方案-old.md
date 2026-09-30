# Hindsight 多 PG 实例横向扩展方案

## 目的

当单个 PG 实例的存储空间或性能不满足需求时，Hindsight 如何横向扩展到多 PG 实例。

## 前置概念：记忆库（bank）/ schema / PG 实例的层级关系

理解横向扩展前，先厘清 Hindsight 的三层正交层级——每层解决不同问题，这也是横向扩展能"正交"的前提。

```
PG 实例（一个 PostgreSQL 数据库）        ← 物理存储、故障域、横向扩展边界
  └─ schema（租户级隔离单元）             ← 多租户隔离边界，一租户一 schema
       └─ bank（记忆库，租户内逻辑分组）   ← 业务语义，bank_id 路由
            └─ memory_units（实际记忆+embedding+图）
```

- **记忆库 = bank**：是表里的一行，靠 `bank_id` 路由（如 `company1-project-alpha`）。`banks` 表定义见 `alembic/.../5a366d414dce_initial_schema.py:185-197`，所有记忆数据表都带 `bank_id` 列。URL 路径 `/v1/default/banks/{bank_id}/memories/recall` 用的就是它。
- **schema = 租户**：PG 物理隔离层，API key → schema（如 `user_company1`）。所有表名 schema 限定（`fq_table()` → `user_company1.memory_units`）。见 `extensions/tenant.py:29`。
- **PG 实例**：物理数据库，横向扩展的边界单元。

**三者是包含关系，不是一一对应**：
- 一个 schema（租户）**可包含多个 bank**（一租户下可建多个项目/场景记忆库）
- 一个 bank **必然属于一个 schema**（不能跨租户）
- 默认每租户只建一个 bank，看起来像对应，那是使用方式，非结构限制

本机实例对应：
```
PG 实例 (zhuqingping_hindsight 内嵌 pg0)
├─ schema: user_company1   ← 租户 company1 (key-zhang3/key-li4)
│    └─ bank: company1-project-alpha
└─ schema: user_company2   ← 租户 company2 (key-wang5/key-xiao6)
     └─ bank: company2-project-gamma
```

**这层正交为什么重要**：横向扩展动的是最上层"PG 实例 → schema"的路由（schema 落在哪个 PG），而 bank 这层完全不变——recall/retain 只认 `bank_id`，不关心 schema 在哪个 PG 实例。这是后面"不碰核心"的根源。

## 核心结论

**Hindsight 多 PG 实例是正交扩展，工作量小、风险低，不碰记忆/检索核心。**

我此前评估"5~8 人周、是 Cognee 的 2~3 倍"是错的。核实源码后修正：Hindsight 的 schema 隔离已把"租户"做成一等公民，多实例只是加一个"实例"维度，与记忆/检索核心解耦。Cognee 把 `postgres_demo` 改生产级才是核心功能改造（高风险高工作量）——两者性质完全不同。

---

## 为什么 Hindsight 横向扩展是"轻量正交扩展"

核实源码的三个关键事实：

### 1. 所有查询已 schema-scoped，无跨 schema join
`engine/schema.py:26` `fq_table(table)` 读 contextvar `_current_schema`（`memory_engine.py:92`），所有表名都生成 `"schema".table` 形式。

**含义**：一个 schema 在逻辑上等价于一个独立逻辑库。记忆写入、recall 检索、图谱遍历全在当前 schema 内完成，不存在"跨租户 join"。所以"租户 A 的数据在 PG1、租户 B 的数据在 PG2"在 SQL 层面天然成立——只要每个请求连到正确的 PG、设对 schema。

### 2. 迁移与 worker 已是 per-tenant，加实例维度是同构扩展
- 迁移：`memory_engine.py:5176` 已 `run_migrations_for_schemas`，per-schema 并发 fan-out。改成 per-(schema, instance) 是同构扩展。
- worker：`list_tenants()` 已 per-tenant 轮询（`static-keys extension.py`）。加实例维度是同构扩展。

**含义**：现有的 per-tenant 调度/迁移循环已经把租户当独立单元遍历，加"实例"只是遍历维度 +1，不是重构。

### 3. 跨租户全局例程已独立设计
`schema.py:48` `fq_routine()` 注释："routines are deliberately cross-tenant"。跨租户的全局例程（枚举 `pg_class`）已经和 per-tenant 查询分离处理。

**含义**：设计者已把"单实例全局 vs per-tenant"边界想清楚。多实例化时，只有这些跨租户例程需要重新定义"全局"的范围（从"一个 PG 的所有 schema"变成"所有 PG 的所有 schema"），但它们是少数、已隔离的。

### 与 Cognee 核心改造的对比

| | Hindsight 多 PG 实例 | Cognee `postgres_demo` 改生产级 |
|--|---------------------|-------------------------------|
| 性质 | 扩展性外挂 | 核心功能改造 |
| 动什么 | 连接池选择层 + 迁移/worker 遍历维度 | 图谱存储 + 检索核心 |
| 碰核心吗 | **否**（记忆/检索不变） | **是**（检索核心） |
| 风险 | 低（正交） | 高（动核心） |
| 可灰度 | 是（按租户逐步迁移） | 否（图谱格式变更全局） |

---

## 扩展架构（复用你在 Cognee 上用 Agent 开发的 `tenant_pg_routing` 设计）

> 说明：Cognee 原生**无**横向扩展能力，`cognee/infrastructure/databases/tenant_pg_routing/` 是你本地用 Agent 开发、未入上游 `topoteretes/cognee`（`git status`=`??` 未跟踪）。以下"借鉴 Cognee"均指**复用你已开发的这套设计**，非 Cognee 自带。

### 现状

```
所有租户 schema → 同一个 PG 实例
  Cognee 原生同样无路由层; 你已用 Agent 开发 tenant_pg_routing (本地未提交)
```

Hindsight 当前：`_backend` 单实例，schema 在 contextvar 层选，连接池单 asyncpg pool。

### 目标架构

```
┌────────────────────────────────────────────────────────────┐
│  Hindsight API/Worker                                      │
│                                                            │
│  请求进来 → authenticate() → TenantContext(schema_name)    │
│           ↓                                                │
│  【新增】TenantRouter: schema_name → PGInstance          │
│           ↓                                                │
│  _get_backend() 按 schema 选 PG pool                      │
│           ↓           ↓           ↓                      │
│        PG1 pool    PG2 pool   PG3 pool                      │
└───────┬────────────┬───────────┬──────────────────────────┘
        │            │           │
        ▼            ▼           ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │  PG1    │  │  PG2    │  │  PG3    │
   │ schema  │  │ schema  │  │ schema  │
   │ user_a  │  │ user_c  │  │ user_e  │
   │ user_b  │  │ user_d  │  │ user_f  │
   └─────────┘  └─────────┘  └─────────┘
   (小租户群)   (大租户独占)  (新租户)
```

### 关键设计点（复用你已开发的 Cognee `tenant_pg_routing`）

**1. 路由表 `tenant_pg_routing`（套用你在 Cognee 上开发的同名设计）**

你在 Cognee 上用 Agent 开发的设计（`cognee/infrastructure/databases/tenant_pg_routing/routing.py`，本地未入上游）：
```sql
CREATE TABLE tenant_pg_routing (
    tenant_id   VARCHAR PRIMARY KEY,
    pg_host     VARCHAR NOT NULL,
    pg_port     VARCHAR NOT NULL,
    pg_username VARCHAR NOT NULL,
    pg_password VARCHAR NOT NULL,
    pg_database VARCHAR NOT NULL DEFAULT 'hindsight'
);
```
- opt-in：未映射的租户回退默认实例（向后兼容，零迁移成本起步）
- 表存在共享关系库（Cognee 是 `cognee_db`；Hindsight 可放在一个独立的 `hindsight_meta` 库或 schema）

Hindsight 适配：Hindsight 的"租户"= schema_name（如 `user_company1`），所以路由键是 schema_name 而非 tenant_id：
```sql
CREATE TABLE schema_pg_routing (
    schema_name VARCHAR PRIMARY KEY,   -- user_company1 等
    pg_host     VARCHAR NOT NULL,
    pg_port     VARCHAR NOT NULL,
    pg_username VARCHAR NOT NULL,
    pg_password VARCHAR NOT NULL,
    pg_database VARCHAR NOT NULL
);
```

**2. backend 选择层改动（Hindsight 唯一核心改动）**

现状（`memory_engine.py`）：
```python
self._backend: DatabaseBackend | None = None  # 单实例
async def _get_backend(self):
    return self._backend
```

改动为：
```python
self._backends: dict[str, DatabaseBackend] = {}  # schema → backend
self._default_backend: DatabaseBackend  # 未映射回退

async def _get_backend(self) -> DatabaseBackend:
    schema = get_current_schema()
    pg_instance = self._tenant_router.resolve(schema)  # 查路由表
    if pg_instance is None:
        return self._default_backend  # opt-in 回退
    return self._backends[pg_instance.id]  # 按 schema 选
```

**这就是核心改动的全部**——一个集中的、薄的 backend 选择层。记忆写入、recall 检索、图谱遍历的代码完全不变（它们只调 `_get_backend()` + `fq_table()`，不知道也不关心连的是哪个 PG）。

**3. 连接池池（per-instance pool）**

每个 PG 实例独立 asyncpg pool：
```python
self._backends = {
    pg.id: PostgresBackend(pg.dsn, pool_min, pool_max)
    for pg in configured_instances
}
```
- 健康检查 + 失败转移：某实例宕机，其租户降级或报错，不影响其他实例租户
- 懒初始化：首次访问某 schema 才建该实例的 pool
- 读副本：每实例的 `READ_DATABASE_URL` 独立配置（Hindsight 已有一等公民读副本，per-instance 化即可）

**4. 迁移 fan-out 跨实例**

现状：`run_migrations_for_schemas(schemas, concurrency)` per-schema 并发。
改动：按实例分组，per-instance 内继续 per-schema 并发：
```python
for pg_instance, schemas_in_instance in group_by_instance(tenants):
    run_migrations_for_schemas(schemas_in_instance, ...)
    # 每实例独立跟踪迁移版本（Alembic 已支持 per-schema search_path）
```
- Alembic 迁移本就 schema-aware（per-tenant `search_path`），跨实例只是多连几个库跑同一套迁移
- 每实例的迁移版本独立（一个实例停留在 v50，另一个到 v104，互不影响）

**5. worker 跨实例调度**

现状：`list_tenants()` 返回所有 schema，轮询 claim。
改动：`list_tenants()` 返回 `(schema, pg_instance)`，worker 跨实例轮询、per-tenant 公平调度。
- Hindsight 已有"per-tenant fair rotation"，加实例维度同构扩展

**6. 新租户分配策略**

- 默认：轮询/容量优先分配到当前最空的 PG 实例
- 大租户：可指定独占一个 PG 实例（物理隔离 + 性能保障）
- 小租户：共享一个 PG 实例的多 schema（成本优化）

---

## 扩展粒度对比：schema 级 vs bank 级

Hindsight 有两层概念（schema、bank），横向扩展可按两种粒度做。本节对比两个思路、修改点与工作量。

### 关键事实（决定可行性）

源码确认：
- **bank 物理上绑定 schema**：bank 是 schema 内表的一行（`banks` 表的 `bank_id` 列），**无独立 bank→PG 实例映射**。实测 `user_company1.banks` 里有 `company1-project-alpha` 和 `PostgreSQL Knowledge` 两个 bank，都在 `user_company1` schema 的 PG 实例里。
- **无跨 bank 聚合查询**：recall/retain/get_bank_stats 都是单 schema 单 bank。`bank_stats_cache` 表也是 schema × bank 限定（`bank_stats_cache.py:237`）。
- **`list_tenants` 只返回 schema 级**（`static-keys extension.py:356`），worker/迁移遍历的是 schema，**无 bank 级枚举**。
- **bank_id 是 contextvar**（`memory_engine.py:98`），请求级绑定。

### 思路 A：schema 粒度扩展（一个 schema 落一个 PG 实例）

**机制**：以 schema 为搬迁单元。某租户 schema 数据量/性能压力大 → 把整个 schema 迁到新 PG 实例 → 该租户所有 bank 一起迁走。

**方案**：
```
schema_pg_routing: schema_name → PG 实例
  user_company1 → PG1
  user_company2 → PG2（company2 的所有 bank 一起在 PG2）
```
请求时：key → schema → 查路由表 → 选 PG 实例 → 在该实例上 schema 限定 + bank_id 过滤。

**修改点**：
1. 路由层：`schema_pg_routing` 表（schema_name → PG 实例），`_get_backend()` 按 contextvar schema 选实例。
2. 连接管理：per-instance asyncpg pool 池。
3. 迁移 fan-out 跨实例：`run_migrations_for_schemas` 扩展成 per-(schema, instance)。
4. worker 跨实例调度：`list_tenants()` 返回 schema 已带实例信息（加一维）。
5. 读副本：per-instance `READ_DATABASE_URL`。
6. 管控面：新租户分配 PG 实例策略。

**工作量**：约 2~3 人周（核心改动集中在一处 backend 选择层）。

**优点**：
- **与 Hindsight 原生模型同构**：schema 本就是隔离单元、`list_tenants`/迁移/worker 都以 schema 为单位，加实例维度是同构扩展。
- **隔离与扩展对齐**：一个租户整体迁走，物理隔离边界清晰。
- **改动集中**：一处 backend 选择层，记忆/检索核心不变。

**缺点**：
- **粒度粗**：某租户只有一个大 bank 撑爆，仍要迁整个 schema（连带其他小 bank）。
- **搬迁代价大**：整个 schema 的所有表 + 向量索引一起搬，数据量大、耗时长。

### 思路 B：bank 粒度扩展（一个 bank 落一个 PG 实例）

**机制**：以 bank 为搬迁单元。某 bank（如某企业的大项目记忆库）数据量/性能压力大 → 把这个 bank 迁到新 PG 实例 → 同 schema 其他 bank 不动。

**方案**：
```
bank_pg_routing: (schema_name, bank_id) → PG 实例
  (user_company1, dev-bank)       → PG1
  (user_company1, big-proj-bank)  → PG2（单独迁走，同 schema 其他 bank 留 PG1）
```
请求时：key → schema → bank_id → 查路由表 → 选 PG 实例 → 在该实例上 bank_id 过滤（注意：bank 不再与 schema 同库，bank 表行也在迁入实例的对应 schema 里）。

**修改点**：
1. 路由层：`bank_pg_routing` 表（schema_name + bank_id → PG 实例），`_get_backend()` 按 contextvar(schema, bank_id) 选实例。
2. 连接管理：per-instance pool 池（同 A）。
3. **bank 物理与 schema 解绑**：bank 的数据行（`banks`/`memory_units`/`chunks`/`entities`/`memory_links`...）要从"schema 内表的一行"变成"可在任意实例的同名 schema 里"。迁 bank 时要按 `bank_id` 把这些表里该 bank 的所有行抽出来、迁到目标实例的同名 schema。
4. **跨实例查询风险**：同 schema 的不同 bank 可能在不同实例，**任何隐式跨 bank 的逻辑都要复查**（如实体消解 `idx_entities_bank_lower_name` 是 bank 内唯一，不跨 bank，OK；但若有跨 bank 的全局视图/聚合要逐个排查）。
5. 迁移：bank 级迁移（按 bank_id 抽行 + 跨实例导入 + 重建 HNSW 索引），而非 schema 级。
6. worker：`list_tenants()` 要扩展成返回 (schema, bank) 列表，或新增 `list_banks()` 枚举——动 worker 调度模型（从 schema 级变 bank 级）。
7. 读副本：per-instance（同 A）。
8. 管控面：bank 级分配策略。

**工作量**：约 5~8 人周（比 schema 级重 2~3 倍）。

**优点**：
- **粒度细**：哪个 bank 大迁哪个，不影响同 schema 其他 bank，搬迁数据量小。
- **大 bank 独占实例**：可给大 bank 独占 PG 实例做性能保障。

**缺点**：
- **与原生模型不对齐**：Hindsight 的 bank 物理绑定 schema（`banks` 表行级），bank→实例需要"解绑"改造，动数据组织方式。
- **bank 级迁移复杂**：按 bank_id 跨表抽行 + 跨实例导入 + HNSW 索引重建，比 schema 整体迁（pg_dump schema 级）复杂得多。
- **worker 调度模型要改**：从 schema 级枚举变 bank 级枚举。
- **跨实例隐患**：需全量排查"是否有隐式跨 bank 逻辑"（虽然现状无跨 bank 聚合，但要保证未来不引入）。

### 对比表

| 维度 | 思路 A（schema 级）| 思路 B（bank 级）|
|------|-------------------|------------------|
| 与原生模型对齐度 | 高（schema 是隔离单元，同构扩展）| 低（bank 物理绑定 schema，需解绑改造）|
| 路由键 | schema_name | (schema_name, bank_id) |
| 搬迁单元 | 整个 schema | 单个 bank |
| 搬迁代价 | 大（全 schema 表+索引）| 小（按 bank_id 抽行）|
| 粒度 | 粗（连带同 schema 其他 bank）| 细（只迁大 bank）|
| 迁移复杂度 | 低（pg_dump schema 级）| 高（跨表抽行 + 跨实例导入 + 重建 HNSW）|
| worker 调度改动 | 小（schema 已是遍历单元，加实例维度）| 大（从 schema 级变 bank 级枚举）|
| 跨实例隐患 | 低（schema 内所有 bank 同库）| 中（同 schema 不同 bank 可能跨库，需排查）|
| 工作量 | ~2~3 人周 | ~5~8 人周 |
| 核心代码改动 | 一处 backend 选择层 | backend 选择层 + bank 解绑 + worker 模型 |

### 建议

**首期选思路 A（schema 级）**：
- 与 Hindsight 原生模型同构，改动集中、风险低、可正交灰度（按租户逐个迁）。
- 适合"某租户整体数据量大/性能慢"的场景——这通常是云化最常见的情况（大客户撑爆单库）。

**思路 B（bank 级）作为后续增强**：
- 仅当出现"单租户内某 bank 极大、其他 bank 很小"的明确场景时再考虑。
- 代价是 bank 物理解绑 + worker 调度模型改造，与"不碰核心"的原则相悖，应作为正交扩展的第二阶段，而非首期。
- 若真要做，建议在思路 A 落地后、bank 级路由需求明确时再启动——届时可复用思路 A 的 per-instance pool / 路由层基建。

> 一个折中：思路 A 落地后，对"单 schema 内某 bank 极大"的场景，可临时用"给该 schema 独占一个 PG 实例"（即思路 A 的极端形态：一 schema 一实例）来缓解，而不必做 bank 级解绑。这是思路 A 内部的容量策略，不是思路 B。

---

## 工作量重估

| 改动项 | 范围 | 风险 |
|--------|------|------|
| 路由表 + TenantRouter | 新增模块，不动核心 | 低 |
| `_get_backend` 按 schema 选 | **1 处集中改动** | 低 |
| per-instance 连接池池 | 连接管理层 | 低 |
| 迁移 fan-out 跨实例 | 迁移 runner | 低 |
| worker 跨实例调度 | worker poller | 低 |
| 新租户分配策略 | 管控面 | 低 |
| 跨租户全局例程重定义 | 少数例程 | 中 |
| 测试 + 灰度 | 全链路 | — |

**估算：2~3 人周**（非此前错估的 5~8）。核心是一处集中的 backend 选择层改动，其余是同构扩展 per-tenant 逻辑。

---

## 为什么不碰核心

**记忆/检索核心（recall/retain/图谱）完全不感知"连的是哪个 PG"**：

```
retain 写入:  fq_table("memory_units")  → "user_company1.memory_units"
                                        → 经 _get_backend() 选中 PG1 的连接
recall 检索:  同上, WHERE bank_id = ...
              语义/BM25/图 RRF 融合全在当前 schema 内
图谱遍历:     memory_links self-join, 同 schema 内
```

- 改造前：所有 schema 在 PG1，查询走 PG1 的 pool
- 改造后：schema 在 PG1 或 PG2，查询走对应 pool
- **核心代码一行不变**——它只调 `_get_backend()` + `fq_table()`，这两个 helper 屏蔽了实例选择

这正是"扩展不碰核心"的工程含义：连接选择是正交的一层。

---

## 灰度与迁移路径

1. **零迁移起步**：路由表为空，所有租户回退默认实例 = 当前行为，零风险上线。
2. **按租户逐步迁移**：把大租户 `user_bigcorp` 加路由表项指向新 PG2 → 该租户流量切到 PG2，其余不变。
3. **迁移该租户数据**：从 PG1 导出该 schema → 导入 PG2（pg_dump/restore schema 级，或逻辑复制）。
4. **验证 + 清理**：验证 recall/retain 正常后，PG1 删除该 schema。
5. **逐步铺开**：按租户逐个迁移，每个都是独立的小迁移，可回滚。

**风险隔离**：任一租户迁移失败不影响其他租户；可按租户粒度灰度。

---

## 触发扩展的判定

何时需要扩展（单 PG 不满足的信号）：
- **存储**：单 PG 实例磁盘占用 > 70%，或某大租户数据量占整体 > 50%（应独占实例）。
- **性能**：recall p95 延迟上升、写吞吐触顶、连接池耗尽、pgvector HNSW 索引构建慢到影响在线。
- **隔离**：某租户需要物理隔离（合规/性能保障）。
- **故障域**：单 PG 实例故障影响所有租户，需拆分故障域。

扩展动作：新增一个 PG 实例 → 新租户分配到它 → 老租户按需迁移。

---

## 与 Cognee 横向扩展的关系

> 事实澄清：Cognee **原生无** `tenant_pg_routing`。你在 Cognee 上用 Agent 开发了该路由层（本地未 `git add`、未入上游），以下对比基于这套你已开发的实现。

你已开发的 Cognee `tenant_pg_routing` 实现了路由表骨架（opt-in、回退默认）。Hindsight 可复用：
- 路由表结构（schema_name 版本）
- opt-in + 回退设计（零迁移起步）
- 路由查询逻辑

差异：
- Cognee 隔离单元是 database（per-dataset 一库），路由是 tenant→instance，dataset 自动落在该 tenant 的 instance
- Hindsight 隔离单元是 schema（per-tenant 一 schema），路由是 schema→instance，schema 内多 bank

两者路由层设计同构。Hindsight 加这一层的工作量与你在 Cognee 上接通 `tenant_pg_routing` 到 dataset 创建路径相当（都是"路由表 + backend 选择"），**不是此前错估的 2~3 倍**。

---

## 结论

- Hindsight 多 PG 实例横向扩展是**正交扩展**：动连接选择层，不碰记忆/检索核心，风险低，可按租户灰度。
- 核心改动是一处集中的 `_get_backend()` 按 schema 选实例，其余是 per-tenant 逻辑的同构扩展。
- 工作量约 **2~3 人周**（此前 5~8 人周评估作废）。
- 复用你已用 Agent 在 Cognee 上开发的 `tenant_pg_routing` 设计（opt-in + 回退），零迁移起步、按租户逐步迁移。注：该设计是本地开发产物，非 Cognee 原生。
- 触发判据：单 PG 存储/性能/隔离/故障域任一不满足时扩展。

> 修正致歉：此前把"Cognee 核心功能改造"与"Hindsight 正交扩展"混为一谈，给出错误的工作量倍数。两者性质不同——Cognee 改 `postgres_demo` 是动检索核心（高风险），Hindsight 加 PG 实例是动连接选择层（低风险正交）。

## 疑问：

（1）数据隔离

- cognee 针对不同的 Dataset 使用 PG 不同的数据库（DB）进行隔离，hindsight 针对不同的租户(Tenant) 使用不同的 PG Schema 进行隔离。
- 数据库（DB）隔离相比 Schema 隔离更好一些。



（2）导入的文档如何存储

- 所有数据都在 PG 的 user_company1 schema 下（zhuqingping_hindsight 容器内嵌 pg0，库名 hindsight）。无外部向量库、无对象存储（原始 PDF 本应进 file_storage bytea 表，但实际没存进去）。

  ```
    一个文档 → 三级抽取的完整链路
    导入 PDF (agent_knowledge_ingest_file 或 API)
       │
       ├─ 抽取文本 → documents.original_text (111,895 字符)
       ├─ (本应存原始PDF → file_storage.data, 但本次未落库)
       │
       ├─ 分块 → chunks 表 (38 条, ~3000字符/块, 纯文本无向量)
       │
       ├─ LLM 抽取事实 → memory_units 表 (247 条)
       │     ├─ text: 一条事实陈述
       │     ├─ embedding: vector(1024) ← 向量化(用于语义检索)
       │     ├─ search_vector: tsvector ← 全文检索(BM25)
       │     ├─ fact_type: observation
       │     └─ chunk_id: 反指来源 chunk
       │
       └─ 实体/关系抽取 → entities + unit_entities + memory_links + entity_cooccurrences
             (图谱层, recall 的 graph 检索臂用)
  ```

  



（3）数据横向扩展

- hindsight 存储的单位
- **记忆库（Bank）**

