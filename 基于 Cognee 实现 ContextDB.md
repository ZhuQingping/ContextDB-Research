# 基于 Cognee 实现 ContextDB

## Cognee 是什么？

Cognee（柏林 Topoteretes UG，2024 年成立）是给 AI Agent 做**跨会话持久记忆**的引擎，Python 实现（3.10–3.14）。

Cognee 是当前**最热的开源 Agent 记忆层**（GitHub 实测 30,949 star / 3,094 fork），Apache-2.0 协议、法律上完全可以用来做托管服务；但它是典型的 **open-core + 公司强主导**项目——核心流水线开源，**"单 Postgres 跑完整记忆层"这条对你最有价值的路径被官方标为 demo feature，生产版是付费 license**。想拿它做服务化，技术上可行，存储层必须自己接。

## Cognee 提供了什么能力？



## 2 Cognee 使用 PG 作为后端存储

基于 PG 作为核心存储引擎。

```sql
cognee_db=# \l
                                                                   List of databases
                 Name                 |  Owner   | Encoding | Locale Provider |   Collate   |    Ctype    | Locale | ICU Rules |   Access privileges   
--------------------------------------+----------+----------+-----------------+-------------+-------------+--------+-----------+-----------------------
 cognee_db                            | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 085bcbef-f417-5975-b94e-65dbb49e9e6d | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 2e546fe0-9f26-5466-a3c9-fdce38e6a114 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 594f1f26-682d-5d8a-ac49-5e5c0cc49bea | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 5ac69798-d8ac-5b94-8d2c-e0dcbdf4e9d2 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 64485146-ce9e-5e21-bb99-b13a5344a408 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 9b404354-85aa-56e8-87ae-f9864f261286 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 9c4ac74a-2b42-554b-95a1-7ed4f7022cae | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 adf8a399-d70f-578b-8c0c-60161b5fbc60 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 b8077ee9-07e5-54aa-a857-01214efbd7e8 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 d7194d51-061d-5954-b010-2e59e64b1c41 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 ed567df0-eb34-5dd1-8361-e038f23ad01d | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
```

### 2.1 Cognee 元数据存储

**Cognee** 元数据保存在 PG 数据库 `cognee_db` 中，包含 用户/租户/角色/ACL/dataset 登记 │ users, tenants, roles, acls, datasets, dataset_database, principals, user_roles, user_tenants 等 40 张数据表中。

```
cognee_db=# \c cognee_db
You are now connected to database "cognee_db" as user "postgres".
cognee_db=# \dn
      List of schemas
  Name  |       Owner       
--------+-------------------
 public | pg_database_owner
(1 row)

cognee_db=# \dt
                     List of tables
 Schema |            Name            | Type  |  Owner   
--------+----------------------------+-------+----------
 public | acls                       | table | postgres
 public | alembic_version            | table | postgres
 public | cache_kv                   | table | postgres
 public | cache_qa_entries           | table | postgres
 public | cache_session_context      | table | postgres
 public | cache_trace_entries        | table | postgres
 public | cache_usage_logs           | table | postgres
 public | data                       | table | postgres
 public | dataset_configurations     | table | postgres
 public | dataset_database           | table | postgres
 public | datasets                   | table | postgres
 public | edges                      | table | postgres
 public | global_database_version    | table | postgres
 public | graph_metrics              | table | postgres
 public | graph_relationship_ledger  | table | postgres
 public | integration_credentials    | table | postgres
 public | nodes                      | table | postgres
 public | notebooks                  | table | postgres
 public | permissions                | table | postgres
 public | pipeline_runs              | table | postgres
 public | principal_configuration    | table | postgres
 public | principals                 | table | postgres
 public | provenance_edge_evidence   | table | postgres
 public | provenance_entries         | table | postgres
 public | queries                    | table | postgres
 public | results                    | table | postgres
 public | role_default_permissions   | table | postgres
 public | roles                      | table | postgres
 public | session_model_usage        | table | postgres
 public | session_records            | table | postgres
 public | sync_operations            | table | postgres
 public | tenant_default_permissions | table | postgres
 public | tenants                    | table | postgres
 public | tool_connections           | table | postgres
 public | tool_write_proposals       | table | postgres
 public | user_api_key               | table | postgres
 public | user_default_permissions   | table | postgres
 public | user_roles                 | table | postgres
 public | user_tenants               | table | postgres
 public | users                      | table | postgres
(40 rows)
```

