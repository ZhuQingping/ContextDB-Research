# Hindsight PostgreSQL 表结构与用途

> 验证日期：2026-10-09
> Hindsight 源码基线：`a77c1f3412a7b82f36588dffce1a8d7480e99cc7`
> 实库迁移版本：`c8e2f4a6b1d3`
> 验证对象：方案三原型 Cell1（PostgreSQL 端口 55434）与 Cell2（端口 55435）

## 1. 结论

每个 Hindsight 租户 schema 中有 **25 张表**：

- 24 张 Hindsight 原生业务与运行表；
- 1 张 Alembic 迁移版本表 `alembic_version`。

这些表由 Hindsight 原生 Alembic 迁移自动创建。方案三没有修改 Hindsight 的迁移目录，也没有在租户 schema 中增加表；它只是为每个租户选择独立 schema，再执行同一套原生迁移。

方案三另外使用 SQLite 保存 `tenants`、`cells`、`placements`、`api_backends`、`api_keys` 和 `schemas` 等 Gateway 元数据，并在 Cell1 的 `public` schema 创建原型验收表 `scheme3_prototype_status_audit`。这些都不属于下面的25张Hindsight原生表。

Hindsight 源码把以下8张表明确归为记忆存储层直接拥有的表：

```text
documents, chunks, memory_units, invalidated_memory_units,
entities, unit_entities, memory_links, entity_cooccurrences
```

证据：`hindsight-api-slim/hindsight_api/engine/schema.py` 的 `STORE_TABLES`。迁移入口位于 `hindsight-api-slim/hindsight_api/migrations.py`，迁移脚本位于 `hindsight-api-slim/hindsight_api/alembic/versions/`。

## 2. 表之间的核心关系

```text
banks（记忆库）
 ├─ documents（原始输入）
 │   ├─ chunks（文本切片）
 │   ├─ attachments（附件元数据）── file_storage / S3 / OBS（附件内容）
 │   └─ memory_units（抽取出的事实和观察）
 │       ├─ unit_entities ── entities（规范化实体）
 │       │                    └─ entity_cooccurrences（实体共现）
 │       └─ memory_links（记忆之间的语义、时间和因果关系）
 ├─ mental_models（晋升后的观察和高层知识）
 │   ├─ mental_model_history / observation_history（版本历史）
 │   └─ knowledge_pages（知识页面树）
 ├─ directives（显式规则）
 ├─ async_operations（持久化异步任务）
 └─ webhooks / audit_log / llm_requests（通知、审计和模型调用记录）
```

一个租户 schema 可以包含多个 Bank。同一 schema 中各 Bank 共用这些表，主要通过 `bank_id` 区分数据。

## 3. 25张表的结构与作用

下面的字段来自运行中 PostgreSQL 的 `pg_catalog` 和 `information_schema`，不是根据表名推测。`PK` 表示主键；未列出的普通索引和部分索引由Alembic迁移维护。

### 3.1 迁移管理

#### `alembic_version`

- **作用**：记录当前租户 schema 已执行到的 Alembic 迁移版本，不存放产品业务数据。
- **主键**：`version_num`
- **字段**：`version_num varchar(32)`

### 3.2 记忆库与源数据

#### `banks`

- **作用**：记忆库主表。保存 Bank 的名称、使命、性格、配置、知识合并进度和内部 UUID。
- **主键**：`bank_id`
- **字段**：
  - `bank_id text`：对外使用的记忆库标识；
  - `name text`：显示名称；
  - `disposition jsonb`：Reflect 使用的性格参数；
  - `mission text`：Bank使命；
  - `config jsonb`：Bank级配置；
  - `internal_id uuid`：内部稳定标识，也用于生成每Bank向量索引名称；
  - `created_at timestamptz`、`updated_at timestamptz`；
  - `last_consolidated_at timestamptz`、`mission_changed_at timestamptz`。

#### `bank_aliases`

- **作用**：为Bank提供别名和主别名，使旧标识或友好名称能够解析到真实 `bank_id`。
- **主键**：`alias`
- **外键**：`bank_id → banks.bank_id`
- **字段**：`alias text`、`bank_id text`、`created_at timestamptz`、`is_primary boolean`。

#### `bank_stats_cache`

- **作用**：缓存Bank统计结果，减少统计接口反复扫描大表。
- **主键**：`bank_id`
- **字段**：`bank_id text`、`payload jsonb`、`computed_at timestamptz`。

#### `documents`

- **作用**：保存每次Retain接收的原始文本及其参数、标签和文件引用，是事实的来源记录。
- **主键**：`(id, bank_id)`
- **字段**：
  - `id text`、`bank_id text`；
  - `original_text text`、`content_hash text`；
  - `retain_params jsonb`、`tags varchar[]`；
  - `file_storage_key text`、`file_original_name text`、`file_content_type text`；
  - `created_at timestamptz`、`updated_at timestamptz`。

