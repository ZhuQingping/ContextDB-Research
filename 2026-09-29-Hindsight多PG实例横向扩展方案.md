# Hindsight 多 PG 实例横向扩展方案

## 一、问题：为什么需要横向扩展

### 背景：Hindsight 的存储模型

Hindsight 用 PostgreSQL 作后端，记忆数据按"PG 实例 → schema → bank"三层组织：

- **PG 实例**：一个 PostgreSQL 数据库，承载多个 schema。云化部署时，通常一个 Hindsight 实例对应一个 PG 实例（自托管时是内嵌 pg0）。

- **schema**：租户级隔离单元。一个租户一个 schema（如 `user_company1`），schema 里有完整的表集合（banks / memory_units / chunks / entities / memory_links / ...）。

- **bank**：租户内的记忆库，靠 `bank_id` 路由（如 `dev-bank`）。一个 schema 可含多个 bank，bank 是 schema 内表的一行 + 各记忆表里的 `bank_id` 列，靠 SQL `WHERE bank_id=?` 逻辑隔离。

  ```sql
  hindsight=# \l
                                                    List of databases
     Name    |  Owner   | Encoding | Locale Provider | Collate |  Ctype  | Locale | ICU Rules |   Access privileges    
  -----------+----------+----------+-----------------+---------+---------+--------+-----------+------------------------
   hindsight | postgres | UTF8     | libc            | C.UTF-8 | C.UTF-8 |        |           | =Tc/postgres          +
             |          |          |                 |         |         |        |           | postgres=CTc/postgres +
             |          |          |                 |         |         |        |           | hindsight=CTc/postgres
   postgres  | postgres | UTF8     | libc            | C.UTF-8 | C.UTF-8 |        |           | 
   template0 | postgres | UTF8     | libc            | C.UTF-8 | C.UTF-8 |        |           | =c/postgres           +
             |          |          |                 |         |         |        |           | postgres=CTc/postgres
   template1 | postgres | UTF8     | libc            | C.UTF-8 | C.UTF-8 |        |           | =c/postgres           +
             |          |          |                 |         |         |        |           | postgres=CTc/postgres
  (4 rows)
  
  hindsight=# \dn
            List of schemas
       Name      |       Owner       
  ---------------+-------------------
   public        | pg_database_owner
   user_company1 | hindsight
   user_company2 | hindsight
  (3 rows)
  
  hindsight=# \dt user_company1.*
                          List of tables
      Schema     |           Name           | Type  |   Owner   
  ---------------+--------------------------+-------+-----------
   user_company1 | alembic_version          | table | hindsight
   user_company1 | async_operations         | table | hindsight
   user_company1 | attachments              | table | hindsight
   user_company1 | audit_log                | table | hindsight
   user_company1 | bank_stats_cache         | table | hindsight
   user_company1 | banks                    | table | hindsight
   user_company1 | chunks                   | table | hindsight
   user_company1 | directives               | table | hindsight
   user_company1 | documents                | table | hindsight
   user_company1 | entities                 | table | hindsight
   user_company1 | entity_cooccurrences     | table | hindsight
   user_company1 | entity_maintenance_queue | table | hindsight
   user_company1 | file_storage             | table | hindsight
   user_company1 | graph_maintenance_queue  | table | hindsight
   user_company1 | invalidated_memory_units | table | hindsight
   user_company1 | knowledge_pages          | table | hindsight
   user_company1 | llm_requests             | table | hindsight
   user_company1 | memory_links             | table | hindsight
   user_company1 | memory_units             | table | hindsight
   user_company1 | mental_model_history     | table | hindsight
   user_company1 | mental_models            | table | hindsight
   user_company1 | observation_history      | table | hindsight
   user_company1 | unit_entities            | table | hindsight
   user_company1 | webhooks                 | table | hindsight
  (24 rows)
  
  hindsight=# \dt user_company2.*
                          List of tables
      Schema     |           Name           | Type  |   Owner   
  ---------------+--------------------------+-------+-----------
   user_company2 | alembic_version          | table | hindsight
   user_company2 | async_operations         | table | hindsight
   user_company2 | attachments              | table | hindsight
   user_company2 | audit_log                | table | hindsight
   user_company2 | bank_stats_cache         | table | hindsight
   user_company2 | banks                    | table | hindsight
   user_company2 | chunks                   | table | hindsight
   user_company2 | directives               | table | hindsight
   user_company2 | documents                | table | hindsight
   user_company2 | entities                 | table | hindsight
   user_company2 | entity_cooccurrences     | table | hindsight
   user_company2 | entity_maintenance_queue | table | hindsight
   user_company2 | file_storage             | table | hindsight
   user_company2 | graph_maintenance_queue  | table | hindsight
   user_company2 | invalidated_memory_units | table | hindsight
   user_company2 | knowledge_pages          | table | hindsight
   user_company2 | llm_requests             | table | hindsight
   user_company2 | memory_links             | table | hindsight
   user_company2 | memory_units             | table | hindsight
   user_company2 | mental_model_history     | table | hindsight
   user_company2 | mental_models            | table | hindsight
   user_company2 | observation_history      | table | hindsight
   user_company2 | unit_entities            | table | hindsight
   user_company2 | webhooks                 | table | hindsight
  (24 rows)
  ```

  

