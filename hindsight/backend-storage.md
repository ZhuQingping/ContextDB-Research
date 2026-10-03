# Hindsight 后端存储格式调研报告
## —— 数据库连接、租户与记忆库、向量/全文/图存储、模型配置

> 分析对象：运行中的 Hindsight 容器 `zhuqingping_hindsight`（镜像 `hindsight-mt`）。
> 分析方法：基于容器内源码（`hindsight_api/config.py`、`pg0.py`、`db_url.py`、`engine/sql/postgresql.py`）、部署脚本（`.deploy-hindsight-mt/run-hindsight.sh`）、宿主 `.env`，以及**对运行中 PG 实库的实证查询**，非推测。
> 日期：2026-09-29

---

## 0. 结论速览（TL;DR）

| 问题 | 结论 |
|------|------|
| **Hindsight 怎么知道数据存到 PG?** | 配置默认值 `DEFAULT_DATABASE_URL = "pg0"`（config.py），走 `pg0-embedded` 库**自启动一个嵌入式 PostgreSQL**，不连外部 DB。 |
| **PG 地址是多少?** | 容器内 `127.0.0.1:5432`，库 `hindsight`，用户/密码 `hindsight`/`hindsight`，版本 PG 18.1。 |
| **元数据（用户/API key/文档库）存哪?** | **两层混合**：用户与 API key 存在**环境变量 + 内存**（不在 PG，无 users 表、无外部 IdP）；记忆库(bank)存在 PG 的 `<租户>.banks` 表。 |
| **有几个用户 / 几个 API key?** | **2 个用户(company1/company2)、4 把 API key**(每用户 2 把,可多 key 映射同用户)。 |
| **API key 怎么验证?** | `StaticKeysTenantExtension`:把请求头 `Authorization: Bearer <key>` 与内存里的 key 列表做 `hmac.compare_digest`(常数时间)比较 → 命中则取对应 user_id 与 schema。 |
| **向量 / 全文 / 图存哪?** | 向量在 `memory_units.embedding`（`vector(1024)`，HNSW）；全文在 `memory_units.search_vector`（tsvector，GIN）；图在 `entities`（节点）+ `memory_links`/`entity_cooccurrences`/`unit_entities`（边与关联）。 |
| **有没有 `.env` 文件?** | 宿主 `/rri/zhuqingping/Code/ContextDB/hindsight/.env` 存在，但**未被实际采用**（指向外部 PG 的早期版本）。实际部署脚本 `run-hindsight.sh` 用 `docker run -e` 直接注入全部配置，无 `.env`。 |
| **LLM / Embedding / Rerank 怎么配?** | 全部走容器环境变量 `HINDSIGHT_API_{LLM,EMBEDDINGS,RERANKER}_*`，在 `run-hindsight.sh` 中硬编码。 |

一句话：**Hindsight 不依赖外部数据库或配置文件——它自带嵌入式 PG，所有配置经环境变量注入；用户与 API key 存内存(非 PG)，文档库存 PG 的 `banks` 表，多租户按 schema 物理隔离，向量/全文/图三种检索数据都落在租户 schema 内的几张表上。**

---

## 1. 数据库：嵌入式 PostgreSQL，而非外部 DB

### 1.1 "pg0" 机制

Hindsight API 的数据库 URL 默认值在源码中硬编码为字符串 `"pg0"`（`config.py:1082`，`DEFAULT_DATABASE_URL = "pg0"`）。当 `HINDSIGHT_API_DATABASE_URL` 未设置时，URL 就是这个标记串。

`pg0.py` 中的 `resolve_database_url()` 解析这个标记：

```
"pg0"  →  启动 pg0-embedded 库的 Pg0，自起一个嵌入式 PostgreSQL 实例（实例名默认 "hindsight"，端口自动分配）
"pg0://name:port"  →  指定实例名与端口
"postgresql://..."  →  连外部 PG（本环境未采用）
```

所以"Hindsight 如何感知数据存到 PG"——**这是硬编码的默认行为，默认就走嵌入式 PG，不需要任何连接配置**。`pg0` 库在 `~/.pg0/` 下管理实例：`installation/18.1.0/`（PG 二进制）、`instances/hindsight/`（数据目录 + `instance.json` 元信息）。

### 1.2 实际 PG 地址（来自 instance.json + 进程实证）

`~/.pg0/instances/hindsight/instance.json` 记录运行时绑定：