关键的元信息表有

| 你的云概念                                             | cognee 对应         | 所在表                          | 关键属性                                                     | 说明                                                   |
| ------------------------------------------------------ | ------------------- | ------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------ |
| 一家公司 / 一个云账号(Company1)                        | **tenant(租户)**    | `tenants`                       | `id`, `name`, `owner_id`                                     | 顶级隔离边界。Company1 / Company2 = 两个 tenant        |
| 公司的管理员账号                                       | tenant 的 **owner** | `tenants.owner_id` → `users.id` | 创建该 tenant 的 user 自动是 owner                           | 有管理本租户的权限                                     |
| 公司里的部门/职位(开发、测试、运维 / 财务、物流、经理) | **role(角色)**      | `roles`                         | `id`, `name`, `tenant_id`(必填)                              | 权限分组,**必须属于一个 tenant**                       |
| 公司里的具体员工(张三、李四)                           | **user(用户)**      | `users`                         | `id`, `email`, `hashed_password`, `is_superuser`, `tenant_id`(当前活动租户), `parent_user_id` | 可属多个 tenant、多个 role                             |
| 一个工作项目 / 知识库                                  | **dataset(数据集)** | `datasets`                      | `id`, `name`, `owner_id`, `tenant_id`                        | 实际数据所在,**每个 dataset 一个独立 PG 库**(物理隔离) |
| 项目权限(谁能读写哪个项目)                             | **ACL(授权)**       | `acls`                          | `principal_id`, `permission_id`, `dataset_id`                | `principal_id` 指向 `principals`(可以是 user 或 role)  |

**(1) Company1(开发/测试/运维)**

```
tenant: Company1                          (owner = Company1 管理员 user)
├─ roles:
│    ├─ "dev"  (开发)
│    ├─ "test"(测试)
│    └─ "ops" (运维)
├─ users:
│    ├─ 管理员(Company1 owner)
│    ├─ 张三  ──> user_roles 加进 "dev"
│    └─ 李四  ──> user_roles 加进 "test"
└─ datasets(工作项目,各自独立 PG 库,tenant_id=Company1):
     ├─ "proj_dev_x"   ACL: role "dev"  可 read/write      ← 开发专属项目
     ├─ "proj_test_y"  ACL: role "test" 可 read/write      ← 测试专属项目
     └─ "shared_docs"  ACL: role "dev"+"test" 都可 read     ← 共享项目
```

**(2) Company2(财务/物流/经理)**

```
tenant: Company2                          (owner = Company2 管理员 user)
├─ roles:
│    ├─ "finance"(财务)
│    ├─ "logistics"(物流)
│    └─ "manager"(经理)
├─ users:
│    └─ 王五 ──> user_roles 加进 "finance"
└─ datasets(各自独立 PG 库,tenant_id=Company2):
     ├─ "finance_db"   ACL: role "finance" 可 read/write
     └─ "logistics_db" ACL: role "logistics" 可 read/write
```

**数据库查询**

```
-- 查看租户信息
select * from public.tenants;
-- 查看用户信息
select tenant_id, email, is_active, is_superuser, is_verified from public.users;
-- 查看角色信息
select * from public.roles;
-- 查看 datasets
select * from public.datasets;
```

**隔离效果**

- 租户间隔离，Company1 的张三(`active tenant=Company1`)默认**只能看到 `tenant_id=Company1` 的 dataset**,看不到 Company2 的任何项目。