关键性质（源码实证）：
- 所有查询 schema-scoped，无跨 schema join（`fq_table()` 读 contextvar `_current_schema`）。
- bank 物理绑定 schema：bank 是 schema 内表的一行，无独立 bank→PG 映射。
- 无跨 bank 聚合查询：recall/retain/stats 都是单 schema 单 bank。
- worker 与迁移以 schema 为遍历单元（`list_tenants()` 返回 schema 列表）。
- 写路径单实例：原生一个 PG 实例承载所有租户 schema。

### 问题

云化服务化场景下，**单 PG 实例会成为存储与性能瓶颈**：

1. **存储瓶颈**：租户数和记忆量持续增长，单实例磁盘容量见顶。大租户（记忆条数百万级）会占据不成比例的存储。
2. **性能瓶颈**：单实例连接池、CPU、IO 争用；大租户的批量 retain/重建 HNSW 索引拖慢在线 recall；写吞吐触顶。
3. **故障域过大**：单实例故障影响所有租户，不满足云服务的可用性承诺。
4. **隔离诉求**：大客户要求物理隔离（独立实例，性能与安全保障）。

原生 Hindsight 只能纵向扩展（升配单实例），没有横向扩展（加实例）能力。本方案解决"单 PG 实例存不下/扛不住时，如何加实例分摊"。

### 扩展粒度的两个候选

Hindsight 有 schema 和 bank 两层，横向扩展可按两种粒度做：
- **schema 级**：一个 schema 整体落一个 PG 实例（一个租户的所有 bank 一起搬）。
- **bank 级**：一个 bank 落一个 PG 实例（同 schema 的不同 bank 可分属不同实例）。

第二节对比这两种，第三节给出推荐方案的高层设计。

---

## 二、如何解决：可行方案与关键决策

### 方案 A：schema 级扩展

**机制**：以 schema 为搬迁单元。某租户 schema 存储或性能压力大时，把整个 schema 迁到新 PG 实例，该租户所有 bank 一起迁走。

**路由键**：`schema_name → PG 实例`。

```
schema_pg_routing:
  user_company1 → PG1
  user_company2 → PG2   (company2 的所有 bank 一起在 PG2)
```

请求路径：API key → schema → 查路由表选 PG 实例 → 在该实例上 schema 限定 + bank_id 过滤。

**与原生模型的关系**：schema 本就是隔离单元、worker/迁移的遍历单元。加"schema 落哪个实例"这一维，是在原生抽象上自然延伸，不动 bank 层、不动记忆/检索核心。

### 方案 B：bank 级扩展

**机制**：以 bank 为搬迁单元。某 bank（如某企业的大项目记忆库）压力大时，单独把这个 bank 迁到新 PG 实例，同 schema 其他 bank 不动。

**路由键**：`(schema_name, bank_id) → PG 实例`。

```
bank_pg_routing:
  (user_company1, dev-bank)       → PG1
  (user_company1, big-proj-bank)  → PG2   (单独迁走，同 schema 其他 bank 留 PG1)
```

**与原生模型的关系**：bank 物理绑定 schema（bank 是 schema 内表的一行）。bank 级扩展要求 bank 能脱离所属 schema、落到任意实例——这要改 bank 的数据组织方式，不是原生抽象的延伸。

### 关键决策点对比

| 决策维度 | 方案 A（schema 级）| 方案 B（bank 级）|
|---------|-------------------|------------------|
| 与原生模型对齐 | 对齐：schema 是原生隔离/遍历单元 | 不对齐：bank 物理绑定 schema，需解绑 |
| 路由键 | schema_name | (schema_name, bank_id) |
| 搬迁单元 | 整个 schema（所有表+索引） | 单 bank（按 bank_id 跨表抽行）|
| 搬迁数据量 | 大 | 小（只迁大 bank）|
| 迁移实现 | pg_dump schema 级，成熟 | 跨表按 bank_id 抽行 + 跨实例导入 + 重建 HNSW，复杂 |
| worker 调度改动 | 小：schema 已是遍历单元，加实例维度 | 大：遍历单元从 schema 级变 bank 级 |
| 跨实例隐患 | 低：schema 内所有 bank 同库 | 中：同 schema 不同 bank 可能跨库，需排查隐式跨 bank 逻辑 |
| 粒度粗细 | 粗（连带同 schema 其他 bank）| 细（只迁大 bank）|
| 核心代码改动 | 一处 backend 选择层 | backend 选择层 + bank 物理解绑 + worker 模型 |