#### `chunks`

- **作用**：保存长文档切分后的有序文本块，用于事实溯源和分块处理。当前表本身没有Embedding列。
- **主键**：`chunk_id`
- **外键**：`(document_id, bank_id) → documents.(id, bank_id)`
- **字段**：`chunk_id text`、`document_id text`、`bank_id text`、`chunk_index integer`、`chunk_text text`、`content_hash text`、`created_at timestamptz`。

#### `attachments`

- **作用**：保存图片、PDF等附件的元数据和实际对象的 `storage_key`，不直接等同于附件二进制内容。
- **主键**：`(bank_id, document_id, attachment_hash)`
- **外键**：`bank_id → banks.bank_id`
- **字段**：`bank_id text`、`document_id text`、`attachment_hash varchar(64)`、`short_id varchar(12)`、`media_type text`、`byte_size bigint`、`storage_key text`、`kind text`、`filename text`、`created_at timestamptz`。

#### `file_storage`

- **作用**：Hindsight原生 PostgreSQL 文件存储后端，按 `storage_key` 保存二进制内容。使用S3、OBS或其他FileStorage扩展时可以不在该表保存对象正文。
- **主键**：`storage_key`
- **字段**：`storage_key text`、`data bytea`。

### 3.3 事实、向量、全文与图数据

#### `memory_units`

- **作用**：核心记忆事实表。Retain提取出的世界事实、经历和观察存放在这里；Recall的向量、全文、时间和图检索都围绕该表展开。
- **主键**：`id`
- **主要外键**：`(document_id, bank_id) → documents.(id, bank_id)`；`chunk_id → chunks.chunk_id`。
- **字段**：
  - 身份与来源：`id uuid`、`bank_id text`、`document_id text`、`chunk_id text`；
  - 内容：`text text`、`context text`、`fact_type text`、`metadata jsonb`、`tags varchar[]`；
  - 检索：`embedding vector(384)`、`search_vector tsvector`、`text_signals text`；
  - 时间：`event_date timestamptz`、`occurred_start timestamptz`、`occurred_end timestamptz`、`mentioned_at timestamptz`；
  - 生命周期：`proof_count integer`、`source_memory_ids uuid[]`、`consolidated_at timestamptz`、`consolidation_failed_at timestamptz`、`edited_at timestamptz`；
  - 范围与附件：`observation_scopes jsonb`、`attachment_ids text[]`；
  - 审计时间：`created_at timestamptz`、`updated_at timestamptz`。
- **约束**：`fact_type ∈ {world, experience, observation}`。

`embedding vector(384)` 是本次方案三实库的结构，对应原型使用的384维Embedding服务；它不是Hindsight固定维度。更换Embedding模型且维度发生变化时，必须迁移列、重算向量并重建索引，不能只切换模型配置。

#### `invalidated_memory_units`

- **作用**：保存被用户作废但仍可恢复的事实，是事实治理归档，不是普通临时表。
- **主键**：没有主键；保留原事实的 `id` 和完整内容。
- **主要外键**：`(document_id, bank_id) → documents.(id, bank_id)`。
- **字段**：
  - 身份与来源：`id uuid`、`bank_id text`、`document_id text`、`chunk_id text`；
  - 内容：`text text`、`context text`、`fact_type text`、`metadata jsonb`、`tags varchar[]`、`text_signals text`；
  - 时间：`event_date timestamptz`、`occurred_start timestamptz`、`occurred_end timestamptz`、`mentioned_at timestamptz`；
  - 生命周期：`proof_count integer`、`source_memory_ids uuid[]`、`consolidated_at timestamptz`、`consolidation_failed_at timestamptz`、`edited_at timestamptz`；
  - 失效归档：`invalidation_reason text`、`invalidated_at timestamptz`、`entity_ids uuid[]`、`causal_links jsonb`、`attachment_ids text[]`；
  - 范围与审计：`observation_scopes jsonb`、`created_at timestamptz`、`updated_at timestamptz`。
- **与在线表的差异**：不保存在线检索使用的 `embedding` 和 `search_vector`。

#### `entities`

- **作用**：保存规范化实体和标签实体，作为图检索节点。
- **主键**：`id`
- **字段**：`id uuid`、`canonical_name text`、`bank_id text`、`metadata jsonb`、`first_seen timestamptz`、`last_seen timestamptz`、`mention_count integer`、`entity_kind text`。
- **约束**：`entity_kind ∈ {regular, label}`。

#### `unit_entities`