| 项 | 值 |
|----|----|
| **地址** | `127.0.0.1:5432`（容器内本地） |
| **数据库** | `hindsight` |
| **用户 / 密码** | `hindsight` / `hindsight` |
| **版本** | PostgreSQL 18.1 |
| **数据目录** | `/home/hindsight/.pg0/instances/hindsight/data`（84 MB） |
| **持久化** | Docker volume `hindsight-pg0` 挂载到 `~/.pg0`，容器重建不丢数据 |
| **运行参数** | postgres 进程 `-F`（无 fsync，开发模式），`shared_buffers=256MB` |

连接池：asyncpg，min 5 / max 100，`statement_timeout=600s`。容器内看到的多个 `postgres: hindsight hindsight 127.0.0.1(xxxx) idle` 即池中空闲连接。

> 登录命令（即本调研所用）：
> `/home/hindsight/.pg0/installation/18.1.0/bin/psql -h127.0.0.1 -Uhindsight -p5432`（密码 `hindsight`）

---

## 2. 租户与记忆库

### 2.1 租户 = PG schema 物理隔离

租户来源于环境变量（由 `StaticKeysTenantExtension` 做 API-key→租户映射）：

```
HINDSIGHT_API_TENANT_USERS=company1:key-zhang3,company1:key-li4,company2:key-wang5,company2:key-xiao6
```

即 **2 个租户：company1、company2**。隔离方式是**一个租户一个 PG schema**：

| Schema | 归属 | 内容 |
|--------|------|------|
| `public` | 共享 | 元数据/迁移版本表，无租户业务数据（`public.banks` 为空） |
| `user_company1` | 租户 company1 | 完整一套 24 张业务表 |
| `user_company2` | 租户 company2 | 完整一套 24 张业务表（结构相同，数据各管各） |

每个租户 schema 拥有**完全相同的 24 张表**（DDL 一致，由 Alembic 按 schema 分别迁移）。这是干净的"schema-per-tenant"多租户隔离——跨公司物理隔离，公司内多用户共享同 schema。

### 2.2 记忆库（Bank）：共 2 个

记忆库记录在各租户 schema的 `banks` 表中：

| bank_id | 名称 | 所属 schema | internal_id | 配置 |
|---------|------|------------|-------------|------|
| `company1-project-alpha` | Company1 Project Alpha | `user_company1` | `837e664b-…` | 有 retain_mission / reflect_mission |
| `company2-project-gamma` | Company2 Project Gamma | `user_company2` | `73fc4be3-…` | reflect_mission |

`banks` 表存储记忆库的"性格与使命"：`disposition`（empathy/literalism/skepticism 三个性格维度）、`config`（retain_mission 提取规则、reflect_mission 反思规则）。`internal_id` 是 bank 的内部 UUID，后面会看到它被用作向量索引名的后缀（实现按 bank 分区的索引）。

> 与 ContextDB 概念对应：**租户 = schema，bank = `banks` 表一行**。

---

## 3. 向量 / 全文 / 图数据分别存哪张表

三种检索数据全部落在租户 schema 内。核心表是 **`memory_units`（记忆单元 = 一条结构化事实）**，向量与全文检索数据直接长在它身上；图数据在其邻接表上。

### 3.1 总览

| 检索类型 | 存储位置 | 类型 / 索引 | 说明 |
|---------|---------|------------|------|
| **向量** | `memory_units.embedding` | `vector(1024)` + HNSW | bge-m3 模型，1024 维 |
| **全文** | `memory_units.search_vector` | tsvector + GIN；实体名走 pg_trgm | 应用层计算填充，非触发器 |
| **图（节点）** | `entities` | uuid PK + 实体名 trigram | entity_kind: regular / label |
| **图（边）** | `memory_links`、`entity_cooccurrences` | — | 见 3.4 |

### 3.2 向量存储：`memory_units.embedding`

- 列类型 `vector(1024)`（pgvector 扩展，对应 bge-m3 的固定 1024 维）。
- 索引：HNSW（`vector_cosine_ops`，余弦相似度）。**每个 bank 建 4 个索引**——1 个通用 + 3 个按 `fact_type` 分区的部分索引：
  - `idx_memory_units_embedding_hnsw`（通用）
  - `idx_mu_emb_worl_837e664b…`（world 类事实）
  - `idx_mu_emb_obsv_837e664b…`（observation 类）
  - `idx_mu_emb_expr_837e664b…`（experience 类）
  
  后缀 `837e664b…` 即 bank 的 `internal_id`。**这种"按 fact_type + bank_id 分区建 HNSW"的设计，让召回既缩小搜索空间又按 bank 隔离。**