### 决策结论

**选方案 A（schema 级）**，理由：

1. **与原生模型同构**：schema 是 Hindsight 既有的隔离/遍历单元，加实例维度是同构扩展，风险低。
2. **改动集中、不碰核心**：核心改动是"按 schema 选 backend"这一层，记忆/检索/图谱代码不变。
3. **迁移成熟**：schema 级 pg_dump/restore 是 PG 标准操作，无需造轮子。
4. **对症云化主场景**：云化最常见的是"大客户撑爆单库"，schema 级正好以租户为单位分摊。

**方案 B 作为后续增强**，仅当出现"单租户内某 bank 极大、其他 bank 很小"的明确场景时再考虑。它需要 bank 物理解绑 + worker 调度模型改造，代价高，应作第二阶段。

> 折中：方案 A 落地后，对"单 schema 内某 bank 极大"的场景，可临时用"给该 schema 独占一个 PG 实例"（方案 A 的极端形态：一 schema 一实例）缓解，不必做 bank 级解绑。

---

## 三、具体方案（high level）：schema 级横向扩展

### 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│  Hindsight API / Worker                                      │
│                                                              │
│  请求 → authenticate() → schema_name                         │
│        ↓                                                     │
│  SchemaRouter: schema_name → PGInstance  (查 routing 表)     │
│        ↓                                                     │
│  _get_backend() 按 schema 选 PG pool                         │
│        ↓           ↓           ↓                            │
│     PG1 pool    PG2 pool    PG3 pool                          │
└──────┬────────────┬───────────┬──────────────────────────────┘
       │            │           │
       ▼            ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │  PG1    │ │  PG2    │ │  PG3    │
   │ schema  │ │ schema  │ │ schema  │
   │ user_a  │ │ user_c  │ │ user_e  │
   │ user_b  │ │ user_d  │ │ ...     │
   └─────────┘ └─────────┘ └─────────┘
   (小租户群)  (大租户独占) (新租户)
```

### 迁移版本信息：天然 per-schema 独立

在展开关键组件前，先讲清一个关键事实——**schema 的迁移版本信息天然跟着 schema 走，不是跟实例走**。这决定了后续迁移/升级组件的设计基线。

Alembic 标准机制：每个 schema 自己有一张 `alembic_version` 表（通过 `version_table_schema` 设为目标 schema）。实测 `user_company1.alembic_version` 和 `public.alembic_version` 各有记录。迁移代码 `run_migrations_for_schemas`（`migrations.py:1420`）每个 schema 在独立进程跑 Alembic `command.upgrade()`，版本表落在该 schema 内。

多实例下的含义：

```
PG 实例 PG1
├─ schema user_company1
│    └─ alembic_version = a7c2e9f41b60   ← 该 schema 的迁移版本
└─ schema user_company2
     └─ alembic_version = a7c2e9f41b60

PG 实例 PG2 (后续加的实例)
└─ schema user_company3 (从 PG1 迁来的新租户)
     └─ alembic_version = a7c2e9f41b60   ← schema 迁过来时版本表一起带过来