- **作用**：记忆事实和实体的多对多关联表，表示一条事实提到了哪些实体。
- **主键**：`(unit_id, entity_id)`
- **外键**：`unit_id → memory_units.id`；`entity_id → entities.id`。
- **字段**：`unit_id uuid`、`entity_id uuid`。

#### `entity_cooccurrences`

- **作用**：记录两个实体共同出现的次数和最近时间，形成实体共现图。
- **主键**：`(entity_id_1, entity_id_2)`
- **外键**：两个实体ID均引用 `entities.id`。
- **字段**：`entity_id_1 uuid`、`entity_id_2 uuid`、`cooccurrence_count integer`、`last_cooccurred timestamptz`。
- **约束**：`entity_id_1 < entity_id_2`，避免同一无向实体对重复存储。

#### `memory_links`

- **作用**：保存记忆事实之间的有向图边，用于语义、时间、实体和因果关系扩展。
- **主键**：没有传统主键；迁移创建唯一索引约束边的重复写入。
- **外键**：`from_unit_id`、`to_unit_id → memory_units.id`；`entity_id → entities.id`。
- **字段**：`from_unit_id uuid`、`to_unit_id uuid`、`link_type text`、`entity_id uuid`、`weight double precision`、`created_at timestamptz`、`bank_id text`。
- **约束**：`weight` 在0到1之间；`link_type ∈ {temporal, semantic, entity, causes, caused_by, enables, prevents}`。

### 3.4 知识晋升与知识页面

#### `mental_models`

- **作用**：保存知识合并和晋升产生的高层知识，包括Observation、学习结果、固定知识和结构性知识。
- **主键**：`(bank_id, id)`
- **外键**：`bank_id → banks.bank_id`。
- **关联字段**：`entity_id` 保存关联实体标识，但当前实库没有为它建立外键约束。
- **字段**：
  - 身份与描述：`id text`、`bank_id text`、`name varchar(256)`、`description text`、`subtype varchar(32)`；
  - 生成配置：`source_query text`、`last_refreshed_source_query text`、`max_tokens integer`、`trigger jsonb`；
  - 内容：`content text`、`structured_content jsonb`、`reflect_response jsonb`、`observations jsonb`、`links varchar[]`；
  - 检索与关联：`embedding vector(384)`、`search_vector tsvector`、`tags varchar[]`、`entity_id uuid`；
  - 时间和状态：`created_at timestamptz`、`last_refreshed_at timestamptz`、`last_updated timestamptz`、`last_memory_seen_at timestamptz`、`last_refresh_failed_at timestamptz`。
- **约束**：`subtype ∈ {structural, emergent, pinned, learned}`。

#### `mental_model_history`

- **作用**：保存Mental Model每次变更前后的历史版本。
- **主键**：`id`
- **外键**：`(mental_model_id, bank_id) → mental_models.(id, bank_id)`。
- **字段**：`id bigint`、`mental_model_id varchar(64)`、`bank_id text`、`content jsonb`、`changed_at timestamptz`。

#### `observation_history`

- **作用**：保存Observation在自动知识合并过程中的历史版本。
- **主键**：`id`
- **字段**：`id bigint`、`observation_id uuid`、`bank_id text`、`content jsonb`、`changed_at timestamptz`。

#### `knowledge_pages`

- **作用**：构建知识库目录和页面树，并把页面绑定到相应Mental Model。
- **主键**：`id`
- **外键**：`bank_id → banks.bank_id`；`parent_id → knowledge_pages.id`；`(mental_model_id, bank_id) → mental_models.(id, bank_id)`。
- **字段**：`id varchar(64)`、`bank_id text`、`parent_id varchar(64)`、`kind varchar(16)`、`name text`、`mental_model_id varchar(64)`、`sort_order integer`、`managed boolean`、`created_at timestamptz`、`updated_at timestamptz`。
- **约束**：`kind ∈ {folder, page}`。

#### `directives`

- **作用**：保存用户显式设置的长期行为规则或指导，不依赖系统从事实中自动归纳。
- **主键**：`id`
- **外键**：`bank_id → banks.bank_id`
- **字段**：`id uuid`、`bank_id text`、`name varchar(256)`、`content text`、`priority integer`、`is_active boolean`、`tags varchar[]`、`created_at timestamptz`、`updated_at timestamptz`。

### 3.5 异步任务与后台维护

#### `async_operations`

- **作用**：持久化异步操作及其任务载荷，也是API与独立Worker之间的原生协作媒介。Worker从表中领取任务，API通过操作ID查询状态。
- **主键**：`operation_id`
- **外键**：`bank_id → banks.bank_id`
- **字段**：`operation_id uuid`、`bank_id text`、`operation_type text`、`status text`、`task_payload jsonb`、`result_metadata jsonb`、`error_message text`、`worker_id text`、`claimed_at timestamptz`、`retry_count integer`、`next_retry_at timestamptz`、`serialization_key text`、`created_at timestamptz`、`updated_at timestamptz`、`completed_at timestamptz`。
- **约束**：`status ∈ {pending, processing, completed, failed, cancelled}`。