- 租户内可以设置共享，也可以设置隔离，通过权限进行控制。

  ```
    ┌──────────┐   ┌──────────┐         ┌──────────┐   ┌──────────┐
    │  客户 1   │   │  客户 2   │         │  客户 3   │   │  客户 4   │
    │ Tenant A │   │ Tenant B │         │ Tenant C │   │ Tenant D │
    └─────┬────┘   └─────┬────┘         └─────┬────┘   └─────┬────┘
          │              │                    │              │
          └──────┬───────┘                    └──────┬───────┘
                 │                                   │
            ┌────▼─────┐                        ┌────▼─────┐
            │ cognee1  │                        │ cognee2  │
            │ 服务实例  │                        │ 服务实例 │
            └────┬─────┘                        └────┬─────┘
                 │                                   │
                 ▼                                   ▼
       ┌──────────────────┐               ┌──────────────────┐
       │ cognee1 专属存储  │               │ cognee2 专属存储  │
       │ (关系+图+向量)    │               │ (关系+图+向量)    │
       └──────────────────┘               └──────────────────┘
  ```

  

### 2.2 Cognee 用户数据存储

客户侧数据按 dataset 维度独立分库,每个 dataset 一个独立 PG 数据库。例如，该数据库中包含了 11 个 dataset，包含11个独立的 PG 数据库。

```
cognee_db=# \l
                                                                   List of databases
                 Name                 |  Owner   | Encoding | Locale Provider |   Collate   |    Ctype    | Locale | ICU Rules |   Access privileges   
--------------------------------------+----------+----------+-----------------+-------------+-------------+--------+-----------+-----------------------
 cognee_db                            | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 085bcbef-f417-5975-b94e-65dbb49e9e6d | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 2e546fe0-9f26-5466-a3c9-fdce38e6a114 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 594f1f26-682d-5d8a-ac49-5e5c0cc49bea | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 5ac69798-d8ac-5b94-8d2c-e0dcbdf4e9d2 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 64485146-ce9e-5e21-bb99-b13a5344a408 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 9b404354-85aa-56e8-87ae-f9864f261286 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 9c4ac74a-2b42-554b-95a1-7ed4f7022cae | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 adf8a399-d70f-578b-8c0c-60161b5fbc60 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 b8077ee9-07e5-54aa-a857-01214efbd7e8 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 d7194d51-061d-5954-b010-2e59e64b1c41 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           | 
 ed567df0-eb34-5dd1-8361-e038f23ad01d | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |        |           |
```

单个 dataset 专属库内包含10个表(以 proj_dev_x  `0085bcbef-f417-5975-b94e-65dbb49e9e6d`)


#### (1) 向量检索表(pgvector)

这些是 pgvector 的 collection(集合)表,每个集合存一类 DataPoint 的向量(1024 维)+ payload:

| 表名                         | 存什么                                  |
| ---------------------------- | --------------------------------------- |
| `DocumentChunk_text`         | 文档切片的向量(原文 chunk 的 embedding) |
| `TextSummary_text`           | 文档摘要的向量                          |
| `TextDocument_name`          | 文档元信息的向量(文档名)                |
| `Entity_name`                | 实体的向量(抽取出的实体名)              |
| `EntityType_name`            | 实体类型的向量(如"技术"、"概念")        |
| `EdgeType_relationship_name` | 关系类型的向量(如 uses/made_from)       |
| `SessionQAVector_text`       | 会话问答的向量(用于会话记忆检索)        |

每张向量表的列结构都是:`id (uuid)` + `payload (json)` + `vector (1024维)`。已验证 `vector_dims(vector)=1024`。

#### (2) 知识图谱表(postgres_demo)

| 表名             | 存什么                                                       |
| ---------------- | ------------------------------------------------------------ |
| `graph_node`     | 图的节点。每个节点是一个实体/摘要/文档等                     |
| `graph_edge`     | 图的边(关系)。`source_id → target_id` 用 `relationship_name` 连 |
| `graph_metadata` | 图级键值元数据(如删除模式标记)                               |