```

- **版本信息跟着 schema 走**：schema 迁到哪个实例，版本表就在哪个实例（pg_dump schema 级天然带上）。
- **每实例版本独立跟踪**：不同实例上的 schema 可在不同版本（后续滚动升级时，先升一部分实例的 schema）。
- **对横向扩展是天然利好**：无需额外设计版本表，schema 的版本信息自带，多实例扩展不需要新增版本管理逻辑。

#### 首期版本与可扩展性约束

本项目首期是干净起点：
- **不涉存量升级、不涉数据搬迁**——所有 schema 初始同版本（最新 head）。
- **但要为后续版本升级和可扩展性留口子**。

设计基线（为后续留口子）：
1. **路由层不假设版本一致**：SchemaRouter 和迁移逻辑要能处理"某实例版本落后"的情况（后续滚动升级时会出现）。首期版本一致，但代码不写死"所有实例同版本"的假设。
2. **迁移 runner 保持 per-schema per-process**：`run_migrations_for_schemas` 加实例维度时，保持每实例独立进程跑迁移，版本表各 schema 各自管。首期同版本，但结构上支持实例间版本差异。
3. **实例状态机**：`pg_instances.status`（active / draining / retired）为后续升级/搬迁/下线留口子。首期只用 active，但字段先建好，不做 draining/retired 逻辑。schema 级迁移态（`schema_pg_routing.schema_state`）同理留口子。

含义：首期实现可以简化（所有实例同版本、只 active 状态、无迁移态），但**数据模型和接口不写死这些假设**——后续版本升级、滚动迁移、实例下线时，不用重构。

### 关键组件

**1. 路由表 `schema_pg_routing`**

独立设计（不复用外部 demo），放在一个共享元数据库（如 `hindsight_meta`）或一个独立的管控 schema：

```sql
-- schema→实例路由表（归属 + schema 级迁移态）
CREATE TABLE schema_pg_routing (
    schema_name    VARCHAR PRIMARY KEY,   -- 如 user_company1
    pg_instance_id VARCHAR NOT NULL,     -- 指向 pg_instances
    schema_state   VARCHAR NOT NULL DEFAULT 'active',  -- active/migrating_out/migrating_in/frozen
    updated_at     TIMESTAMP NOT NULL DEFAULT now()
);

-- 实例登记表（静态规格 + 实例级状态）
CREATE TABLE pg_instances (
    pg_instance_id VARCHAR PRIMARY KEY,
    host           VARCHAR NOT NULL,
    port           VARCHAR NOT NULL,
    username       VARCHAR NOT NULL,
    password       VARCHAR NOT NULL,    -- 生产应走密管
    database       VARCHAR NOT NULL DEFAULT 'hindsight',
    read_url       VARCHAR,             -- 该实例的只读副本（可选）
    -- 静态规格（部署时登记，低频改，用于新租户容量规划）
    cpu_cores      INT,
    memory_mb      INT,
    disk_total_mb  BIGINT,
    pg_version     VARCHAR,             -- 如 18.1
    vector_ext     VARCHAR,             -- pgvector / vchord / pgvectorscale
    -- 实例级状态（实例本身的可用性，不含 schema 迁移态）
    status         VARCHAR NOT NULL DEFAULT 'active',  -- active/draining/retired
    created_at     TIMESTAMP NOT NULL DEFAULT now()
);

-- 实例动态容量（采集上报，时序，与登记表分离）
CREATE TABLE pg_instance_metrics (
    pg_instance_id VARCHAR NOT NULL,
    collected_at   TIMESTAMP NOT NULL DEFAULT now(),
    disk_used_mb   BIGINT,
    schema_count   INT,
    conn_in_use    INT,
    pool_util      NUMERIC,             -- 0~1
    -- 索引便于取最新一条
    PRIMARY KEY (pg_instance_id, collected_at)
);
```

**关于规格与容量信息的分层（关键设计决策）**：

把信息分三类、分表存，避免高频动态数据污染低频登记表：

| 类别 | 字段 | 表 | 来源 | 更新频率 | 用途 |
|------|------|----|------|---------|------|
| 静态规格 | cpu_cores/memory_mb/disk_total_mb/pg_version/vector_ext | pg_instances | 部署时登记 | 实例创建后基本不变 | 新租户容量规划输入 |
| 动态容量 | disk_used_mb/schema_count/conn_in_use/pool_util | pg_instance_metrics | 监控采集上报 | 分钟级 | 新租户实时分配决策、扩容预警 |
| 派生指标 | 磁盘利用率 | （计算）| JOIN 上面两表 | 跟随动态 | 阈值判定 |

为什么动态容量单放 `pg_instance_metrics` 而不进 `pg_instances`：
1. `pg_instances` 是"实例是什么"（登记表，低频），`metrics` 是"实例现在怎样"（快照，高频）。混表会让高频更新污染登记表读写。
2. 动态容量是时序数据，单存最新一条会丢历史趋势（看不到"这周磁盘涨了多少"），容量规划会缺数据。metrics 表带时间戳保留历史行。
3. 监控采集是另一模块职责，独立表解耦更干净。

新租户分配决策查询（JOIN 三表）：
```sql
SELECT i.pg_instance_id, i.cpu_cores, i.disk_total_mb,
       m.disk_used_mb, m.schema_count,
       (m.disk_used_mb::float / NULLIF(i.disk_total_mb,0)) AS disk_used_pct