- 注意：`chunks` 表（源文本切片）**没有 embedding 列**，它只是保留原始切片文本供溯源，向量化只发生在 `memory_units`。

### 3.3 全文存储：`memory_units.search_vector`

- 列类型 `tsvector`，GIN 索引 `idx_memory_units_text_search`。
- **没有触发器、也没有列 DEFAULT**——`search_vector` 由应用层在写入时计算并填充（`engine/sql/postgresql.py` 中查询用 `to_tsquery('english', ...)` + `ts_rank_cd` 打分；另一后端可走 VectorChord BM25）。
- 实体名模糊匹配另走 pg_trgm：`entities_canonical_name_lower_trgm_nonlabel_idx`（GIN，对小写实体名建三元组索引）。

### 3.4 图存储：节点 + 两类边

图数据由三张表协同表达：

**节点** —— `entities`：每个实体一行（uuid、canonical_name、entity_kind ∈ {regular, label}、mention_count、首末出现时间）。company1 实测 323 个节点（全 regular）。

**边** 分两张表：

1. `memory_links` —— 记忆单元之间的有向边（company1 实测 **4079 条**）：
   - `from_unit_id` → `to_unit_id`，`link_type ∈ {temporal, semantic, entity, causes, caused_by, enables, prevents}`，`weight` 0~1。
   - 实测分布：temporal 2583 / semantic 1487 / caused_by 9。
   - 这是记忆的"关系图"——时间先后、语义相似、因果使能等。

2. `entity_cooccurrences` —— 实体之间的共现统计（company1 实测 1391 条）：`entity_id_1` ↔ `entity_id_2`、`cooccurrence_count`、`last_cooccurred`。这是实体级的"共现图"。

**关联表** `unit_entities`：哪条记忆单元提到了哪个实体（记忆↔实体的多对多）。

> 三种检索不是割裂的：recall 时可同时跑向量召回 + 全文 BM25/ts_rank + 图遍历，由 `engine/sql/postgresql.py` 合并打分。

### 3.5 实测数据量（company1 有真实数据，company2 基本为空）

| 表 | company1 | company2 |
|----|---------|----------|
| memory_units | 287（world 174 / observation 82 / experience 31） | ~2 |
| documents | 15 | 0 |
| chunks | 50 | 0 |
| entities（图节点） | 323 | 4 |
| memory_links（图边） | 4079 | 0 |
| entity_cooccurrences | 1391 | 0 |
| unit_entities | 930 | 0 |

已安装扩展：`vector 0.8.5`（pgvector）、`pg_trgm 1.6`、`plpgsql`。

---

## 4. 模型配置：LLM / Embedding / Rerank

### 4.1 关于 `.env` 文件：存在但未被实际采用

- **容器内无 hindsight 的 `.env` 文件**（`find /app /home/hindsight -name ".env*"` 仅找到 `/home/ci/LLMProxy/.env`，那是 LLM 网关的域账号，与 hindsight 无关）。
- **宿主 `/rri/zhuqingping/Code/ContextDB/hindsight/.env` 存在**（即安装时看到的那份），但它是**指向外部 PG 的早期版本配置**：
  - `HINDSIGHT_API_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/hindsight`
  - 端口 8420/8424
- **实际部署脚本 `.deploy-hindsight-mt/run-hindsight.sh` 没有使用这份 `.env`**，而是用 `docker run -e ...` **直接硬编码注入所有环境变量**（端口 8888/9999，DB 走嵌入式 pg0，用户 hindsight）。

> 结论：**当前运行实例不读 `.env`**。`.env` 是历史遗留，与实际运行配置不一致（DB、端口、用户都对不上）。真正生效的配置来源是 `run-hindsight.sh` 里的 `docker run -e` 参数。

### 4.2 实际生效的模型配置（来自 run-hindsight.sh / 容器 env）

三类模型全部走 `HINDSIGHT_API_*` 环境变量注入。配置模式统一：`PROVIDER` 选后端 + `PROVIDER` 专属的 `MODEL / BASE_URL / API_KEY`。