#### `graph_maintenance_queue`

- **作用**：记录需要重新补充图关系的记忆单元，由后台Graph Maintenance任务消费。
- **主键**：`(bank_id, unit_id)`
- **字段**：`bank_id text`、`unit_id uuid`、`enqueued_at timestamptz`。

#### `entity_maintenance_queue`

- **作用**：记录需要检查和清理的实体，例如事实删除后可能已没有引用的实体。
- **主键**：`(bank_id, entity_id)`
- **字段**：`bank_id text`、`entity_id uuid`、`enqueued_at timestamptz`。

### 3.6 可观测性和外部通知

#### `llm_requests`

- **作用**：记录LLM请求的提供商、模型、耗时、Token、输入输出和错误，用于调试、计量及成本分析。
- **主键**：`id`
- **字段**：
  - 标识：`id uuid`、`bank_id text`、`operation text`、`scope text`；
  - Trace：`trace_id text`、`span_id text`、`parent_span_id text`；
  - 模型：`provider text`、`model text`、`llm_info jsonb`；
  - 状态和耗时：`status text`、`started_at timestamptz`、`ended_at timestamptz`、`duration_ms integer`；
  - Token：`input_tokens integer`、`output_tokens integer`、`cached_tokens integer`、`thoughts_tokens integer`、`total_tokens integer`；
  - 内容：`input jsonb`、`output jsonb`、`error text`、`metadata jsonb`。

#### `audit_log`

- **作用**：记录Hindsight操作审计信息。是否写入由审计配置决定，建表并不表示默认记录所有请求。
- **主键**：`id`
- **字段**：`id uuid`、`action text`、`transport text`、`bank_id text`、`started_at timestamptz`、`ended_at timestamptz`、`request jsonb`、`response jsonb`、`metadata jsonb`。

#### `webhooks`

- **作用**：保存Bank级Webhook配置；Webhook投递本身作为任务写入 `async_operations`。
- **主键**：`id`
- **外键**：`bank_id → banks.bank_id`
- **字段**：`id uuid`、`bank_id text`、`url text`、`secret text`、`event_types text[]`、`enabled boolean`、`http_config jsonb`、`created_at timestamptz`、`updated_at timestamptz`。

## 4. 建表与升级机制

Hindsight启动时通过Alembic检查并升级目标schema。多API实例并发启动时，迁移模块使用PostgreSQL advisory lock和进程内锁串行化迁移，防止多个实例同时修改同一schema。

对华为云ContextDB的直接含义：

1. Hindsight版本升级可能同时带来表结构迁移，必须把应用版本和Alembic版本作为一个发布单元管理。
2. 生产环境不应让每个普通API进程长期持有任意DDL权限；应由受控迁移任务执行升级。
3. `memory_units.embedding` 和 `mental_models.embedding` 与Embedding维度绑定，模型升级必须验证维度、重算数据和重建索引。
4. `file_storage` 只在使用PostgreSQL原生文件存储后端时保存二进制数据；接入OBS后仍需保留 `documents` 和 `attachments` 中的元数据与对象引用。
5. `async_operations`、两个维护队列表和历史表都是备份恢复范围，不能只备份记忆正文和向量表。

## 5. 本次实库核验结果

运行中原型的三个租户schema表名完全一致：

```text
Cell1: scheme3_tenant1、scheme3_tenant2
Cell2: scheme3_tenant3
```

每个schema都包含：

```text
alembic_version
async_operations
attachments
audit_log
bank_aliases
bank_stats_cache
banks
chunks
directives
documents
entities
entity_cooccurrences
entity_maintenance_queue
file_storage
graph_maintenance_queue
invalidated_memory_units
knowledge_pages
llm_requests
memory_links
memory_units
mental_model_history
mental_models
observation_history
unit_entities
webhooks
```

因此数量口径为：

```text
24张Hindsight原生业务与运行表
+ 1张Alembic迁移版本表
= 每个租户schema共25张表
```

## 6. 复核SQL

```sql
-- 列出一个租户schema的全部表
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'scheme3_tenant1'
ORDER BY tablename;

-- 查看字段、类型、可空性和默认值
SELECT
    a.attname AS column_name,
    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
    NOT a.attnotnull AS nullable,
    pg_get_expr(d.adbin, d.adrelid) AS default_value
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
WHERE n.nspname = 'scheme3_tenant1'
  AND c.relname = 'memory_units'
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY a.attnum;

-- 查看当前迁移版本
SELECT version_num FROM scheme3_tenant1.alembic_version;
```
