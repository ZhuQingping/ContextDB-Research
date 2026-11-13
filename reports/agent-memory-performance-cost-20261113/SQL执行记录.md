# SQL 执行记录与用途说明

本附件保存本次 API 实测中出现的 SQL 全文。主要目录来自临时 API 的 asyncpg 发送记录，并与 PG 完成日志关联；另列原服务 reflect 中确实执行的 Mental Model SQL。**没有把源码模板写成实测 SQL。**

相同 SQL 按空白归一后去重，原始文本保留第一条。`$1` 等是实际绑定参数；完整参数在 evidence/sender-*.jsonl 和对应 PG filtered.log，报告不内联 1024 维向量。COPY 目录项保存驱动调用形态，并附 PG 实际 COPY 文本。

|编号|作用|
|---|---|
|[SQL-001](#sql-001)|读取 Bank 的身份、立场和目标，为 retain/recall/reflect 构建运行上下文。|
|[SQL-002](#sql-002)|读取 Bank 配置，覆盖服务默认配置；这是控制信息，不是记忆内容检索。|
|[SQL-003](#sql-003)|确认 Bank 存在；带 FOR NO KEY UPDATE 时还序列化该 Bank 的任务提交。|
|[SQL-004](#sql-004)|检查或读取附件引用；本次文本请求也会执行通用附件补全路径。|
|[SQL-005](#sql-005)|读取文档更新时间，检测处理期间是否发生并发修改。|
|[SQL-006](#sql-006)|读取文档内容 hash，比较内容是否已保存，支持幂等/增量处理。|
|[SQL-007](#sql-007)|读取文档已有片段与 hash，判断哪些片段变化、能否跳过重复抽取。|
|[SQL-008](#sql-008)|用 pg_trgm 按相似实体名批量查找候选，为实体归一提供近似匹配。|
|[SQL-009](#sql-009)|读取候选实体之间的共现关系，为实体消歧或统计维护提供证据。|
|[SQL-010](#sql-010)|将新实体名按小写顺序插入并去重，返回规范实体 ID；统一锁/冲突顺序减少并发死锁。|
|[SQL-011](#sql-011)|创建文档占位行或锁定已存在文档；读取旧 hash，串行化同文档并发写入。|
|[SQL-012](#sql-012)|扫描或读取指定文档/作用域中的事实，支持替换检查、引用或辅助处理。|
|[SQL-013](#sql-013)|文档替换路径清理旧事实；本轮新文档也进入公共替换流程，语句出现不表示一定删除了已有事实。|
|[SQL-014](#sql-014)|替换文档记录并保留旧创建时间；本轮对象只属于合成数据 Bank。|
|[SQL-015](#sql-015)|保存文档原文、hash、retain 参数和标签；替换时更新内容并维护时间戳。|
|[SQL-016](#sql-016)|清理被替换文档的附件引用，为重新保存附件准备一致状态。|
|[SQL-017](#sql-017)|批量写入或更新原文片段；冲突时只允许同 Bank 更新，返回实际写入的 chunk_id。|
|[SQL-018](#sql-018)|用数组 UNNEST 一次批量写入抽取事实、向量、时间、标签及来源；同时构造全文 search_vector。|
|[SQL-019](#sql-019)|重新确认实体父行仍存在并持有键共享锁；必要时重建实体，保证随后写关联的外键有效。|
|[SQL-020](#sql-020)|批量写入事实—实体关联；同一关联已存在时跳过。|
|[SQL-021](#sql-021)|按事实 ID 批量读取事件日期和类型，准备创建时间关系。|
|[SQL-022](#sql-022)|对每个事实分别查找时间之前和之后的近邻，再按时间差选出有限邻居，用于创建时间边。|
|[SQL-023](#sql-023)|先按 ID 锁住仍存在的两端事实，再批量写入关系边；冲突去重，避免并发删除造成悬挂外键。|
|[SQL-024](#sql-024)|统计该文档或作用域下的事实数量，用于结果、状态或新鲜度计算。|
|[SQL-025](#sql-025)|累加实体被提及次数并更新最近出现时间；本次是批处理中的逐条参数执行。|
|[SQL-026](#sql-026)|累加实体对的共现次数与最近共现时间；本次由 executemany 多次执行。|
|[SQL-027](#sql-027)|读取刚写入事实的已存向量与类型，随后批量查找语义邻居；不是重新生成 embedding。|
|[SQL-028](#sql-028)|设置本次连接/事务的检索参数；例如 retain 建边使用较低 ef_search。|
|[SQL-029](#sql-029)|创建事务结束自动删除的向量种子临时表，供批量 ANN 建边使用。|
|[SQL-030](#sql-030)|COPY 批量装入待建语义边的种子向量；这是驱动协议调用，PG 侧有对应 COPY 语句。|
|[SQL-031](#sql-031)|按类型读取种子，每个种子执行 ANN Top-K；将文本向量只转换一次，寻找可建立语义边的既有事实。|
|[SQL-032](#sql-032)|确认 Bank 存在；带 FOR NO KEY UPDATE 时还序列化该 Bank 的任务提交。|
|[SQL-033](#sql-033)|读取该 Bank 的异步任务状态，去重待处理任务或提供后台任务诊断。|
|[SQL-034](#sql-034)|持久化后台 consolidation 等任务的身份、状态、payload 和串行化键；API 返回不代表所有后台维护结束。|
|[SQL-035](#sql-035)|检查图/实体维护队列是否有待处理项，以决定是否提交后台维护任务。|
|[SQL-036](#sql-036)|读取 Bank 的身份、立场和目标，为 retain/recall/reflect 构建运行上下文。|
|[SQL-037](#sql-037)|读取 Bank 配置，覆盖服务默认配置；这是控制信息，不是记忆内容检索。|
|[SQL-038](#sql-038)|一条 SQL 合并向量与关键词召回；每种事实类型、每条检索分支独立 ORDER BY/LIMIT，返回正文与分数。关键词实际为 ts_rank_cd。|
|[SQL-039](#sql-039)|按事件/提及时间与窗口重叠条件寻找时序入口；每种类型先取相似度最高的 60 条。|
|[SQL-040](#sql-040)|批量沿时间/因果边扩展邻居；每源节点先取高权重边，再过滤目标事实并计算向量相似度。|
|[SQL-041](#sql-041)|Observation 图扩展：共享实体分支通过来源事实查关联并映射回 Observation；语义、因果分支直接从起点 Observation 查边，最后汇总。|
|[SQL-042](#sql-042)|普通事实图扩展：共享实体、双向语义边、出向因果边三路 SQL 联合；共享实体计数与各路限流在库内，最终图评分在 Python。|
|[SQL-043](#sql-043)|补全返回事实的实体名；Observation 没有直接实体时通过其来源事实推导实体。|
|[SQL-044](#sql-044)|按最终结果 ID 批量读取 id、document_id 和 attachment_ids，供文档/附件引用补全；此处不读取正文。|
|[SQL-045](#sql-045)|检查或读取附件引用；本次文本请求也会执行通用附件补全路径。|
|[SQL-046](#sql-046)|确认 Bank 存在；带 FOR NO KEY UPDATE 时还序列化该 Bank 的任务提交。|
|[SQL-047](#sql-047)|读取事实整合/写入水位及待整合、失败数量，为 reflect 判断知识新鲜度提供状态。|
|[SQL-048](#sql-048)|统计本次 reflect 可应用的行为规则；这是同接口分页实现带来的附加查询。|
|[SQL-049](#sql-049)|读取启用且在请求作用域内的行为规则，按优先级提供给 reflect 的提示词。|
|[SQL-050](#sql-050)|一条 SQL 合并向量与关键词召回；每种事实类型、每条检索分支独立 ORDER BY/LIMIT，返回正文与分数。关键词实际为 ts_rank_cd。|
|[SQL-051](#sql-051)|批量补读原文片段，供 recall/reflect 的来源展示或证据展开使用。|
|[SQL-052](#sql-052)|按事件/提及时间与窗口重叠条件寻找时序入口；每种类型先取相似度最高的 60 条。|
|[SQL-053](#sql-053)|按事实 ID 批量读取正文/来源/元数据，供事实引用、证据展开或来源校验。|
|[SQL-054](#sql-054)|一条 SQL 合并向量与关键词召回；每种事实类型、每条检索分支独立 ORDER BY/LIMIT，返回正文与分数。关键词实际为 ts_rank_cd。|
|[SQL-055](#sql-055)|按事件/提及时间与窗口重叠条件寻找时序入口；每种类型先取相似度最高的 60 条。|
|[SQL-056](#sql-056)|开始、提交或回滚事务；确定锁、临时表和事务局部参数的生命周期。|
|[SQL-057](#sql-057)|开始、提交或回滚事务；确定锁、临时表和事务局部参数的生命周期。|
|[SQL-058](#sql-058)|读取或检查知识正文、刷新水位和作用域；与原始事实召回分开。|
|[SQL-059](#sql-059)|按向量检索高层知识正文 Mental Models，供 reflect 优先使用已有整理结果。|
|[SQL-060](#sql-060)|读取或检查知识正文、刷新水位和作用域；与原始事实召回分开。|
|[SQL-061](#sql-061)|读取或检查知识正文、刷新水位和作用域；与原始事实召回分开。|
|[SQL-062](#sql-062)|读取或检查知识正文、刷新水位和作用域；与原始事实召回分开。|
|[SQL-063](#sql-063)|读取或检查知识正文、刷新水位和作用域；与原始事实召回分开。|

## SQL-001

读取 Bank 的身份、立场和目标，为 retain/recall/reflect 构建运行上下文。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`104`、PID=`49673`。

```sql
SELECT name, disposition, mission
        FROM ctxdb_ws_pg_trace_20261112.banks WHERE bank_id = $1
```

## SQL-002

读取 Bank 配置，覆盖服务默认配置；这是控制信息，不是记忆内容检索。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`106`、PID=`49673`。

```sql
SELECT config FROM ctxdb_ws_pg_trace_20261112.banks WHERE bank_id = $1
```

## SQL-003

确认 Bank 存在；带 FOR NO KEY UPDATE 时还序列化该 Bank 的任务提交。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`108`、PID=`49673`。

```sql
SELECT 1 FROM ctxdb_ws_pg_trace_20261112.banks WHERE bank_id = $1
```

## SQL-004

检查或读取附件引用；本次文本请求也会执行通用附件补全路径。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`110`、PID=`49673`。

```sql
SELECT DISTINCT storage_key FROM ctxdb_ws_pg_trace_20261112.attachments WHERE bank_id = $1 AND document_id = ANY($2::text[])
```

## SQL-005

读取文档更新时间，检测处理期间是否发生并发修改。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`112`、PID=`49673`。

```sql
SELECT updated_at FROM ctxdb_ws_pg_trace_20261112.documents WHERE id = $1 AND bank_id = $2
```

## SQL-006

读取文档内容 hash，比较内容是否已保存，支持幂等/增量处理。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 4 次；关联 PG 执行 4 次。首条发送记录：provider=`rrf`、qid=`114`、PID=`49673`。

```sql
SELECT content_hash FROM ctxdb_ws_pg_trace_20261112.documents WHERE id = $1 AND bank_id = $2
```

## SQL-007

读取文档已有片段与 hash，判断哪些片段变化、能否跳过重复抽取。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`115`、PID=`49673`。

```sql
SELECT chunk_id, chunk_index, content_hash
        FROM ctxdb_ws_pg_trace_20261112.chunks
        WHERE document_id = $1 AND bank_id = $2
        ORDER BY chunk_index
```

## SQL-008

用 pg_trgm 按相似实体名批量查找候选，为实体归一提供近似匹配。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`135`、PID=`49673`。

```sql
SELECT c.id, c.canonical_name, c.metadata, c.last_seen, c.mention_count,
                           q.query_text
                    FROM unnest($2::text[]) AS q(query_text)
                    CROSS JOIN LATERAL (
                        SELECT e.id, e.canonical_name, e.metadata, e.last_seen, e.mention_count
                        FROM ctxdb_ws_pg_trace_20261112.entities e
                        WHERE e.bank_id = $1
                          AND e.entity_kind != 'label'
                          AND LOWER(e.canonical_name) % LOWER(q.query_text)
                        ORDER BY similarity(LOWER(e.canonical_name), LOWER(q.query_text)) DESC, e.id
                        LIMIT $3
                    ) c
```

## SQL-009

读取候选实体之间的共现关系，为实体消歧或统计维护提供证据。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`136`、PID=`49673`。

```sql
SELECT ec.entity_id_1, ec.entity_id_2
                FROM ctxdb_ws_pg_trace_20261112.entity_cooccurrences ec
                WHERE ec.entity_id_1 = ANY($1::uuid[])
                   OR ec.entity_id_2 = ANY($1::uuid[])
```

## SQL-010

将新实体名按小写顺序插入并去重，返回规范实体 ID；统一锁/冲突顺序减少并发死锁。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`137`、PID=`49673`。

```sql
INSERT INTO ctxdb_ws_pg_trace_20261112.entities (bank_id, canonical_name, first_seen, last_seen, mention_count, entity_kind)
            SELECT $1, name, COALESCE(event_date, now()), COALESCE(event_date, now()), 0, kind
            FROM unnest($2::text[], $3::timestamptz[], $4::text[]) AS t(name, event_date, kind)
            ORDER BY LOWER(name)
            ON CONFLICT (bank_id, LOWER(canonical_name))
            DO NOTHING
            RETURNING id, LOWER(canonical_name) AS name_lower
```

## SQL-011

创建文档占位行或锁定已存在文档；读取旧 hash，串行化同文档并发写入。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`140`、PID=`49673`。

```sql
INSERT INTO ctxdb_ws_pg_trace_20261112.documents (id, bank_id, original_text, content_hash) VALUES ($1, $2, '', '__pending__') ON CONFLICT (id, bank_id) DO UPDATE SET content_hash = ctxdb_ws_pg_trace_20261112.documents.content_hash RETURNING content_hash
```

## SQL-012

扫描或读取指定文档/作用域中的事实，支持替换检查、引用或辅助处理。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`141`、PID=`49673`。

```sql
SELECT
    id, text, fact_type, context, document_id, chunk_id, tags, metadata,
    proof_count, event_date, occurred_start, occurred_end, mentioned_at,
    created_at, updated_at, source_memory_ids, consolidated_at, observation_scopes

        FROM ctxdb_ws_pg_trace_20261112.memory_units
        WHERE bank_id = $1 AND fact_type = ANY($2) AND document_id = $3
        ORDER BY created_at, id
        LIMIT $4 OFFSET $5
```

## SQL-013

文档替换路径清理旧事实；本轮新文档也进入公共替换流程，语句出现不表示一定删除了已有事实。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`142`、PID=`49673`。

```sql
DELETE FROM ctxdb_ws_pg_trace_20261112.memory_units WHERE document_id = $1 AND bank_id = $2
```

## SQL-014

替换文档记录并保留旧创建时间；本轮对象只属于合成数据 Bank。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`143`、PID=`49673`。

```sql
DELETE FROM ctxdb_ws_pg_trace_20261112.documents WHERE id = $1 AND bank_id = $2 RETURNING created_at
```

## SQL-015

保存文档原文、hash、retain 参数和标签；替换时更新内容并维护时间戳。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`144`、PID=`49673`。

```sql
INSERT INTO ctxdb_ws_pg_trace_20261112.documents (id, bank_id, original_text, content_hash, retain_params, tags, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, COALESCE($7, NOW()), NOW())
        ON CONFLICT (id, bank_id) DO UPDATE
        SET original_text = EXCLUDED.original_text,
            content_hash = EXCLUDED.content_hash,
            retain_params = EXCLUDED.retain_params,
            tags = EXCLUDED.tags,
            updated_at = NOW()
```

## SQL-016

清理被替换文档的附件引用，为重新保存附件准备一致状态。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`145`、PID=`49673`。

```sql
DELETE FROM ctxdb_ws_pg_trace_20261112.attachments WHERE bank_id = $1 AND document_id = $2
```

## SQL-017

批量写入或更新原文片段；冲突时只允许同 Bank 更新，返回实际写入的 chunk_id。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`146`、PID=`49673`。

```sql
INSERT INTO ctxdb_ws_pg_trace_20261112.chunks (chunk_id, document_id, bank_id, chunk_text, chunk_index, content_hash)
            SELECT * FROM unnest($1::text[], $2::text[], $3::text[], $4::text[], $5::integer[], $6::text[])
            ON CONFLICT (chunk_id) DO UPDATE SET
                chunk_text = EXCLUDED.chunk_text,
                chunk_index = EXCLUDED.chunk_index,
                content_hash = EXCLUDED.content_hash
            WHERE ctxdb_ws_pg_trace_20261112.chunks.bank_id = EXCLUDED.bank_id
            RETURNING chunk_id
```

## SQL-018

用数组 UNNEST 一次批量写入抽取事实、向量、时间、标签及来源；同时构造全文 search_vector。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`147`、PID=`49673`。

```sql
WITH input_data AS (
                SELECT * FROM unnest(
                    $2::text[], $3::vector[], $4::timestamptz[], $5::timestamptz[], $6::timestamptz[], $7::timestamptz[],
                    $8::text[], $9::text[], $10::jsonb[], $11::text[], $12::text[], $13::jsonb[], $14::jsonb[], $15::text[],
                    $16::jsonb[]
                ) AS t(text, embedding, event_date, occurred_start, occurred_end, mentioned_at,
                       context, fact_type, metadata, chunk_id, document_id, tags_json,
                       observation_scopes_json, text_signals, attachment_ids_json)
            )
            INSERT INTO ctxdb_ws_pg_trace_20261112.memory_units (bank_id, text, embedding, event_date, occurred_start, occurred_end, mentioned_at,
                                 context, fact_type, metadata, chunk_id, document_id, tags,
                                 observation_scopes, text_signals, attachment_ids, search_vector)
            SELECT
                $1,
                text, embedding, event_date, occurred_start, occurred_end, mentioned_at,
                context, fact_type, metadata, chunk_id, document_id,
                COALESCE(
                    (SELECT array_agg(elem) FROM jsonb_array_elements_text(tags_json) AS elem),
                    '{}'::varchar[]
                ),
                observation_scopes_json,
                text_signals,
                -- Same jsonb-array-to-text[] shape as `tags` just above: asyncpg
                -- does not bind a list-of-lists to text[][], so each row's ids
                -- travel as a JSON array and are unpacked here.
                COALESCE(
                    (SELECT array_agg(elem) FROM jsonb_array_elements_text(attachment_ids_json) AS elem),
                    '{}'::text[]
                ),
                    to_tsvector('english'::regconfig, COALESCE(text, '') || ' ' || COALESCE(context, '') || ' ' || COALESCE(text_signals, ''))
            FROM input_data
            RETURNING id
```

## SQL-019

重新确认实体父行仍存在并持有键共享锁；必要时重建实体，保证随后写关联的外键有效。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`148`、PID=`49673`。

```sql
WITH locked AS (
                SELECT id FROM ctxdb_ws_pg_trace_20261112.entities
                WHERE id = ANY($2::uuid[])
                ORDER BY id
                FOR KEY SHARE
            )
            INSERT INTO ctxdb_ws_pg_trace_20261112.entities (id, bank_id, canonical_name, entity_kind)
            SELECT t.entity_id, $1, t.canonical_name, t.entity_kind
            FROM unnest($2::uuid[], $3::text[], $4::text[]) AS t(entity_id, canonical_name, entity_kind)
            WHERE t.entity_id NOT IN (SELECT id FROM locked)
            ON CONFLICT DO NOTHING
```

## SQL-020

批量写入事实—实体关联；同一关联已存在时跳过。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`149`、PID=`49673`。

```sql
INSERT INTO ctxdb_ws_pg_trace_20261112.unit_entities (unit_id, entity_id)
            SELECT u, e FROM unnest($1::uuid[], $2::uuid[]) AS t(u, e)
            ON CONFLICT DO NOTHING
```

## SQL-021

按事实 ID 批量读取事件日期和类型，准备创建时间关系。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`150`、PID=`49673`。

```sql
SELECT id, event_date, fact_type
            FROM ctxdb_ws_pg_trace_20261112.memory_units
            WHERE id = ANY(
                ARRAY(
                    SELECT input.unit_id::uuid
                    FROM unnest($1::text[]) AS input(unit_id)
                    WHERE input.unit_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                )
            )
```

## SQL-022

对每个事实分别查找时间之前和之后的近邻，再按时间差选出有限邻居，用于创建时间边。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`151`、PID=`49673`。

```sql
SELECT from_id, id, event_date, time_diff_hours FROM (
                    SELECT src.unit_id::text AS from_id, combined.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY src.unit_id
                               ORDER BY combined.time_diff_hours
                           ) AS rn
                    FROM unnest($1::uuid[], $2::timestamptz[], $3::text[])
                         AS src(unit_id, event_date, fact_type)
                    CROSS JOIN LATERAL (
                        (SELECT mu.id, mu.event_date,
                                ABS(EXTRACT(EPOCH FROM mu.event_date - src.event_date)) / 3600.0 AS time_diff_hours
                         FROM ctxdb_ws_pg_trace_20261112.memory_units mu
                         WHERE mu.bank_id = $4
                           AND mu.fact_type = src.fact_type
                           AND mu.event_date <= src.event_date
                           AND mu.id != src.unit_id
                         ORDER BY mu.event_date DESC
                         LIMIT $5)
                        UNION ALL
                        (SELECT mu.id, mu.event_date,
                                ABS(EXTRACT(EPOCH FROM mu.event_date - src.event_date)) / 3600.0 AS time_diff_hours
                         FROM ctxdb_ws_pg_trace_20261112.memory_units mu
                         WHERE mu.bank_id = $4
                           AND mu.fact_type = src.fact_type
                           AND mu.event_date > src.event_date
                           AND mu.id != src.unit_id
                         ORDER BY mu.event_date ASC
                         LIMIT $5)
                    ) combined
                ) ranked
                WHERE rn <= $5
```

## SQL-023

先按 ID 锁住仍存在的两端事实，再批量写入关系边；冲突去重，避免并发删除造成悬挂外键。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 4 次；关联 PG 执行 4 次。首条发送记录：provider=`rrf`、qid=`152`、PID=`49673`。

```sql
WITH locked AS (
                    SELECT id FROM ctxdb_ws_pg_trace_20261112.memory_units
                    WHERE id = ANY($7::uuid[])
                    ORDER BY id
                    FOR KEY SHARE
                )
                INSERT INTO ctxdb_ws_pg_trace_20261112.memory_links
                    (from_unit_id, to_unit_id, link_type, weight, entity_id, bank_id)
                SELECT f, t, tp, w, e, $6
                FROM unnest($1::uuid[], $2::uuid[], $3::text[], $4::float8[], $5::uuid[])
                    AS u(f, t, tp, w, e)
                WHERE f IN (SELECT id FROM locked) AND t IN (SELECT id FROM locked)
                ON CONFLICT (from_unit_id, to_unit_id, link_type,
                             COALESCE(entity_id, '00000000-0000-0000-0000-000000000000'::uuid))
                DO NOTHING
```

## SQL-024

统计该文档或作用域下的事实数量，用于结果、状态或新鲜度计算。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`153`、PID=`49673`。

```sql
SELECT COUNT(*) FROM ctxdb_ws_pg_trace_20261112.memory_units WHERE bank_id = $1 AND document_id = $2
```

## SQL-025

累加实体被提及次数并更新最近出现时间；本次是批处理中的逐条参数执行。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 15 次。首条发送记录：provider=`rrf`、qid=`157`、PID=`49673`。

```sql
UPDATE ctxdb_ws_pg_trace_20261112.entities SET
                        mention_count = mention_count + $2,
                        last_seen     = GREATEST(last_seen, $3)
                    WHERE id = $1::uuid
```

## SQL-026

累加实体对的共现次数与最近共现时间；本次由 executemany 多次执行。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 36 次。首条发送记录：provider=`rrf`、qid=`158`、PID=`49673`。

```sql
INSERT INTO ctxdb_ws_pg_trace_20261112.entity_cooccurrences
                        (entity_id_1, entity_id_2, cooccurrence_count, last_cooccurred)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (entity_id_1, entity_id_2)
                    DO UPDATE SET
                        cooccurrence_count = ctxdb_ws_pg_trace_20261112.entity_cooccurrences.cooccurrence_count + EXCLUDED.cooccurrence_count,
                        last_cooccurred    = GREATEST(ctxdb_ws_pg_trace_20261112.entity_cooccurrences.last_cooccurred, EXCLUDED.last_cooccurred)
```

## SQL-027

读取刚写入事实的已存向量与类型，随后批量查找语义邻居；不是重新生成 embedding。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`160`、PID=`49673`。

```sql
SELECT id::text, embedding::text, fact_type
        FROM ctxdb_ws_pg_trace_20261112.memory_units
        WHERE bank_id = $1 AND id = ANY($2::uuid[])
        ORDER BY id
```

## SQL-028

设置本次连接/事务的检索参数；例如 retain 建边使用较低 ef_search。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`163`、PID=`49673`。

```sql
SET LOCAL hnsw.ef_search = 60
```

## SQL-029

创建事务结束自动删除的向量种子临时表，供批量 ANN 建边使用。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`164`、PID=`49673`。

```sql
CREATE TEMP TABLE _ann_seeds (unit_id text, emb_text text, fact_type text) ON COMMIT DROP
```

## SQL-030

COPY 批量装入待建语义边的种子向量；这是驱动协议调用，PG 侧有对应 COPY 语句。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`165`、PID=`49673`。

```sql
_ann_seeds
```

PG 实际执行：

```sql
COPY "_ann_seeds"("unit_id", "emb_text", "fact_type") FROM STDIN (FORMAT binary)
```

## SQL-031

按类型读取种子，每个种子执行 ANN Top-K；将文本向量只转换一次，寻找可建立语义边的既有事实。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`166`、PID=`49673`。

```sql
WITH seeds AS MATERIALIZED (
                    SELECT unit_id, emb_text::vector AS emb
                    FROM _ann_seeds
                    WHERE fact_type = $2
                )
                SELECT s.unit_id       AS from_id,
                       n.id::text      AS to_id,
                       n.similarity
                FROM seeds s
                CROSS JOIN LATERAL (
                    SELECT mu.id,
                           1 - (mu.embedding <=> s.emb) AS similarity
                    FROM ctxdb_ws_pg_trace_20261112.memory_units mu
                    WHERE mu.bank_id = $1
                      AND mu.fact_type = $2
                      AND mu.embedding IS NOT NULL
                    ORDER BY mu.embedding <=> s.emb
                    LIMIT $3
                ) n
```

## SQL-032

确认 Bank 存在；带 FOR NO KEY UPDATE 时还序列化该 Bank 的任务提交。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`171`、PID=`49673`。

```sql
SELECT 1 FROM ctxdb_ws_pg_trace_20261112.banks WHERE bank_id = $1 FOR NO KEY UPDATE
```

## SQL-033

读取该 Bank 的异步任务状态，去重待处理任务或提供后台任务诊断。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`172`、PID=`49673`。

```sql
SELECT operation_id, task_payload, status FROM ctxdb_ws_pg_trace_20261112.async_operations
                        WHERE bank_id = $1 AND operation_type = $2 AND status = 'pending'
```

## SQL-034

持久化后台 consolidation 等任务的身份、状态、payload 和串行化键；API 返回不代表所有后台维护结束。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`173`、PID=`49673`。

```sql
INSERT INTO ctxdb_ws_pg_trace_20261112.async_operations
                        (operation_id, bank_id, operation_type, result_metadata, status,
                         task_payload, serialization_key)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
```

## SQL-035

检查图/实体维护队列是否有待处理项，以决定是否提交后台维护任务。

观测阶段：`20-dual-retain`、`26-dual-retain-with-transactions`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`178`、PID=`49673`。

```sql
SELECT 1 WHERE
                        EXISTS (SELECT 1 FROM ctxdb_ws_pg_trace_20261112.graph_maintenance_queue WHERE bank_id = $1)
                        OR EXISTS (SELECT 1 FROM ctxdb_ws_pg_trace_20261112.entity_maintenance_queue WHERE bank_id = $1)
```

## SQL-036

读取 Bank 的身份、立场和目标，为 retain/recall/reflect 构建运行上下文。

观测阶段：`21-dual-rrf-recall`、`22-dual-rrf-reflect`、`23-dual-maas-recall`、`25-dual-maas100-reflect`。应用调用 4 次；关联 PG 执行 4 次。首条发送记录：provider=`rrf`、qid=`184`、PID=`49673`。

```sql
SELECT name, disposition, mission
        FROM ctxdb_ws_agent_memory.banks WHERE bank_id = $1
```

## SQL-037

读取 Bank 配置，覆盖服务默认配置；这是控制信息，不是记忆内容检索。

观测阶段：`21-dual-rrf-recall`、`22-dual-rrf-reflect`、`23-dual-maas-recall`、`25-dual-maas100-reflect`。应用调用 4 次；关联 PG 执行 4 次。首条发送记录：provider=`rrf`、qid=`186`、PID=`49673`。

```sql
SELECT config FROM ctxdb_ws_agent_memory.banks WHERE bank_id = $1
```

## SQL-038

一条 SQL 合并向量与关键词召回；每种事实类型、每条检索分支独立 ORDER BY/LIMIT，返回正文与分数。关键词实际为 ts_rank_cd。

观测阶段：`21-dual-rrf-recall`。应用调用 1 次；关联 PG 执行 1 次。首条发送记录：provider=`rrf`、qid=`188`、PID=`49673`。

```sql
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,        NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'observation'   AND embedding IS NOT NULL   AND (1 - (embedding <=> $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,        NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'experience'   AND embedding IS NOT NULL   AND (1 - (embedding <=> $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,        NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'world'   AND embedding IS NOT NULL   AND (1 - (embedding <=> $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,        ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'observation'   AND search_vector @@ to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC LIMIT $3)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,        ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'experience'   AND search_vector @@ to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC LIMIT $3)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,        ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'world'   AND search_vector @@ to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC LIMIT $3)
```

## SQL-039

按事件/提及时间与窗口重叠条件寻找时序入口；每种类型先取相似度最高的 60 条。

观测阶段：`21-dual-rrf-recall`。应用调用 1 次；关联 PG 执行 1 次。首条发送记录：provider=`rrf`、qid=`189`、PID=`49673`。

```sql
(
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $2
          AND fact_type = 'observation'
          AND embedding IS NOT NULL
          AND (
              (occurred_start IS NOT NULL AND occurred_end IS NOT NULL
               AND occurred_start <= $4 AND occurred_end >= $3)
              OR
              (mentioned_at IS NOT NULL AND mentioned_at BETWEEN $3 AND $4)
              OR
              (occurred_start IS NOT NULL AND occurred_start BETWEEN $3 AND $4)
              OR
              (occurred_end IS NOT NULL AND occurred_end BETWEEN $3 AND $4)
          )
          AND (1 - (embedding <=> $1::vector)) >= $5



        ORDER BY embedding <=> $1::vector
        LIMIT 60
        )
UNION ALL
(
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $2
          AND fact_type = 'experience'
          AND embedding IS NOT NULL
          AND (
              (occurred_start IS NOT NULL AND occurred_end IS NOT NULL
               AND occurred_start <= $4 AND occurred_end >= $3)
              OR
              (mentioned_at IS NOT NULL AND mentioned_at BETWEEN $3 AND $4)
              OR
              (occurred_start IS NOT NULL AND occurred_start BETWEEN $3 AND $4)
              OR
              (occurred_end IS NOT NULL AND occurred_end BETWEEN $3 AND $4)
          )
          AND (1 - (embedding <=> $1::vector)) >= $5



        ORDER BY embedding <=> $1::vector
        LIMIT 60
        )
UNION ALL
(
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $2
          AND fact_type = 'world'
          AND embedding IS NOT NULL
          AND (
              (occurred_start IS NOT NULL AND occurred_end IS NOT NULL
               AND occurred_start <= $4 AND occurred_end >= $3)
              OR
              (mentioned_at IS NOT NULL AND mentioned_at BETWEEN $3 AND $4)
              OR
              (occurred_start IS NOT NULL AND occurred_start BETWEEN $3 AND $4)
              OR
              (occurred_end IS NOT NULL AND occurred_end BETWEEN $3 AND $4)
          )
          AND (1 - (embedding <=> $1::vector)) >= $5



        ORDER BY embedding <=> $1::vector
        LIMIT 60
        )
```

## SQL-040

批量沿时间/因果边扩展邻居；每源节点先取高权重边，再过滤目标事实并计算向量相似度。

观测阶段：`21-dual-rrf-recall`、`22-dual-rrf-reflect`、`23-dual-maas-recall`、`25-dual-maas100-reflect`。应用调用 24 次；关联 PG 执行 24 次。首条发送记录：provider=`rrf`、qid=`190`、PID=`49673`。

```sql
SELECT src.from_unit_id, mu.id, mu.text, mu.context, mu.event_date, mu.occurred_start, mu.occurred_end, mu.mentioned_at, mu.fact_type, mu.document_id, mu.chunk_id, mu.tags, mu.metadata, mu.proof_count,
                       l.weight, l.link_type,
                       1 - (mu.embedding <=> $1::vector) AS similarity
                FROM unnest($2::uuid[]) AS src(from_unit_id)
                CROSS JOIN LATERAL (
                    SELECT ml.to_unit_id, ml.weight, ml.link_type
                    FROM ctxdb_ws_agent_memory.memory_links ml
                    WHERE ml.from_unit_id = src.from_unit_id
                      AND ml.link_type IN ('temporal', 'causes', 'caused_by', 'enables', 'prevents')
                      AND ml.weight >= 0.1
                    ORDER BY ml.weight DESC
                    LIMIT $5
                ) l
                JOIN ctxdb_ws_agent_memory.memory_units mu ON mu.id = l.to_unit_id
                WHERE mu.bank_id = $6
                  AND mu.fact_type = $3
                  AND mu.embedding IS NOT NULL
                  AND (1 - (mu.embedding <=> $1::vector)) >= $4
```

## SQL-041

Observation 图扩展：共享实体分支通过来源事实查关联并映射回 Observation；语义、因果分支直接从起点 Observation 查边，最后汇总。

观测阶段：`21-dual-rrf-recall`、`23-dual-maas-recall`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`200`、PID=`49673`。

```sql
WITH seed_sources AS (
                SELECT DISTINCT unnest(source_memory_ids) AS source_id
                FROM ctxdb_ws_agent_memory.memory_units
                WHERE id = ANY($1::uuid[])
                  AND source_memory_ids IS NOT NULL
            ),
            source_entities AS (
                SELECT DISTINCT ue_seed.entity_id
                FROM seed_sources ss
                JOIN ctxdb_ws_agent_memory.unit_entities ue_seed ON ue_seed.unit_id = ss.source_id
            ),
            connected_sources AS (
                SELECT DISTINCT t.unit_id AS source_id
                FROM (
                    SELECT
                        ue_target.unit_id,
                        row_number() OVER (
                            PARTITION BY ue_target.entity_id
                            ORDER BY ue_target.unit_id DESC
                        ) AS rn
                    FROM ctxdb_ws_agent_memory.unit_entities ue_target
                    JOIN source_entities se ON se.entity_id = ue_target.entity_id
                ) t
                WHERE t.rn <= 200
                  AND NOT EXISTS (
                      SELECT 1 FROM seed_sources ss WHERE ss.source_id = t.unit_id
                  )
            ),
            candidate_ids AS (
                SELECT DISTINCT o.id
                FROM connected_sources cs
                CROSS JOIN LATERAL (
                    SELECT m.id
                    FROM ctxdb_ws_agent_memory.memory_units m
                    WHERE m.source_memory_ids @> ARRAY[cs.source_id]
                    OFFSET 0
                ) o
            ),
            candidates AS (
                SELECT
                    mu.id, mu.text, mu.context, mu.event_date,
                    mu.occurred_start, mu.occurred_end, mu.mentioned_at, mu.fact_type,
                    mu.document_id, mu.chunk_id, mu.tags, mu.proof_count,
                    mu.source_memory_ids
                FROM ctxdb_ws_agent_memory.memory_units mu
                JOIN candidate_ids ci ON ci.id = mu.id
                WHERE mu.fact_type = 'observation'
                  AND mu.id != ALL($1::uuid[])

            ),
            scored AS (
                SELECT c.id, COUNT(DISTINCT cs.source_id)::float AS score
                FROM candidates c
                CROSS JOIN LATERAL unnest(c.source_memory_ids) AS s(source_id)
                JOIN connected_sources cs ON cs.source_id = s.source_id
                GROUP BY c.id
            ),
            observation_entity_expanded AS (
                SELECT
                    c.id, c.text, c.context, c.event_date,
                    c.occurred_start, c.occurred_end, c.mentioned_at, c.fact_type,
                    c.document_id, c.chunk_id, c.tags, c.proof_count,
                    sc.score,
                    'entity'::text AS source
                FROM candidates c
                JOIN scored sc ON sc.id = c.id
                ORDER BY sc.score DESC
                LIMIT $2
            ),
            -- Exact v0.5.6 query shape: GROUP BY + MAX(weight) for semantic,
            -- DISTINCT ON for causal, hardcoded to fact_type='observation'.
            semantic_expanded AS (
                SELECT
                    id, text, context, event_date,
                    occurred_start, occurred_end, mentioned_at, fact_type,
                    document_id, chunk_id, tags, proof_count,
                    MAX(weight) AS score,
                    'semantic'::text AS source
                FROM (
                    SELECT mu.id, mu.text, mu.context, mu.event_date,
                           mu.occurred_start, mu.occurred_end, mu.mentioned_at, mu.fact_type,
                           mu.document_id, mu.chunk_id, mu.tags, mu.proof_count,
                           ml.weight
                    FROM ctxdb_ws_agent_memory.memory_links ml JOIN ctxdb_ws_agent_memory.memory_units mu ON mu.id = ml.to_unit_id
                    WHERE ml.from_unit_id = ANY($1::uuid[])
                      AND ml.link_type = 'semantic' AND mu.fact_type = 'observation'
                      AND mu.id != ALL($1::uuid[])

                    UNION ALL
                    SELECT mu.id, mu.text, mu.context, mu.event_date,
                           mu.occurred_start, mu.occurred_end, mu.mentioned_at, mu.fact_type,
                           mu.document_id, mu.chunk_id, mu.tags, mu.proof_count,
                           ml.weight
                    FROM ctxdb_ws_agent_memory.memory_links ml JOIN ctxdb_ws_agent_memory.memory_units mu ON mu.id = ml.from_unit_id
                    WHERE ml.to_unit_id = ANY($1::uuid[])
                      AND ml.link_type = 'semantic' AND mu.fact_type = 'observation'
                      AND mu.id != ALL($1::uuid[])

                ) sem_raw
                GROUP BY id, text, context, event_date,
                         occurred_start, occurred_end, mentioned_at, fact_type,
                         document_id, chunk_id, tags, proof_count
                ORDER BY score DESC LIMIT $2
            ),
            causal_expanded AS (
                SELECT DISTINCT ON (mu.id)
                    mu.id, mu.text, mu.context, mu.event_date,
                    mu.occurred_start, mu.occurred_end, mu.mentioned_at, mu.fact_type,
                    mu.document_id, mu.chunk_id, mu.tags, mu.proof_count,
                    ml.weight AS score, 'causal'::text AS source
                FROM ctxdb_ws_agent_memory.memory_links ml JOIN ctxdb_ws_agent_memory.memory_units mu ON ml.to_unit_id = mu.id
                WHERE ml.from_unit_id = ANY($1::uuid[])
                  AND ml.link_type IN ('causes', 'caused_by', 'enables', 'prevents')
                  AND mu.fact_type = 'observation'

                ORDER BY mu.id, ml.weight DESC LIMIT $2
            )
            SELECT * FROM observation_entity_expanded
            UNION ALL
            SELECT * FROM semantic_expanded
            UNION ALL
            SELECT * FROM causal_expanded
```

## SQL-042

普通事实图扩展：共享实体、双向语义边、出向因果边三路 SQL 联合；共享实体计数与各路限流在库内，最终图评分在 Python。

观测阶段：`21-dual-rrf-recall`、`22-dual-rrf-reflect`、`23-dual-maas-recall`、`24-dual-maas-reflect`、`25-dual-maas100-reflect`。应用调用 18 次；关联 PG 执行 18 次。首条发送记录：provider=`rrf`、qid=`203`、PID=`49673`。

```sql
WITH
            seed_entities AS (
                SELECT DISTINCT ue.entity_id
                FROM ctxdb_ws_agent_memory.unit_entities ue
                WHERE ue.unit_id = ANY($1::uuid[])
            ),
            entity_expanded AS (
                SELECT mu.id, mu.text, mu.context, mu.event_date,
                       mu.occurred_start, mu.occurred_end, mu.mentioned_at, mu.fact_type,
                       mu.document_id, mu.chunk_id, mu.tags, mu.proof_count,
                       COUNT(DISTINCT se.entity_id)::float AS score,
                       'entity'::text AS source
                FROM seed_entities se
                CROSS JOIN LATERAL (
                    SELECT ue_target.unit_id
                    FROM ctxdb_ws_agent_memory.unit_entities ue_target
                    WHERE ue_target.entity_id = se.entity_id
                      AND ue_target.unit_id != ALL($1::uuid[])
                      -- Filter before applying the cap: candidates from other fact
                      -- types, or outside the recall window, must not consume this
                      -- entity's bounded fan-out.
                      AND EXISTS (
                          SELECT 1
                          FROM ctxdb_ws_agent_memory.memory_units mu_target
                          WHERE mu_target.id = ue_target.unit_id
                            AND mu_target.fact_type = $2

                      )
                    ORDER BY ue_target.unit_id DESC
                    LIMIT 200
                ) t
                JOIN ctxdb_ws_agent_memory.memory_units mu ON mu.id = t.unit_id
                GROUP BY mu.id
                ORDER BY score DESC
                LIMIT $3
            ),

            semantic_expanded AS (
                SELECT
                    id, text, context, event_date,
                    occurred_start, occurred_end, mentioned_at, fact_type,
                    document_id, chunk_id, tags, proof_count,
                    MAX(weight) AS score,
                    'semantic'::text AS source
                FROM (
                    SELECT
                        mu.id, mu.text, mu.context, mu.event_date,
                        mu.occurred_start, mu.occurred_end, mu.mentioned_at, mu.fact_type,
                        mu.document_id, mu.chunk_id, mu.tags, mu.proof_count,
                        ml.weight
                    FROM ctxdb_ws_agent_memory.memory_links ml
                    JOIN ctxdb_ws_agent_memory.memory_units mu ON mu.id = ml.to_unit_id
                    WHERE ml.from_unit_id = ANY($1::uuid[])
                      AND ml.link_type = 'semantic'
                      AND mu.fact_type = $2
                      AND mu.id != ALL($1::uuid[])

                    UNION ALL
                    SELECT
                        mu.id, mu.text, mu.context, mu.event_date,
                        mu.occurred_start, mu.occurred_end, mu.mentioned_at, mu.fact_type,
                        mu.document_id, mu.chunk_id, mu.tags, mu.proof_count,
                        ml.weight
                    FROM ctxdb_ws_agent_memory.memory_links ml
                    JOIN ctxdb_ws_agent_memory.memory_units mu ON mu.id = ml.from_unit_id
                    WHERE ml.to_unit_id = ANY($1::uuid[])
                      AND ml.link_type = 'semantic'
                      AND mu.fact_type = $2
                      AND mu.id != ALL($1::uuid[])

                ) sem_raw
                GROUP BY id, text, context, event_date,
                         occurred_start, occurred_end, mentioned_at, fact_type,
                         document_id, chunk_id, tags, proof_count
                ORDER BY score DESC
                LIMIT $3
            ),
            causal_expanded AS (
                SELECT DISTINCT ON (mu.id)
                    mu.id, mu.text, mu.context, mu.event_date,
                    mu.occurred_start, mu.occurred_end, mu.mentioned_at, mu.fact_type,
                    mu.document_id, mu.chunk_id, mu.tags, mu.proof_count,
                    ml.weight AS score,
                    'causal'::text AS source
                FROM ctxdb_ws_agent_memory.memory_links ml
                JOIN ctxdb_ws_agent_memory.memory_units mu ON ml.to_unit_id = mu.id
                WHERE ml.from_unit_id = ANY($1::uuid[])
                  AND ml.link_type IN ('causes', 'caused_by', 'enables', 'prevents')
                  AND mu.fact_type = $2

                ORDER BY mu.id, ml.weight DESC
                LIMIT $3
            )
            SELECT * FROM entity_expanded
            UNION ALL
            SELECT * FROM semantic_expanded
            UNION ALL
            SELECT * FROM causal_expanded
```

## SQL-043

补全返回事实的实体名；Observation 没有直接实体时通过其来源事实推导实体。

观测阶段：`21-dual-rrf-recall`、`22-dual-rrf-reflect`、`23-dual-maas-recall`、`25-dual-maas100-reflect`。应用调用 7 次；关联 PG 执行 7 次。首条发送记录：provider=`rrf`、qid=`207`、PID=`49742`。

```sql
(SELECT ue.unit_id, e.id AS entity_id, e.canonical_name FROM ctxdb_ws_agent_memory.unit_entities ue JOIN ctxdb_ws_agent_memory.entities e ON e.id = ue.entity_id WHERE ue.unit_id = ANY($1::uuid[])) UNION (SELECT obs.id AS unit_id, e.id AS entity_id, e.canonical_name FROM ctxdb_ws_agent_memory.memory_units obs CROSS JOIN LATERAL unnest(obs.source_memory_ids) AS src_id JOIN ctxdb_ws_agent_memory.unit_entities src_ue ON src_ue.unit_id = src_id JOIN ctxdb_ws_agent_memory.entities e ON e.id = src_ue.entity_id WHERE obs.id = ANY($1::uuid[]) AND obs.fact_type = 'observation' AND obs.source_memory_ids IS NOT NULL AND NOT EXISTS (SELECT 1 FROM ctxdb_ws_agent_memory.unit_entities d WHERE d.unit_id = obs.id))
```

## SQL-044

按最终结果 ID 批量读取 id、document_id 和 attachment_ids，供文档/附件引用补全；此处不读取正文。

观测阶段：`21-dual-rrf-recall`、`22-dual-rrf-reflect`、`23-dual-maas-recall`。应用调用 3 次；关联 PG 执行 3 次。首条发送记录：provider=`rrf`、qid=`209`、PID=`49742`。

```sql
SELECT id::text AS id, document_id, attachment_ids FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $1 AND id = ANY($2::uuid[])
```

## SQL-045

检查或读取附件引用；本次文本请求也会执行通用附件补全路径。

观测阶段：`21-dual-rrf-recall`、`23-dual-maas-recall`。应用调用 2 次；关联 PG 执行 2 次。首条发送记录：provider=`rrf`、qid=`210`、PID=`49742`。

```sql
SELECT 1 WHERE EXISTS (SELECT 1 FROM ctxdb_ws_agent_memory.attachments WHERE bank_id = $1)
```

## SQL-046

确认 Bank 存在；带 FOR NO KEY UPDATE 时还序列化该 Bank 的任务提交。

观测阶段：`22-dual-rrf-reflect`、`24-dual-maas-reflect`、`25-dual-maas100-reflect`。应用调用 5 次；关联 PG 执行 5 次。首条发送记录：provider=`rrf`、qid=`221`、PID=`49742`。

```sql
SELECT 1 FROM ctxdb_ws_agent_memory.banks WHERE bank_id = $1
```

## SQL-047

读取事实整合/写入水位及待整合、失败数量，为 reflect 判断知识新鲜度提供状态。

观测阶段：`22-dual-rrf-reflect`、`24-dual-maas-reflect`、`25-dual-maas100-reflect`。应用调用 3 次；关联 PG 执行 3 次。首条发送记录：provider=`rrf`、qid=`223`、PID=`49742`。

```sql
SELECT
            MAX(consolidated_at) AS last_consolidated_at,
            MAX(updated_at) AS last_memory_write_at,
            COUNT(*) FILTER (
                WHERE consolidated_at IS NULL
                  AND consolidation_failed_at IS NULL
                  AND fact_type IN ('experience', 'world')
            ) AS pending,
            COUNT(*) FILTER (WHERE consolidation_failed_at IS NOT NULL AND fact_type IN ('experience', 'world')) AS failed
        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $1
```

## SQL-048

统计本次 reflect 可应用的行为规则；这是同接口分页实现带来的附加查询。

观测阶段：`22-dual-rrf-reflect`、`24-dual-maas-reflect`、`25-dual-maas100-reflect`。应用调用 3 次；关联 PG 执行 3 次。首条发送记录：provider=`rrf`、qid=`225`、PID=`49742`。

```sql
SELECT COUNT(*)
                FROM ctxdb_ws_agent_memory.directives
                WHERE bank_id = $1 AND is_active = TRUE AND (tags IS NULL OR tags = '{}')
```

## SQL-049

读取启用且在请求作用域内的行为规则，按优先级提供给 reflect 的提示词。

观测阶段：`22-dual-rrf-reflect`、`24-dual-maas-reflect`、`25-dual-maas100-reflect`。应用调用 3 次；关联 PG 执行 3 次。首条发送记录：provider=`rrf`、qid=`226`、PID=`49742`。

```sql
SELECT id, bank_id, name, content, priority, is_active, tags, created_at, updated_at
                FROM ctxdb_ws_agent_memory.directives
                WHERE bank_id = $1 AND is_active = TRUE AND (tags IS NULL OR tags = '{}')
                ORDER BY priority DESC, created_at DESC, id DESC
                LIMIT $2 OFFSET $3
```

## SQL-050

一条 SQL 合并向量与关键词召回；每种事实类型、每条检索分支独立 ORDER BY/LIMIT，返回正文与分数。关键词实际为 ts_rank_cd。

观测阶段：`22-dual-rrf-reflect`、`24-dual-maas-reflect`、`25-dual-maas100-reflect`。应用调用 7 次；关联 PG 执行 7 次。首条发送记录：provider=`rrf`、qid=`233`、PID=`49742`。

```sql
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,        NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'world'   AND embedding IS NOT NULL   AND (1 - (embedding <=> $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,        NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'experience'   AND embedding IS NOT NULL   AND (1 - (embedding <=> $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,        ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'world'   AND search_vector @@ to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC LIMIT $3)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,        ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'experience'   AND search_vector @@ to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC LIMIT $3)
```

## SQL-051

批量补读原文片段，供 recall/reflect 的来源展示或证据展开使用。

观测阶段：`22-dual-rrf-reflect`、`25-dual-maas100-reflect`。应用调用 5 次；关联 PG 执行 5 次。首条发送记录：provider=`rrf`、qid=`239`、PID=`49742`。

```sql
SELECT chunk_id, chunk_text, chunk_index, document_id
            FROM ctxdb_ws_agent_memory.chunks
            WHERE chunk_id = ANY($1::text[])
```

## SQL-052

按事件/提及时间与窗口重叠条件寻找时序入口；每种类型先取相似度最高的 60 条。

观测阶段：`22-dual-rrf-reflect`、`25-dual-maas100-reflect`。应用调用 3 次；关联 PG 执行 3 次。首条发送记录：provider=`rrf`、qid=`259`、PID=`49742`。

```sql
(
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $2
          AND fact_type = 'world'
          AND embedding IS NOT NULL
          AND (
              (occurred_start IS NOT NULL AND occurred_end IS NOT NULL
               AND occurred_start <= $4 AND occurred_end >= $3)
              OR
              (mentioned_at IS NOT NULL AND mentioned_at BETWEEN $3 AND $4)
              OR
              (occurred_start IS NOT NULL AND occurred_start BETWEEN $3 AND $4)
              OR
              (occurred_end IS NOT NULL AND occurred_end BETWEEN $3 AND $4)
          )
          AND (1 - (embedding <=> $1::vector)) >= $5



        ORDER BY embedding <=> $1::vector
        LIMIT 60
        )
UNION ALL
(
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $2
          AND fact_type = 'experience'
          AND embedding IS NOT NULL
          AND (
              (occurred_start IS NOT NULL AND occurred_end IS NOT NULL
               AND occurred_start <= $4 AND occurred_end >= $3)
              OR
              (mentioned_at IS NOT NULL AND mentioned_at BETWEEN $3 AND $4)
              OR
              (occurred_start IS NOT NULL AND occurred_start BETWEEN $3 AND $4)
              OR
              (occurred_end IS NOT NULL AND occurred_end BETWEEN $3 AND $4)
          )
          AND (1 - (embedding <=> $1::vector)) >= $5



        ORDER BY embedding <=> $1::vector
        LIMIT 60
        )
```

## SQL-053

按事实 ID 批量读取正文/来源/元数据，供事实引用、证据展开或来源校验。

观测阶段：`22-dual-rrf-reflect`。应用调用 1 次；关联 PG 执行 1 次。首条发送记录：provider=`rrf`、qid=`316`、PID=`49742`。

```sql
SELECT
    id, text, fact_type, context, document_id, chunk_id, tags, metadata,
    proof_count, event_date, occurred_start, occurred_end, mentioned_at,
    created_at, updated_at, source_memory_ids, consolidated_at, observation_scopes

        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $1 AND id = ANY($2::uuid[])
```

## SQL-054

一条 SQL 合并向量与关键词召回；每种事实类型、每条检索分支独立 ORDER BY/LIMIT，返回正文与分数。关键词实际为 ts_rank_cd。

观测阶段：`23-dual-maas-recall`。应用调用 1 次；关联 PG 执行 1 次。首条发送记录：provider=`siliconflow`、qid=`148`、PID=`49674`。

```sql
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,        NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'experience'   AND embedding IS NOT NULL   AND (1 - (embedding <=> $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,        NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'observation'   AND embedding IS NOT NULL   AND (1 - (embedding <=> $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,        NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'world'   AND embedding IS NOT NULL   AND (1 - (embedding <=> $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,        ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'experience'   AND search_vector @@ to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC LIMIT $3)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,        ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'observation'   AND search_vector @@ to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC LIMIT $3)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id, chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,        ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'world'   AND search_vector @@ to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC LIMIT $3)
```

## SQL-055

按事件/提及时间与窗口重叠条件寻找时序入口；每种类型先取相似度最高的 60 条。

观测阶段：`23-dual-maas-recall`。应用调用 1 次；关联 PG 执行 1 次。首条发送记录：provider=`siliconflow`、qid=`149`、PID=`49674`。

```sql
(
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $2
          AND fact_type = 'experience'
          AND embedding IS NOT NULL
          AND (
              (occurred_start IS NOT NULL AND occurred_end IS NOT NULL
               AND occurred_start <= $4 AND occurred_end >= $3)
              OR
              (mentioned_at IS NOT NULL AND mentioned_at BETWEEN $3 AND $4)
              OR
              (occurred_start IS NOT NULL AND occurred_start BETWEEN $3 AND $4)
              OR
              (occurred_end IS NOT NULL AND occurred_end BETWEEN $3 AND $4)
          )
          AND (1 - (embedding <=> $1::vector)) >= $5



        ORDER BY embedding <=> $1::vector
        LIMIT 60
        )
UNION ALL
(
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $2
          AND fact_type = 'observation'
          AND embedding IS NOT NULL
          AND (
              (occurred_start IS NOT NULL AND occurred_end IS NOT NULL
               AND occurred_start <= $4 AND occurred_end >= $3)
              OR
              (mentioned_at IS NOT NULL AND mentioned_at BETWEEN $3 AND $4)
              OR
              (occurred_start IS NOT NULL AND occurred_start BETWEEN $3 AND $4)
              OR
              (occurred_end IS NOT NULL AND occurred_end BETWEEN $3 AND $4)
          )
          AND (1 - (embedding <=> $1::vector)) >= $5



        ORDER BY embedding <=> $1::vector
        LIMIT 60
        )
UNION ALL
(
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $2
          AND fact_type = 'world'
          AND embedding IS NOT NULL
          AND (
              (occurred_start IS NOT NULL AND occurred_end IS NOT NULL
               AND occurred_start <= $4 AND occurred_end >= $3)
              OR
              (mentioned_at IS NOT NULL AND mentioned_at BETWEEN $3 AND $4)
              OR
              (occurred_start IS NOT NULL AND occurred_start BETWEEN $3 AND $4)
              OR
              (occurred_end IS NOT NULL AND occurred_end BETWEEN $3 AND $4)
          )
          AND (1 - (embedding <=> $1::vector)) >= $5



        ORDER BY embedding <=> $1::vector
        LIMIT 60
        )
```

## SQL-056

开始、提交或回滚事务；确定锁、临时表和事务局部参数的生命周期。

观测阶段：`26-dual-retain-with-transactions`。应用调用 3 次；关联 PG 执行 3 次。首条发送记录：provider=`siliconflow100`、qid=`222`、PID=`50258`。

```sql
BEGIN;
```

## SQL-057

开始、提交或回滚事务；确定锁、临时表和事务局部参数的生命周期。

观测阶段：`26-dual-retain-with-transactions`。应用调用 3 次；关联 PG 执行 3 次。首条发送记录：provider=`siliconflow100`、qid=`238`、PID=`50258`。

```sql
COMMIT;
```

## SQL-058

读取或检查知识正文、刷新水位和作用域；与原始事实召回分开。

证据级别：仅 PG 执行审计，来自原服务 `11-agent-reflect` 时间窗口；没有该请求的应用侧记录。窗口内可能含 UI 或后台请求，不能仅凭时间认定归属 reflect。SQL-059 的知识向量检索另有 reflect 工具 trace 交叉确认；其余条目作为窗口观察保留，不进入双向请求 SQL 计数。

```sql
SELECT COUNT(*) FROM ctxdb_ws_agent_memory.mental_models WHERE bank_id = $1
```

## SQL-059

按向量检索高层知识正文 Mental Models，供 reflect 优先使用已有整理结果。

证据级别：仅 PG 执行审计，来自原服务 `11-agent-reflect` 时间窗口；没有该请求的应用侧记录。窗口内可能含 UI 或后台请求，不能仅凭时间认定归属 reflect。SQL-059 的知识向量检索另有 reflect 工具 trace 交叉确认；其余条目作为窗口观察保留，不进入双向请求 SQL 计数。

```sql
SELECT
	                id, name, content,
	                tags, created_at, last_refreshed_at, last_memory_seen_at, trigger,
	                1 - (embedding <=> $2::vector) as relevance
	            FROM ctxdb_ws_agent_memory.mental_models
	            WHERE bank_id = $1 AND embedding IS NOT NULL
	            ORDER BY embedding <=> $2::vector
	            LIMIT $3
```

## SQL-060

读取或检查知识正文、刷新水位和作用域；与原始事实召回分开。

证据级别：仅 PG 执行审计，来自原服务 `11-agent-reflect` 时间窗口；没有该请求的应用侧记录。窗口内可能含 UI 或后台请求，不能仅凭时间认定归属 reflect。SQL-059 的知识向量检索另有 reflect 工具 trace 交叉确认；其余条目作为窗口观察保留，不进入双向请求 SQL 计数。

```sql
SELECT kp.id, kp.bank_id, kp.parent_id, kp.kind, kp.name, kp.mental_model_id, kp.sort_order, kp.managed, kp.created_at, kp.updated_at, mm.tags AS mm_tags, mm.source_query AS mm_source_query, mm.trigger AS mm_trigger, mm.last_refreshed_at AS mm_last_refreshed_at, mm.last_refresh_failed_at AS mm_last_refresh_failed_at, mm.last_memory_seen_at AS mm_last_memory_seen_at, mm.content AS mm_content
	                FROM ctxdb_ws_agent_memory.knowledge_pages kp LEFT JOIN ctxdb_ws_agent_memory.mental_models mm ON mm.id = kp.mental_model_id AND mm.bank_id = kp.bank_id
	                WHERE kp.bank_id = $1 AND kp.id = $2 AND kp.kind = 'page'
```

## SQL-061

读取或检查知识正文、刷新水位和作用域；与原始事实召回分开。

证据级别：仅 PG 执行审计，来自原服务 `11-agent-reflect` 时间窗口；没有该请求的应用侧记录。窗口内可能含 UI 或后台请求，不能仅凭时间认定归属 reflect。SQL-059 的知识向量检索另有 reflect 工具 trace 交叉确认；其余条目作为窗口观察保留，不进入双向请求 SQL 计数。

```sql
SELECT kp.id, kp.bank_id, kp.parent_id, kp.kind, kp.name, kp.mental_model_id, kp.sort_order, kp.managed, kp.created_at, kp.updated_at, mm.tags AS mm_tags, mm.source_query AS mm_source_query, mm.trigger AS mm_trigger, mm.last_refreshed_at AS mm_last_refreshed_at, mm.last_refresh_failed_at AS mm_last_refresh_failed_at, mm.last_memory_seen_at AS mm_last_memory_seen_at
	                FROM ctxdb_ws_agent_memory.knowledge_pages kp LEFT JOIN ctxdb_ws_agent_memory.mental_models mm ON mm.id = kp.mental_model_id AND mm.bank_id = kp.bank_id
	                WHERE kp.bank_id = $1
```

## SQL-062

读取或检查知识正文、刷新水位和作用域；与原始事实召回分开。

证据级别：仅 PG 执行审计，来自原服务 `11-agent-reflect` 时间窗口；没有该请求的应用侧记录。窗口内可能含 UI 或后台请求，不能仅凭时间认定归属 reflect。SQL-059 的知识向量检索另有 reflect 工具 trace 交叉确认；其余条目作为窗口观察保留，不进入双向请求 SQL 计数。

```sql
SELECT id, bank_id, name, source_query, content, tags,
	                       last_refreshed_at, last_memory_seen_at, last_refresh_failed_at, created_at, reflect_response,
	                       max_tokens, trigger, structured_content
	                FROM ctxdb_ws_agent_memory.mental_models
	                WHERE bank_id = $1 AND id = $2
```

## SQL-063

读取或检查知识正文、刷新水位和作用域；与原始事实召回分开。

证据级别：仅 PG 执行审计，来自原服务 `11-agent-reflect` 时间窗口；没有该请求的应用侧记录。窗口内可能含 UI 或后台请求，不能仅凭时间认定归属 reflect。SQL-059 的知识向量检索另有 reflect 工具 trace 交叉确认；其余条目作为窗口观察保留，不进入双向请求 SQL 计数。

```sql
SELECT reflect_response FROM ctxdb_ws_agent_memory.mental_models WHERE bank_id = $1 AND id = $2
```