| 类别 | 环境变量 | 值 | 说明 |
|------|---------|----|------|
| **LLM** | `HINDSIGHT_API_LLM_PROVIDER` | `anthropic` | 走 Anthropic Messages API 协议 |
| | `HINDSIGHT_API_LLM_BASE_URL` | `http://127.0.0.1:31943` | **容器内本地 LLMProxy 网关** |
| | `HINDSIGHT_API_LLM_MODEL` | `codeagent/maas-glm-5.2-volcengine-codeagent` | GLM-5.2 |
| | `HINDSIGHT_API_LLM_API_KEY` | `none` | 网关不鉴权（接受 anthropic SDK 默认的 `x-api-key: none`） |
| | `HINDSIGHT_API_LLM_TIMEOUT` | `600` | 秒 |
| **Embedding** | `HINDSIGHT_API_EMBEDDINGS_PROVIDER` | `openai` | OpenAI 兼容协议 |
| | `HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL` | `https://api.modelarts-maas.com/v1` | 华为云 MaaS |
| | `HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL` | `bge-m3` | 固定 1024 维 |
| | `HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY` | `Ud26…XQ` | MaaS key |
| **Reranker** | `HINDSIGHT_API_RERANKER_PROVIDER` | `cohere` | Cohere rerank 协议 |
| | `HINDSIGHT_API_RERANKER_COHERE_BASE_URL` | `https://api.modelarts-maas.com/v1/rerank` | 华为云 MaaS |
| | `HINDSIGHT_API_RERANKER_COHERE_MODEL` | `bge-reranker-v2-m3` | |
| | `HINDSIGHT_API_RERANKER_COHERE_API_KEY` | `Ud26…XQ` | 与 embedding 共用同一 MaaS key |

### 4.3 LLM 调用链路（本地网关 → GLM）

```
Hindsight API
   │  Anthropic Messages 协议
   ▼
127.0.0.1:31943  ← 容器内 LLMProxy 网关（/home/ci/LLMProxy, entrypoint.sh 先起它并等 31943 就绪）
   │  经公司代理 172.18.100.92:8080 出网
   ▼
上游 GLM-5.2 模型
```

- `entrypoint.sh` 的启动顺序：**先起 LLMProxy 网关 → 轮询等 `127.0.0.1:31943` 可连接 → 再 exec Hindsight 的 `start-all.sh`**。因为 Hindsight 的 embedding/reranker 探测和 LLM 调用都要打这个网关，必须先就绪。
- 出网：容器经 `HTTP(S)_PROXY=http://z00835654:***@172.18.100.92:8080` 公司代理访问华为云 MaaS（embedding/reranker）；LLM 走本地网关。

### 4.4 两个易踩的坑（已在 run-hindsight.sh 注释中固化）

1. **bge-m3 不支持 `dimensions` 参数**：所以 `HINDSIGHT_API_EMBEDDINGS_OPENAI_DIMENSIONS` **故意不设**——设了会让 Hindsight 每次调用都带 `dimensions` 参数而被 MaaS 拒绝。留空则由启动探针用一个无参测试调用自动探测出 1024 维，pgvector 列在首次启动时自动 ALTER 到 1024。
2. **LLM model id 不带 `[1m]` 后缀**：那是 Claude Code 的上下文路由提示，网关会拒绝带后缀的 id，所以这里用裸 id `codeagent/maas-glm-5.2-volcengine-codeagent`。

---

## 5. 元数据存储：用户与 API key 在内存，文档库在 PG

> 本节回答："有几个文档库、有几个用户、API key 验证等信息存在哪?" 这是多租户与鉴权的核心，前面章节只讲了业务表，这里补齐元数据层。

### 5.1 关键结论：元数据是"两层混合"

Hindsight **没有 users 表、没有 api_keys 表、没有外部身份提供商(IdP)**。元数据按性质分两层存放：

| 元数据 | 存储位置 | 是否落 PG |
|--------|---------|-----------|
| **用户(user)与 API key** | 环境变量 `HINDSIGHT_API_TENANT_USERS` → 进程启动时解析进**内存 dict** | ❌ 不落 PG |
| **文档库(bank)** | PG 的 `<租户 schema>.banks` 表 | ✅ 落 PG |
| **租户(=schema)** | 由 user_id 派生:`user_<user_id>` | schema 本身即隔离边界 |
| **控制平面(CP)用户** | 无独立存储；CP 用 `key-zhang3` 调 API，落到同一套 | ❌ 不落 PG |