**postgres_demo** 是"把关系元数据、PGVector 向量、图状态塞进同一个 Postgres 服务"的演示用图后端。基本图存储能力齐全，但不支持图查询语言、性能不可扩展、多个生产接口未实现，官方代码已明确标注 demo、不建议生产使用。

官方建议生产用 Kuzu(Ladybug)或 Neo4j 这类图原生后端。

```python
"""cognee/infrastructure/databases/graph/postgres_demo/adapter.py"""
"""Postgres graph adapter using two tables (graph_node, graph_edge) over SQLAlchemy + asyncpg.

DEMO: Using Postgres as a graph store is currently a demo feature and is not
production-ready. Use it to demo keeping relational metadata, PGVector, and graph
state in a single Postgres service, but rely on a graph-native backend such as Kuzu or Neo4j
for production workloads.

Interested in further development or production use of Postgres as a graph database? Write to
us at social@cognee.ai to explore the options.
"""
```

**功能性缺口**

  - ❌  不支持 Cypher 查询（query() 直接 NotImplementedError）→ 自然语言搜索不可用
  - ❌  不自带向量检索，依赖独立的 PGVector 适配器
  - ❌  6 个生产接口未实现：节点/边的 feedback weights、truth state、update_node（部分属性更新）均继承 NotImplementedError → 反馈学习、真值子系统、节点更新走不通

**性能不可扩展（核心风险）**

  - get_filtered_graph_data：全表扫描 + Python 端逐行过滤，500 万节点会全载入内存
  - get_graph_metrics：整图载入内存算连通分量，且 diameter/avg_shortest_path/avg_clustering 三个指标永久返回 -1
  - get_graph_data：无分页全扫描
  - 多处 N+1 查询：has_edges、delete_edge_triples、provenance 更新（每行一次锁+更新）
  - 多跳遍历用 N 条顺序 SQL，无递归 CTE（图原生库一条 CTE 搞定）
  - 全局 advisory lock 串行化所有写操作，跨 dataset 也串行，无写并发
  - 连接池 pool_size=2 per dataset，写队列会占满
  - top-degree 采样用物理前缀 20 万行，会系统性漏掉近期热点节点

 **商用建议**

  - 不要直接上 postgres_demo。生产图负载用图原生后端（Kuzu/Ladybug 或 Neo4j)。
  - 其真实价值在"三库合一的 PoC/演示场景"：单一 Postgres 同时演关系元数据 + PGVector + 图，部署简单。
  - 若强行商用，需补齐：Cypher/NL 查询、6 个未实现接口、递归 CTE 重写遍历、N+1 批量化、分页、写并发、name 索引——工作量等同重写一遍图引擎，不划算。

#### (3) 两类表怎么配合(检索时)

`recall` 时:

1. 用你的问题算向量 → 在 `DocumentChunk_text`/`Entity_name` 等表里做**向量相似度检索**,找到相关 chunk/实体;
2. 拿这些实体 id → 在 `graph_node`/`graph_edge` 里**图遍历**找邻居关系;
3. LLM 用这些上下文生成答案 → 存进 `SessionQAVector_text`(会话记忆)。



### 2.3 用户数据膨胀，PG横向扩展

随着客户量两增长，希望做到存储层 PG 横向扩展，新租户用新 PG 实例，达到以下效果：