FROM pg_instances i
LEFT JOIN LATERAL (
  SELECT * FROM pg_instance_metrics m
  WHERE m.pg_instance_id = i.pg_instance_id
  ORDER BY collected_at DESC LIMIT 1
) m ON true
WHERE i.status = 'active'
ORDER BY disk_used_pct ASC NULLS LAST;
-- 选磁盘利用率最低的 active 实例
```

- `schema_pg_routing`：schema→实例映射，opt-in。未映射的 schema 回退默认实例，保证零迁移起步。`schema_state` 记 schema 级迁移态（见下）。
- `pg_instances`：实例登记表，含连接信息、静态规格、实例级状态。
- `pg_instance_metrics`：实例动态容量，时序，独立采集。
- 三表分离：登记/路由/容量各司其职，更新频率与职责不同。

**关于状态机（实例级 vs schema 级分离）**：

迁移是 schema 级动作，不是实例级状态——一个实例上可能 schema_A 在迁出、schema_B 正常服务，实例整体说"migrating"不准。所以把"实例可用性"和"schema 迁移态"分开记：

实例级状态 `pg_instances.status`（实例本身的可用性）：

| 状态 | 含义 | 英文习惯 |
|------|------|---------|
| `active` | 正常服务，可接新 schema/新租户 | ✅ 标准运维术语 |
| `draining` | 正常服务存量 schema，但停止接新 schema/新租户（为下线/维护做准备，优雅排空） | ✅ 标准运维术语（drain = 排空流量后下线，K8s/DB 滚动升级通用）|
| `retired` | 已退役下线，不再服务任何 schema，记录保留供审计 | ✅ 退役保留记录，符合审计习惯 |

schema 级状态 `schema_pg_routing.schema_state`（schema 的迁移中状态）：

| 状态 | 含义 |
|------|------|
| `active` | schema 正常路由到该实例 |
| `migrating_out` | schema 正从此实例迁出（迁出期间该 schema 写入冻结或双写）|
| `migrating_in` | schema 正迁入此实例（迁入完成前不对外路由）|
| `frozen` | schema 写入冻结（维护用，首期不用）|

这样实例说"我 active 但有个 schema 在 migrating_out"，schema 说"我在迁出"，职责清晰。首期只用实例 `active` + schema `active`，其余状态字段先建好留口子，不实现迁移态逻辑。

> 命名修正说明：此前版本用 `pg_instances.status='migrating'` 是错的——`migrating` 描述的是 schema 级动作，记在实例侧语义错位。已改为实例级三态（active/draining/retired）+ schema 级迁移态分表记录。

**2. SchemaRouter（新增模块）**

职责：给 schema_name，返回该 schema 所在的 PG 实例连接信息。

- 启动时加载 `pg_instances`，为每个 active 实例建 asyncpg pool（per-instance pool，独立 min/max size、健康检查）。
- `resolve(schema_name)` 查 `schema_pg_routing`：命中返回对应实例；未命中返回默认实例。
- 路由结果带短 TTL 缓存（如 60s），避免每请求查表；管控面改路由后主动失效缓存。

**3. backend 选择层改动（核心改动，集中一处）**

现状（`memory_engine.py`）：
```python
self._backend: DatabaseBackend | None = None   # 单实例

async def _get_backend(self) -> DatabaseBackend:
    return self._backend
```

改为：
```python
self._router: SchemaRouter                       # per-instance pool 池
self._default_backend: DatabaseBackend           # 未映射回退

async def _get_backend(self) -> DatabaseBackend:
    schema = get_current_schema()                # contextvar
    instance = self._router.resolve(schema)
    if instance is None:
        return self._default_backend             # opt-in 回退
    return self._router.get_pool(instance.id)    # 按 schema 选实例
```

**这是核心改动的全部**——一处集中的 backend 选择层。记忆写入、recall 检索、图谱遍历的代码不变（它们只调 `_get_backend()` + `fq_table()`，不知道也不关心连的是哪个 PG）。

**4. 迁移 fan-out 跨实例**

现状：`run_migrations_for_schemas(schemas, concurrency)` per-schema 并发，假设单实例。

改为：按实例分组，每个实例内继续 per-schema 并发：
```python
for instance, schemas_in_instance in group_by_instance(tenants):
    run_migrations_for_schemas(schemas_in_instance, instance_pool=...)