### 5.2 用户与 API key:来自环境变量,内存校验

**配置**(来自 `run-hindsight.sh`,硬编码注入)：

```
HINDSIGHT_API_TENANT_EXTENSION=hindsight_ext_static_keys_tenant:StaticKeysTenantExtension
HINDSIGHT_API_TENANT_USERS=company1:key-zhang3,company1:key-li4,company2:key-wang5,company2:key-xiao6
HINDSIGHT_API_TENANT_SCHEMA_PREFIX=user   # 默认值,生成 user_<id> schema
```

**所以:2 个用户、4 把 API key**:

| 用户(user_id) | API key | 对应 schema |
|--------------|---------|------------|
| company1 | `key-zhang3`、`key-li4` | `user_company1` |
| company2 | `key-wang5`、`key-xiao6` | `user_company2` |

> 注意:**一个用户可持有多把 key**(company1 持 2 把),多把 key 映射同一用户/同一 schema——这是 `StaticKeysTenantExtension` 的设计卖点(便于轮换 key)。

**验证机制**(源码 `extensions/hindsight_ext_static_keys_tenant/extension.py`):

1. 客户端在请求头带 `Authorization: Bearer <api_key>`。
2. 扩展把该 key 与内存中全部已配置 key 逐一做 **`hmac.compare_digest`(常数时间比较)**——避免时序侧信道泄露 key 形状。
3. 命中 → 取该 key 对应的 `user_id` 与 `schema_name`，返回 `TenantContext(schema_name=user_<id>)`。
4. 未命中 → `AuthenticationError`(401)。
5. **首次访问某 schema 时懒加载**:加锁跑一次该 schema 的迁移(Alembic)，建出 24 张表，之后缓存"已初始化"标记。
6. MCP 通道(`authenticate_mcp`)走同一套，**不允许关闭鉴权**(扩展在启动期就拒绝 `HINDSIGHT_API_TENANT_MCP_AUTH_DISABLED`)。

> 计量用途:认证后会在 `RequestContext` 上设 `tenant_id`(=user_id)和 `api_key_id`(=key 的 sha256 前 16 位,**非 key 本身**),供用量统计,不会泄露明文 key。

### 5.3 文档库(bank):存在 PG 的 `banks` 表

文档库是业务概念,落 PG。每个租户 schema 的 `banks` 表一行 = 一个文档库:

| bank_id | schema | internal_id | 说明 |
|---------|--------|-------------|------|
| `company1-project-alpha` | `user_company1` | `837e664b-…` | company1 的共享记忆库 |
| `company2-project-gamma` | `user_company2` | `73fc4be3-…` | company2 的共享记忆库 |

`banks` 表字段(即"文档库元数据"):`bank_id`、`name`、`disposition`(性格:empathy/literalism/skepticism)、`config`(retain_mission/reflect_mission)、`internal_id`(内部 UUID,用作向量索引名后缀)、`mission`、时间戳。

**所以"有几个文档库"**:本部署共 **2 个文档库**,分布在 2 个租户 schema 各 1 个。`banks.bank_id` 同时是所有业务表(`memory_units`/`documents`/`chunks`/`entities`/`memory_links`...)的 `bank_id` 列,实现"同一 schema 内按文档库再分桶"。

### 5.4 关于 `public` schema:空壳,不是元数据中心

`public` schema 也有完整 24 张表(与租户 schema 同构),但**全部为空**(`public.banks` 0 行)。它是 `DefaultTenantExtension`(单租户无鉴权模式)的默认落点;本部署改用了 `StaticKeysTenantExtension` 多租户模式后,public 不再承载任何租户数据,只是建表模板/迁移基线。**元数据并不在 public,而在环境变量(用户/key)+ 各 `user_*` schema 的 `banks` 表(文档库)。**

### 5.5 控制平面(CP,端口 9999):不引入额外元数据存储

CP 是 Next.js 前端进程(`/app/control-plane`),**自带数据库**——它通过环境变量 `HINDSIGHT_CP_DATAPLANE_API_KEY=key-zhang3` 以 company1 的身份调用 API(8888)。所以 CP 上看到的用户/文档库/统计,全部来自同一个 API + 同一个 PG,**没有独立的 CP 用户库或元数据库**。