```
  ┌──────────┐   ┌──────────┐         ┌──────────┐   ┌──────────┐
  │  客户 1   │   │  客户 2   │         │  客户 3   │   │  客户 4   │
  │ Tenant A │   │ Tenant B │         │ Tenant C │   │ Tenant D │
  └─────┬────┘   └─────┬────┘         └─────┬────┘   └─────┬────┘
        │              │                    │              │
        └──────┬───────┘                    └──────┬───────┘
               │                                   │
               ▼                                   ▼
     ┌───────────────────────────────────────────────────┐
     │            cognee1  (单个服务实例)                  │
     │   接入层按 tenant 路由:                             │
     │     Tenant A / B  ─────────────►  PG1             │
     │     Tenant C / D  ─────────────►  PG2             │
     └──────────┬──────────────────────────┬─────────────┘
                │                          │
                ▼                          ▼
       ┌─────────────────┐         ┌─────────────────┐
       │   PG 实例 1      │         │   PG 实例 2      │
       │      PG1        │         │      PG2         │
       │  ┌────────────┐ │         │  ┌────────────┐  │
       │  │ 关系库共享  │  │         │  │ 关系库共享  │   │
       │  │ users·ACL  │  │         │  │ users·ACL  │  │
       │  │ 注册表      │  │         │  │ 注册表      │  │
       │  ├────────────┤  │         │  ├────────────┤  │
       │  │A:Graph+Vec │  │         │  │C:Graph+Vec │  │
       │  │B:Graph+Vec │  │         │  │D:Graph+Vec │  │
       │  └────────────┘  │         │  └────────────┘  │
       └─────────────────┘         └─────────────────┘
```

当前 **Cognee** 代码并不支持，原因如下：

#### **(1) PG 数据库信息保存在本地配置文件 `.env`**

**Cognee** 的数据库连接信息(IP/Port/user/password)从 .env 文件读取,通过 lru_cache 单例全局生效，PG 数据库连接信息无对应的运行时 setter,不支持动态切换,需改 `.env` 后重启服务才生效。

```
[ci@localhost cognee]$ cat .env
# -----------------------------------------------------------------------------
# Relational DB (users, ACLs, dataset-database registry) — Postgres on 5433.
# -----------------------------------------------------------------------------
DB_PROVIDER="postgres"
DB_HOST="127.0.0.1"
DB_PORT="5433"
DB_USERNAME="postgres"
DB_PASSWORD="postgres"
DB_NAME="cognee_db"

# -----------------------------------------------------------------------------
# Vector DB — PGVector on the same Postgres. Per-dataset isolation creates one
# Postgres database per dataset (handler auto-selected: pgvector). The per-dataset
# engine connects to database "<dataset_id>", so VECTOR_DB_URL here is the
# template/base the handler reuses for host/port/user/pass.
# -----------------------------------------------------------------------------
VECTOR_DB_PROVIDER="pgvector"
VECTOR_DB_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/cognee_db"
VECTOR_DB_HOST="127.0.0.1"
VECTOR_DB_PORT="5433"
VECTOR_DB_USERNAME="postgres"
VECTOR_DB_PASSWORD="postgres"
VECTOR_DB_NAME="cognee_db"

# -----------------------------------------------------------------------------
# Graph DB — postgres_demo (graph-on-Postgres demo; no raw Cypher / NL search).
# Per-dataset isolation creates one Postgres database per dataset. The handler
# uses GRAPH_DATABASE_HOST/PORT/USERNAME/PASSWORD (not a URL).
# -----------------------------------------------------------------------------
GRAPH_DATABASE_PROVIDER="postgres_demo"
GRAPH_DATABASE_HOST="127.0.0.1"
GRAPH_DATABASE_PORT="5433"
GRAPH_DATABASE_USERNAME="postgres"
GRAPH_DATABASE_PASSWORD="postgres"

# -----------------------------------------------------------------------------
# Session cache — keep it on Postgres too (single backend = PG-only goal).
# -----------------------------------------------------------------------------
CACHE_BACKEND="postgres"
```

#### **(2) 创建 dataset 的默认 handler,host/port/user/pass 全取自全局配置`env`，只是库名随 dataset 变,不随租户变。**

参见代码：PGVectorDatasetDatabaseHandler.py