```
- Alembic 迁移本就 schema-aware（per-tenant `search_path`），跨实例只是多连几个库跑同一套迁移。
- 每实例的迁移版本独立跟踪（一个实例可停留在 v50，另一个到 v104，互不影响）。

**5. worker 跨实例调度**

现状：`list_tenants()` 返回 schema 列表，worker per-tenant 轮询 claim。

改为：`list_tenants()` 返回 `(schema, pg_instance)`，worker 跨实例轮询、per-tenant 公平调度。Hindsight 已有"per-tenant fair rotation"，加实例维度是同构扩展。

**6. 读副本（per-instance）**

现状：`HINDSIGHT_API_READ_DATABASE_URL` 单值。

改为：`pg_instances.read_url` per-instance，`_get_read_backend()` 按 schema 选对应实例的读副本。Hindsight 读副本本就是一等公民，per-instance 化即可。

**7. 新租户分配策略（管控面）**

- 默认：容量优先，分配到当前最空的 active 实例。
- 大租户：可指定独占一个实例（物理隔离 + 性能保障）。
- 小租户：共享一个实例的多 schema（成本优化）。
- 实例容量阈值（存储/连接数/schema 数）触发预警，管控面决定是否加实例。

### low level 设计（实现过程同步刷新）

> 本节随实现推进填充，是 high level 设计落到代码级的产物。每完成一个组件的实现，把它的 low level 细节（类/方法签名、SQL、改动点、边界处理）写到这里，保证设计文档与代码同步。
> **状态：首期实现完成，13 项验证全通过（详见 `2026-09-30-Hindsight多PG实例验证报告.md`）。**

**1. 路由数据模型（表）**

- [x] `schema_pg_routing` / `pg_instances` / `pg_instance_metrics` 三表 DDL 脚本（含索引）—— `hindsight_pg_routing_schema.sql`
- [x] 初始化脚本：把当前单实例登记为默认 `pg_instance`（`pg-default`），不强制迁移任何 schema —— `hindsight_init_meta_db.sh`
- [x] 字段：见 high level 表定义，含静态规格、实例状态机、schema 迁移态、metrics 时序
- 落地：meta 库 `hindsight_meta`（首期在默认 pg0 实例内，独立 DB）。三表 + FK `schema_pg_routing.pg_instance_id → pg_instances` + 索引 `idx_schema_pg_routing_instance`。初始化只插 `pg-default` 一行，**不插任何 routing 行** → opt-in 回退。

**2. SchemaRouter（新增模块 `engine/schema_router.py`）**

- [x] 类设计：`SchemaRouter`，构造参数（元库连接串、默认实例 id、TTL、pool 规格、`init_callback_builder`、`default_backend`、`default_dsn`）+ `@dataclass PgInstance`
- [x] 方法签名：`resolve(schema) -> PgInstance | None`、`warm(schema)`、`backend_for_schema(schema)`（sync）、`read_backend_for_schema(schema)`（sync）、`get_pool(pg_instance_id)`、`get_backend_for_schema(schema)`（async）、`get_read_backend_for_schema(schema)`（async）、`group_schemas_by_instance(schemas)`、`invalidate(schema)` / `invalidate_all()`、`reload_instances()`、`migrate_schema(...)`（stub）、`initialize()` / `shutdown()`
- [x] per-instance asyncpg pool 懒初始化（`get_pool` 带 `asyncio.Lock` 双检）+ 健康检查（`is_ready`）
- [x] 路由结果 TTL 缓存（默认 60s，`schema → (instance|None, ts)`）+ 主动失效（`invalidate`）
- [x] 边界：实例 `status` 只 active/draining 服路由；schema `schema_state` 仅留字段，首期非 active 回退默认 + log（draining/retired/migrating_* 切换逻辑留口子）
- **关键设计**：sync/async 分裂。`resolve()`（async，查 meta）填充 sync TTL 缓存；`backend_for_schema()`（sync，只读缓存，miss→默认）给 3 个 `pool_getter` lambda 用。warm 在 `_authenticate_tenant` + `_execute_task`（两个学到 schema 的 async 点）调用。路由层不假设版本一致。
- 模块级函数 `resolve_migration_groups(meta_url, schemas, default_dsn, default_instance_id) -> {dsn: [schemas]}`，供迁移路径直接用（迁移时 router 尚未构造）。

**3. backend 选择层改动（核心，集中一处）**

- [x] `memory_engine.py`：新增 `self._router`（None 除非 meta 配置）；`self._backend` 保留（= 默认实例 pool，作为 opt-in 回退目标，不删）
- [x] `_get_backend()` 改为按 contextvar schema 选实例 pool（router None 时返回 `self._backend`）
- [x] `_get_read_backend()` 同理按 schema 选实例的 read_url pool
- [x] grep 所有 `_get_backend()` 调用点，确认行为不变（router None 时拿同一 backend）
- [x] **不改** `engine/search/`、`engine/retain/`、`engine/memories/` 等核心目录
- **关键发现并处理**：3 个 `pool_getter=lambda: self._backend` 子系统（`BrokerTaskBackend` / `AuditLogger` / `LLMTraceRecorder`）+ file storage **绕过 `_get_backend()`**，写 schema 限定表。已改为 `pool_getter=self._pool_for_current_schema`（sync，读 TTL 缓存）。warm 在 `_authenticate_tenant:2896` + `_execute_task:3979`（set schema 后）。`_get_pool()` 亦走 `_pool_for_current_schema().get_pool()`。cache miss → 默认（pg1 无该 schema → 查询 fail-fast，不静默跨实例写坏数据）。

**4. 迁移 fan-out 跨实例**

- [x] 在 caller `memory_engine.initialize()` 的 PG 分支按实例分组：`resolve_migration_groups` → 每实例 `run_migrations_for_schemas(instance_dsn, inst_schemas, ...)`，`asyncio.gather` 跨实例并发
- [x] 保持 per-schema per-process（`run_migrations_for_schemas` 本身**未改**，仍 per-schema 进程并发）
- [x] `migration_database_url` per-instance：默认实例用配置的 bypass URL，非默认实例回退自身 DSN（首期无 per-instance pgbouncer bypass，TODO）
- [x] 版本表：保持 per-schema `alembic_version`，天然跟 schema 走（实测 pg2 上 `user_company2.alembic_version` = head，pg1 无）

**5. worker 跨实例调度**

- [x] `list_tenants()` 不改（返回 `Tenant(schema, tenant_id)`）；instance 由 router 解析（不动共享 `Tenant` dataclass）
- [x] poller `claim_batch` 加 `_claim_batch_multi_instance`：`group_schemas_by_instance` → 每实例在其 pool 上 acquire 一条连接跑 `_claim_batch_on_conn`
- [x] 保留现有 "per-tenant fair rotation" 语义（每实例组内跑原轮转逻辑）；availability 跨实例共享计账户
- 实例 down：该实例 acquire 报错被吞 + log，其他实例继续 claim（首期简单处理）

**6. 读副本 per-instance**

- [x] `_get_read_backend()` / `get_read_backend_for_schema` 按实例 `read_url` 选 pool（懒建 read_backend）
- [x] 未配 read_url 的实例回退该实例主 pool（实测：pg2 配 read_url → 独立 read pool；默认无 read_url → 主 pool）

**7. 配置与默认实例**

- [x] `HINDSIGHT_API_DEFAULT_PG_INSTANCE`（默认实例 id，回退用）
- [x] `HINDSIGHT_API_META_DATABASE_URL`（路由表元库连接串）
- [x] 默认实例 pool 即当前 `self._backend` 初始化逻辑，向后兼容（router 把 `self._backend` 作为 `default_backend` 传入，不重复建 pool；`backend_owned_externally=True` 标记，shutdown 不关它）

**边界处理与回归点**（实现时逐项验证，13 项全通过）：
- [x] 路由表为空时 = 当前行为（opt-in 零回归）—— live service 重启（meta 未配）正常启动
- [x] schema 隔离不破（跨租户、跨实例）—— company1 key 读不到 company2 bank；marker 写入只落 pg2
- [x] bank 隔离不破（bank_id contextvar 不受路由层影响）
- [x] pgbouncer 事务模式适配不破（per-instance 下 GUC 重设仍生效）—— pg2 pool 底层 `_NoResetConnection` + `pg_trgm.similarity_threshold` per-acquire 生效
- [x] 跨租户全局例程（`fq_routine`）不跨实例假设
- [x] per-instance pool acquire/release 配对，无连接泄漏（5 并发后 size=5 idle=5）
- [x] 实例宕机有明确错误（不静默回退默认实例，防数据不一致）—— pg2 down → `ConnectionRefusedError`

### 首期留口子（未实现，接口/字段已留）

- `migrate_schema(schema, target_instance_id)` —— 签名留，抛 `NotImplementedError`（数据迁移第二阶段做）
- `pg_instances.status` draining/retired 切换逻辑 —— 字段已建，逻辑留口子
- `schema_pg_routing.schema_state` migrating_out/migrating_in/frozen 切换逻辑 —— 字段已建，逻辑留口子
- `hindsight_meta` 元库 HA —— 首期单库（在默认实例内），TODO
- bank 级扩展（方案 B）—— 首期不做
- per-instance `migration_database_url`（pgbouncer bypass）—— 非默认实例暂回退自身 DSN，TODO

### 灰度迁移路径

1. **零迁移起步**：路由表为空，所有 schema 回退默认实例 = 当前行为，零风险上线。
2. **加实例**：`pg_instances` 登记新实例，不迁移既有 schema，新租户分配到新实例。
3. **按 schema 迁移**：把源 schema 设为 `schema_state=migrating_out`（冻结写入或双写）→ 从源实例 `pg_dump` schema 级导出 → 导入目标实例 → 目标侧设 `migrating_in` → 验证 recall/retain → 路由表更新指向 + 两侧行 `schema_state` 复位 `active` → 清理源实例 schema。
4. **验证与回滚**：迁移期间双写或只读切换，验证后切流量；失败回滚路由表即可（数据仍在源实例）。
5. **逐步铺开**：按租户逐个迁移，每个独立、可回滚。

**风险隔离**：任一租户迁移失败不影响其他租户；按租户粒度灰度。

### 触发扩展的判定

何时需要加实例（单 PG 不满足的信号）：
- **存储**：单实例磁盘占用 > 70%，或某大租户数据量占整体 > 50%（应独占实例）。
- **性能**：recall p95 延迟上升、写吞吐触顶、连接池耗尽、HNSW 索引构建慢到影响在线。
- **故障域**：单实例故障影响租户数超过容忍阈值，需拆分。
- **隔离诉求**：大客户要求物理隔离。

---

## 四、过程中的思考与遗留问题

### 关于扩展粒度

方案 A（schema 级）的粒度是租户。云化主场景"大客户撑爆单库"对症。但有一个边界场景：**单租户内数据极度不均**——某租户 10 个 bank，其中 1 个占 90% 数据。方案 A 要为这 1 个 bank 迁整个 schema（连带其他 9 个小 bank）。

短期用"给该 schema 独占实例"缓解（方案 A 极端形态）。长期若这类场景普遍，才值得做方案 B（bank 级）。**不建议首期做方案 B**：bank 物理解绑 + worker 调度模型改造，代价高且与"不碰核心"原则相悖。

### 关于路由表的放置

路由表放哪有两个选项：
- **独立元数据库**（如 `hindsight_meta`）：与业务数据分离，单点但轻量，适合路由表本身很小的场景（行数 = schema 数）。
- **每个 PG 实例都有一个 `hindsight_meta` schema**：路由表多副本，需同步。复杂，不推荐首期。

首期选独立元数据库即可。若担心单点，可上 RDS/GaussDB 主备。遗留问题：元数据库自身的 HA 与路由表缓存失效协议（管控面改路由后如何让所有 API pod 立即生效），需在设计时定清楚。

### 关于 opt-in 回退

路由表未映射的 schema 回退默认实例，是零迁移起步的关键。但要防止"默认实例成为永久瓶颈"——新租户持续涌入默认实例而不分配。管控面必须强制"新租户走分配策略"，不能默认落默认实例。这个策略约束是管控面的责任，不在 Hindsight 核心。

### 关于连接池

per-instance pool 要求每个实例独立 asyncpg pool。实例数增长时，总连接数 = 实例数 × pool_max_size，可能反压 PG。需要：
- per-instance pool 大小按实例负载动态调整（小租户群共享实例的 pool 可小）。
- 连接复用与超时回收。
- 监控各实例连接池利用率。

遗留问题：实例数到什么量级需要引入连接池前置（如 pgbouncer per-instance）？Hindsight 原生已适配 pgbouncer transaction 模式，per-instance 加 pgbouncer 是成熟路径，但要评估运维成本。

### 关于 worker 调度

`list_tenants()` 从 schema 级加实例维度是同构扩展，但要注意：
- worker 要能感知实例健康（某实例宕机时，该实例的 task 不阻塞全局调度）。
- 公平调度要从"per-schema"升级成"per-(schema, instance)"，避免某实例任务堆积。
- 迁移中的 schema（`schema_state=migrating_out/migrating_in`）的 task 要暂停或路由到目标实例。

### 关于跨实例一致性

recall/retain 都是单 schema 单 bank，无跨实例事务需求。但有两个边缘点：
- **schema 迁移期间的一致性**：迁移中该 schema 若有写入，要冻结或双写。靠 `schema_state=migrating_out` 暂停写入（实例侧状态不承担此职责）。
- **路由表与实际数据的一致性**：路由表说 schema 在 PG2，但数据还在 PG1（迁移未完成）——靠 `schema_state` + 切流量时点控制，不在核心代码层保证。

### 遗留待定项

1. 路由表元数据库的 HA 方案。
2. per-instance 连接池大小的动态调优策略。
3. 实例容量阈值的具体数值（存储/连接/schema 数）。
4. 迁移期间的双写 vs 只读切换策略（取决于业务对停写的容忍度）。
5. 管控面与 SchemaRouter 的缓存失效协议。
6. 是否需要 bank 级扩展（方案 B）——待方案 A 上线后按真实场景判断。