### 5.6 完整的"请求→鉴权→落库"链路

```
客户端请求
  │  Authorization: Bearer key-zhang3
  ▼
Hindsight API (8888)
  │  StaticKeysTenantExtension.authenticate()
  │   ├─ hmac.compare_digest(key)  ← 与内存 dict 比
  │   └─ 命中 → user_id=company1, schema=user_company1
  │            (首次访问:懒加载迁移建 24 表)
  ▼
TenantContext(schema_name=user_company1)
  │  后续所有 SQL 都在 user_company1 schema 下执行
  │  bank_id 列再从业务数据里分出 company1-project-alpha
  ▼
PG: user_company1.{memory_units, banks, entities, ...}
```

---

## 6. 与 ContextDB 概念的映射

| ContextDB 概念 | Hindsight 实现 |
|---------------|---------------|
| 数据库 | 嵌入式 PG（pg0），`127.0.0.1:5432` 库 `hindsight` |
| 租户隔离 | PG schema（`user_<tenant>`） |
| 用户与 API key（元数据） | **不落库**——环境变量 `HINDSIGHT_API_TENANT_USERS` → 内存 dict，`hmac.compare_digest` 校验 |
| 文档库 / 命名空间 | `banks` 表一行（bank_id + internal_id） |
| 记忆单元 / 文档 | `memory_units` 表一行（含 text、embedding、search_vector） |
| 向量检索 | `memory_units.embedding`（vector(1024) + HNSW，按 fact_type/bank 分区） |
| 全文检索 | `memory_units.search_vector`（tsvector + GIN）；实体名 pg_trgm |
| 图检索 | `entities`（节点）+ `memory_links`（记忆边）+ `entity_cooccurrences`（实体共现） |
| 写入（retain） | Stop hook → POST memories → 入 memory_units（含向量化） |
| 读取（recall） | UserPromptSubmit hook → 向量+全文+图召回 → 注入 prompt |

**结论**：Hindsight 是一个"单库内多租户、三路检索（向量/全文/图）合一"的极简 ContextDB 后端——自带 PG、不依赖外部组件、配置全走环境变量，适合作为 Agent 记忆层的轻量落地形态。

---

## 附录 A：关键源码 / 文件位置

| 文件 | 作用 |
|------|------|
| `/app/api/hindsight_api/config.py` | 全部 `HINDSIGHT_API_*` 环境变量与默认值（`DEFAULT_DATABASE_URL="pg0"`） |
| `/app/api/hindsight_api/pg0.py` | 嵌入式 PG 的启动/解析（`EmbeddedPostgres`、`resolve_database_url`） |
| `/app/api/hindsight_api/db_url.py` | DB URL 归一化（asyncpg ↔ libpq） |
| `/app/api/hindsight_api/engine/sql/postgresql.py` | 向量/全文/图查询 SQL 的实际构造 |
| `/app/api/hindsight_api/_text_search.py`、`_pg_search.py` | 全文检索表达式 |
| `/app/extensions/hindsight_ext_static_keys_tenant/extension.py` | **用户/API key 鉴权扩展**（内存校验、schema 派生、懒加载迁移） |
| `/app/api/hindsight_api/extensions/builtin/tenant.py` | 内置单租户/单 key 扩展（`DefaultTenant`、`ApiKeyTenant`，本部署未用） |
| `.deploy-hindsight-mt/run-hindsight.sh` | **实际部署脚本**（`docker run -e` 注入全部配置，含 `TENANT_USERS`） |
| `hindsight/.env` | 历史遗留配置（指向外部 PG，**未采用**） |
| `~/.pg0/instances/hindsight/instance.json` | 运行中 PG 实例的地址/端口/凭据 |

## 附录 B：复现查询命令

```bash
# 进入容器
docker exec -it zhuqingping_hindsight bash

# 登录 PG
/home/hindsight/.pg0/installation/18.1.0/bin/psql -h127.0.0.1 -Uhindsight -p5432
# 密码: hindsight

# 查租户 schema
\dn+
# 查记忆库
SELECT * FROM user_company1.banks;
# 查向量索引
\d user_company1.memory_units
# 查向量维度
SELECT vector_dims(embedding) FROM user_company1.memory_units WHERE embedding IS NOT NULL LIMIT 1;
# 查图边类型分布
SELECT link_type, count(*) FROM user_company1.memory_links GROUP BY link_type;
```