```python
# 第 25 行:配置只取全局单例
vector_config = get_vectordb_config()

# 第 34-40 行:在【全局配置的那一个 PG 实例】上建库,host/port/user/pass 全来自全局配置
await create_pg_database_if_not_exists(
    vector_db_name,
    host=vector_config.vector_db_host,         # ← 全局单值
    port=vector_config.vector_db_port,          # ← 全局单值
    username=vector_config.vector_db_username,  # ← 全局单值
    password=vector_config.vector_db_password,  # ← 全局单值
)

# 第 42-52 行:用全局连接串建引擎,只有库名(dataset_id)随 dataset 变
new_vector_engine = create_vector_engine(
    vector_db_url=vector_config.vector_db_url, # ← 全局单值
    vector_db_name=vector_db_name,             # ← 只有这个随 dataset 变
    ...
)
```

#### **(3) 如何支持 PG 数据库的横向扩展**

**思路**:加一张"租户→PG 实例"路由表,自定义 handler 查表决定连哪个 PG。

```
┌──────────────────────────────────────────────────────────┐
│  cognee_db (共享关系库)                                    │
│    ├ tenants           租户                               │
│    ├ datasets          数据集(已有)                        │
│    ├ dataset_database  每数据集的库登记(已有)                │
│    └ tenant_pg_routing  【新增】租户→PG实例映射表            │
│        (tenant_id → pg_instance_id → host/port/user/pass) │
└───────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
   PG实例A (Company1)               PG实例B (Company2)
   库: <dataset_id>                  库: <dataset_id>
```

新租户建租户时分配新 PG 实例 → 该租户后续所有 dataset 都落在它的 PG 上 → 租户间物理隔离 + 按租户水平扩容。

配合管控一起实现 PG 数据库的横向扩展功能。



## Cognee 开源版本的约束

Cognee 针对 PG 的图支持不完备，代码中明确说明未达到商用标准。

Cognee UI 只支持英文，暂不支持中文。

Cognee UI 接口支持不完备，部分功能未在开源支持。

![image-20260924160048009](C:\Users\z00835654\AppData\Roaming\Typora\typora-user-images\image-20260924160048009.png)



## 测试验证

局限 1:OSS 版没有租户管理 UI/HTTP API。 建 tenant、建 role 只能写 Python 脚本调内部函数,UI 里"建工作空间"按钮是云版空壳。要包装成云服务,这部分管理面得自己补。

局限 2:SDK 的 cognee.remember() 默认用 default_user 身份,不以指定租户用户身份写入。 我实测发现:用 SDK 写知识时,数据落到了"default_user 名下的 dataset 库",而不是目标租户的 dataset 库(那 5 个多租户 dataset 库是空的)。也就是说,OSS 
  版的多租户"写入"路径还没和租户身份打通——隔离(读)是好的,但"以某租户用户身份写入知识"在 SDK 层不直接支持,得绕(通过 HTTP API 带 token 才能正确按身份写)。

  给你的建议(汇报口径)

  - 隔离能力:cognee 多租户隔离(物理+逻辑双层)可用、已验证,适合做多租户云服务的底座。
  - 待补的能力:① 租户/用户管理 UI(HTTP 层+前端);② SDK 多租户写入路径(或统一走 HTTP API 带 token 写)。
  - 结论:cognee 后端权限模型完整,但 OSS 版离"开箱即用的多租户云服务"还差一个管理面 + 写入身份打通,需要二次开发或评估商用版。

## Cognee 本地部署验证

```
  访问 UI
  - UI 地址: http://10.83.11.134:3000(或本机 IP:3000)
  - 登录页: http://10.83.11.134:3000/local-login
  - 登录凭据: admin@cognee.example.com / Cognee@2026

```



### User

`admin@cognee.example.com` 是 User，可以登陆 UI  http://10.83.11.134:3000/datasets

### 实际测试效果

```
Company1: c1_admin@cognee.example.com/Company1@2026
Company1: li4@cognee.example.com/Test@2026
Company2: c2_admin@cognee.example.com/Company2@2026
Company2: wang5@cognee.example.com/Finance@2026
```



```
export COGNEE_BASE_URL="http://10.83.11.134:8100"
claude plugin marketplace add topoteretes/cognee-integrations

claude plugin install cognee-memory@cognee

```



