# Hindsight 记忆检索执行分析与 PostgreSQL 增强方案

**技术分析报告｜2026-11-12**

[1. 执行摘要](#executive-summary) · [2. Recall 执行分析](#chapter4) · [3. PG 增强方案](#chapter7) · [附录 A：接口参考](#api-appendix) · [附录 B：架构与选型](#independent-review)

本报告聚焦 Recall 执行机制与 PG 增强方案，包含完整 SQL、调用次数与耗时分析。附录 A 提供厂商接口参考，附录 B 评估数据库通用性、模型部署、AGE 选型和 Reflect 执行能力。

**范围与架构边界：** 第二章记录现场实测，第三章提出执行增强方案，附录 B 讨论选型与实施优先级。MemoryRecall 定位为 Hindsight 适配/SQL 包装入口，PG 底层提供通用执行机制，不固化 world、observation 等业务类型。拟研发机制尚未实现，性能收益有待验证。

**实测范围：** PG 16.15、pgvector 0.6.0；agent_memory 共 2,002 条记忆。请求 21 使用 RRF，请求 23 使用 MaaS 模型，两条时间线分别分析；19 次业务 SQL、PG execute 累计、应用调用累计和 HTTP 时间不是同一口径。

<a id="executive-summary"></a>

## 1. 执行摘要

**本报告回答两个问题：Hindsight 的一次 Recall 如何调用 PG，以及 PG 应增强哪些执行能力。** 第二章给出现有流程、完整 SQL 与实测耗时，第三章提出增强方案；现状与拟建设能力分别说明。

| 分析结论 | 实测依据 | 对增强方案的启示 |
|---|---|---|
| **当前 Recall 需要应用分步编排，四路检索未完全并行** | 主样本执行 19 次业务 SQL：2 次准备、14 次检索、3 次补全；图扩展在时序路径完成后启动，图任务内部存在局部并发 | 用统一入口组织融合执行计划；独立任务并行，图扩展按起点依赖启动，关系扩展在库内迭代 |
| **候选融合前已读取正文，存在减少宽字段搬运的空间** | 四路交给融合的 1,915 条记录，按 ID 合并为 1,032 条，再裁剪为 300 条候选 | 融合与 Top-K 阶段优先传递 ID、分数和必要属性，入选后再读取正文；存储 I/O 收益需另行验证 |
| **数据库优化应集中在检索阶段** | 主样本 PG execute 累计 360.034 ms；向量＋关键词查询占 212.779 ms，图与时序阶段合计 144.085 ms，结果补全仅 2.982 ms | 优先优化检索访问、执行调度与迭代；在具备可靠分数上界的访问路径实施 Top-K 提前剪枝 |
| **启用模型后，模型服务可能成为主要耗时来源** | 独立 MaaS 样本中，重排阶段 7.782 s、检索阶段 493 ms；不能与主样本 SQL 时间拼接 | 提供批量模型重排执行能力，并分别评估模型部署、吞吐与预算；仅将同一模型迁入数据库不会自动提升质量或缩短推理时间 |

**建议建设：一个 MemoryRecall 适配入口，两项执行能力——融合检索执行、批量模型重排。** 检索侧重点研发延迟物化、依赖感知并行与库内迭代、Top-K 动态剪枝，分别争取减少数据搬运、串行等待与无效计算。MemoryRecall 表达 Hindsight 的业务规则，PG 底层保持通用。

**验收以同等检索质量下的端到端延迟、资源消耗和吞吐为准。** 接口合并不等于减少数据库工作；减少候选搬运不等于提升召回质量。上述机制尚未实现，预期收益需要通过同条件测试验证。AGE、模型部署方式和 Reflect 的扩展讨论见附录 B，不作为本报告主线结论。

---

<a id="chapter4"></a>

## 2. Recall 执行流程与 SQL 耗时分析

### 2.1 执行概览：调度顺序、SQL 次数与结果规模

**Recall 先通过四种策略找候选，再融合、裁剪和排序，最后限制返回的记忆正文总长度。四种策略不等于四次 SQL，也不意味着四路同时执行。**

本章以真实 Bank `agent_memory` 的请求 **21** 为主样本：使用 RRF，HTTP 耗时 1.585 秒，执行 19 次已采集业务 SQL，最终返回 38 条记忆。请求 **23** 使用 MaaS 模型，作为独立对照，最终返回 35 条。先用主样本讲完整条交互，再说明模型路径的差别。

#### 2.1.1 检索、融合与补全的调度顺序

```text
读取 Bank 信息与配置
    ↓
应用生成查询向量
    ↓
向量＋关键词：一条组合 SQL
    ↓
时序检索：先找入口，再按批次扩展邻居
    ↓
图检索：按三种事实类型调度，存在局部并发
    ↓
应用合并候选并排序，再选择总长度符合上限的记忆
    ↓
补全实体与文档/附件引用
    ↓
主样本返回 38 条记忆
```

向量＋关键词、时序入口及后续扩展先后执行；图任务在这些步骤结束后才启动。图扩展依赖语义种子，但代码中还等待了整条时序路径结束。不能根据 trace 阶段名 `parallel_retrieval` 判断为“四路完全并行”。

#### 2.1.2 19 次业务 SQL 的阶段分布

| 执行阶段 | 本次 SQL 次数 | SQL 编号 | 做什么 |
|---|---:|---|---|
| 准备 | **2** | SQL-036、037 | 读 Bank 信息和配置 |
| 向量＋关键词 | **1** | SQL-038 | 一条 SQL 包含三种事实类型各自的向量、关键词分支，共六个分支 |
| 时序入口 | **1** | SQL-039 | 按时间窗找入口候选 |
| 时序扩展 | **9** | SQL-040 | 同一 SQL 按类型和本批节点重复执行：observation 1 批、experience 3 批、world 5 批 |
| 图扩展 | **3** | SQL-041、042 | Observation 1 次；world、experience 各 1 次 |
| 应用合并、排序、控制返回长度 | **0** | Python 处理 | 这部分在应用中完成；启用 MaaS 时还会调用模型服务 |
| 结果补全 | **3** | SQL-043、044、045 | 补充实体、读取文档/附件引用、检查附件是否存在 |
| **合计** | **19** | **2＋1＋1＋9＋3＋0＋3** | **2 次准备＋14 次检索＋3 次补全** |

这里统计的是本请求已捕获的业务 SQL，排除管理面鉴权、连接初始化和异步 usage 统计。SQL-038 的六个分支只算一次应用 SQL 调用；“应用处理 0 次 SQL”也不表示没有 CPU、网络或模型成本。每种 SQL 的全文放在后面对应步骤，重复调用不重复粘贴全文。

#### 2.1.3 候选集合与最终返回结果的变化

| 处理位置 | 主样本请求 21（RRF） | 数量的含义 |
|---|---:|---|
| 四路交给 RRF 的候选汇总 | **1,915 条记录** | 向量 642＋关键词 502＋图 622＋时序 149；跨路可能重复 |
| 按 ID 合并并融合排名 | **1,032 条不同记忆** | 同一记忆合为一条，各路名次仍共同贡献分数 |
| 按融合排名裁剪 | **300 条候选** | 本次排序候选预算；其余 732 条不进入后续排序处理 |
| 排好顺序后，选出正文总长度不超过 4,000 Token 的记忆 | **38 条记忆** | 本次不用重排模型；应用按排名和长度选择，正文共 3,992 Token |
| 实体/附件补全后返回 | **仍为 38 条记忆** | 补充信息，不重新加回未入选候选 |

**独立 MaaS 对照请求 23：** 四路计数、合并数量和 300 条候选上限相同；模型对 300 组问题/正文返回 300 个评分，随后应用按分数和时间等规则排序，再按正文总长度上限选出 **35 条、3,999 Token**。35 条不是模型直接淘汰后的数量。同样的预算容纳条数不同，取决于优先装入的内容与长度，不能据此判断哪次检索质量更高。

以上计数属于不同层次：1,915 是各路整理后交给 RRF 的候选数，不是所有 PG 查询返回行数之和；1,032 是唯一记忆数；300 是候选上限；38/35 是最终内容预算下的结果数。两次请求的计数相同，也不保证具体候选和顺序完全相同。结果选择细节见 2.6 节。

#### 2.1.4 分阶段耗时与主要成本

同一主样本的 HTTP 总耗时为 **1,585 ms**。下表分别统计应用驱动调用耗时和 PG 执行阶段耗时：

| 阶段 | SQL 次数 | 应用侧调用耗时合计 ms | PG execute 耗时合计 ms | 占本样本 PG execute 合计的比例 |
|---|---:|---:|---:|---:|
| 准备 | 2 | 7.167 | 0.188 | 0.1% |
| 向量＋关键词 | 1 | 539.147 | 212.779 | 59.1% |
| 时序入口 | 1 | 25.473 | 18.875 | 5.2% |
| 时序扩展 | 9 | 107.575 | 65.017 | 18.1% |
| 图扩展 | 3 | 246.279 | 60.193 | 16.7% |
| 结果补全 | 3 | 16.472 | 2.982 | 0.8% |
| **合计** | **19** | **942.112** | **360.034** | **100%** |

- **应用侧耗时**：从驱动调用开始到取得结果，包含 PG 协议处理、执行、传输、驱动解码和调度等。它不等于纯网络时间。
- **PG execute 耗时**：数据库日志记录的执行阶段时间，不是纯 CPU 时间，也不包含单独记录的 parse/bind 等所有工作。
- **两个合计都不是请求总耗时。** 图查询有重叠区间，逐条相加会重复计算部分时间；请求还包括生成向量、RRF、结果处理及未计入这些业务 SQL 的其他开销。因此不能用 1,585 减去 360.034 就断言其余全是应用或网络开销。

**本次应优先分析向量＋关键词查询，再分析图/时间扩展与阶段等待。** 3 次结果补全的 PG 执行合计仅约 3 ms，调用次数虽可合并，却不是本次主要 SQL 耗时来源。逐条双侧时间见 2.8.1 节，具体优化判断见 2.9 节。

### 2.2 第一步：读取 Bank 信息与配置——2 次 SQL

应用先确认当前记忆库的身份、目标和配置，为随后检索准备上下文。本次两个查询分别返回一条记录。

**SQL-036：读取 Bank 名称、立场和任务目标，执行 1 次（R01）。** `$1=agent_memory`。

```sql
SELECT name, disposition, mission
        FROM ctxdb_ws_agent_memory.banks WHERE bank_id = $1
```

**SQL-037：读取 Bank 配置，执行 1 次（R02）。** `$1=agent_memory`。

```sql
SELECT config FROM ctxdb_ws_agent_memory.banks WHERE bank_id = $1
```

接下来应用生成 1024 维查询向量。向量生成是应用/模型步骤，不计入上述业务 SQL；随后 PG 同时接收向量和关键词查询文本。

### 2.3 第二步：向量与关键词一起召回——1 次 SQL

**这一查询解决两个问题：内容在意思上是否相关，文字上是否包含相关词项。** 本次检索 observation、experience、world 三种事实类型，每种都有向量与关键词分支，六个分支用 `UNION ALL` 组合为 SQL-038，只调用一次（R03）。

- 向量分支用 `<=>` 计算余弦距离，各自排序并取前 300 条，同时要求相似度至少为 0.3。
- 关键词分支用 `@@ to_tsquery(...)` 匹配，再按 `ts_rank_cd(...)` 排序并取预算内的候选。虽然输出列名为 `bm25_score`，本次原生分支实际不是 BM25 算法。
- 这条 SQL 已经返回正文、context、metadata 等字段，并非只返回 ID。

**输入。** `$1` 为查询向量，`$2=agent_memory`，`$3=300`；`$4` 是以下 OR 连接关键词：

```text
2026年9月至11月 | 团队为什么选择 | hindsight | 作为 | contextbase | 底座 | 而不是 | openviking | 和 | cognee | 有哪些已明确的选型边界
```

**完整 SQL-038：**

```sql
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id,
    chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,
    NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE
    bank_id = $2   AND fact_type = 'observation'   AND embedding IS NOT NULL   AND (1 - (embedding <=>
    $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id,
    chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,
    NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE
    bank_id = $2   AND fact_type = 'experience'   AND embedding IS NOT NULL   AND (1 - (embedding <=>
    $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id,
    chunk_id, tags, metadata, proof_count,        1 - (embedding <=> $1::vector) AS similarity,
    NULL::float AS bm25_score,        'semantic' AS source FROM ctxdb_ws_agent_memory.memory_units WHERE
    bank_id = $2   AND fact_type = 'world'   AND embedding IS NOT NULL   AND (1 - (embedding <=>
    $1::vector)) >= 0.3          ORDER BY embedding <=> $1::vector LIMIT 300)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id,
    chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,
    ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM
    ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'observation'   AND
    search_vector @@ to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector,
    to_tsquery('english', $4)) DESC LIMIT $3)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id,
    chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,
    ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM
    ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'experience'   AND search_vector
    @@ to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC
    LIMIT $3)
UNION ALL
(SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type, document_id,
    chunk_id, tags, metadata, proof_count,        NULL::float AS similarity,
    ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score,        'bm25' AS source FROM
    ctxdb_ws_agent_memory.memory_units WHERE bank_id = $2   AND fact_type = 'world'   AND search_vector @@
    to_tsquery('english', $4)          ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC
    LIMIT $3)
```

**返回与下一步。** 本次 PG 返回 **1,144 行**，应用整理为 semantic 642 条和 keyword 502 条。随后复用同一获取连接执行时序查询，而非先把四路结果立刻融合。向量结果也为后面的图检索提供起点，避免在条件允许时重复检索语义种子。

这是一条六分支 SQL，不是六次独立调用。本次只读计划回放观察到普通 `Append`，没有据此证明原请求六个分支并行；是否使用 HNSW 也要看实际计划，不能仅凭 SQL 形态判断。

### 2.4 第三步：找时间入口，再沿时间/因果关系扩展——1＋9 次 SQL

#### 2.4.1 时间与因果关系扩展示例

下面是假设例子，用于说明机制，**不是本次真实 Bank 中的记忆或测试结果**：

| 记忆 | 内容 |
|---|---|
| A | 11 月 1 日，Atlas 项目出现检索延迟高的问题 |
| B | 11 月 3 日，团队给 Atlas 增加了索引 |
| C | 11 月 5 日，Atlas 的检索延迟下降 |
| D | Alice 是 Atlas 的负责人 |
| E | Alice 还负责另一个项目的数据库优化 |

用户问“Atlas 在 11 月是怎么解决检索慢的问题的？”如果先找到 B，时间扩展会继续寻找相邻事件，希望把过程补齐：

```text
问题是什么？             做了什么？              后来有什么结果？
A：检索延迟高   ───→    B：增加索引   ───→    C：延迟下降
```

这表示时间顺序。如果库里还已经记录“增加索引促成延迟下降”的因果边，也可以沿该边从 B 找到 C。**日期先后本身不证明因果。** 后面的图扩展则会从共同项目 Atlas 找到 D，关注相关背景，见 2.5 节。

#### 2.4.2 SQL-039：先找入口候选，执行 1 次（R04）

应用已经提供时间窗 2026-09-01 至 2026-11-10。PG 用事件区间重叠或 mentioned_at / occurred_start / occurred_end 落在窗口内等条件找入口，再按向量相似度排序，每种类型最多取 60 条。

`$1` 为查询向量，`$2=agent_memory`，`$3/$4` 为时间窗开始与结束，`$5` 为相似度阈值。

```sql
(
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type,
    proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
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
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type,
    proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
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
        SELECT id, text, context, event_date, occurred_start, occurred_end, mentioned_at, fact_type,
    proof_count, document_id, chunk_id, tags, metadata, 1 - (embedding <=> $1::vector) AS similarity
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

**返回与后续处理。** 本次返回 **162 行入口候选**。应用按时间分桶选择入口，每种类型最多选 10 个，使入口不都集中在一个时间片，然后开始查邻居。

#### 2.4.3 SQL-040：批量查邻居，重复执行 9 次（R05～R13）

每次应用传入“当前准备继续扩展的一批节点”。PG 沿已有时间/因果边查邻居，对每个源节点限制边数，再关联目标事实并检查类型、相似度和适用过滤。应用接收结果后，更新已访问集合、传播得分、剩余预算和下一批节点。

`$1` 为查询向量，`$2` 为本批源节点 ID 数组，`$3` 为事实类型，`$4` 为相似度阈值，`$5` 为每源节点邻边上限，`$6=agent_memory`。

```sql
SELECT src.from_unit_id, mu.id, mu.text, mu.context, mu.event_date, mu.occurred_start, mu.occurred_end,
    mu.mentioned_at, mu.fact_type, mu.document_id, mu.chunk_id, mu.tags, mu.metadata, mu.proof_count,
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

同一 SQL 的不同参数形成以下 9 个查询批次：

| 调用 | 类型与批次 | 本批源节点数 | SQL 返回行数 |
|---|---|---:|---:|
| R05 | observation 第 1 批 | 10 | 0 |
| R06 | experience 第 1 批 | 10 | 93 |
| R07 | experience 第 2 批 | 20 | 184 |
| R08 | experience 第 3 批 | 12 | 101 |
| R09 | world 第 1 批 | 10 | 100 |
| R10 | world 第 2 批 | 20 | 200 |
| R11 | world 第 3 批 | 20 | 170 |
| R12 | world 第 4 批 | 20 | 181 |
| R13 | world 第 5 批 | 11 | 110 |

**9 次查询批次不等于同一条记忆沿关系走了 9 跳。** 每批处理多个节点，同一目标也可能经不同源节点或关系反复出现。应用保留适用的传播结果并控制预算，最后时序路交给 RRF 的是 **149 条候选**，不是上表返回行数的简单相加。

#### 2.4.4 时间窗的边界

时间窗直接用于 SQL-039 的入口选择，并参与后续时间接近度评分；SQL-040 **没有再用该事件时间窗硬过滤所有邻居**，因此扩展结果也可能在窗外。语义、关键词和图也不会因这个窗口自动排除窗外事实。`temporal_window` 应理解为时序检索与评分的输入，不是整个 recall 的硬过滤条件。

上述入口和扩展查询在主样本中先后执行，完成之后才进入图阶段。

### 2.5 第四步：找关联事实与背景——3 次图 SQL

#### 2.5.1 按事实类型组织图扩展

沿用 2.4 节的假设例子：B“给 Atlas 增加索引”和 D“Alice 是 Atlas 的负责人”都提到项目 Atlas，系统可以沿这个共同实体找到关联事实：

```text
B：给 Atlas 增加索引
          │
       共同项目：Atlas
          │
D：Alice 是 Atlas 的负责人
```

时间扩展侧重补齐事件过程；图扩展侧重补齐相关背景与证据。两者都可以使用因果边，也可能找到同一记忆，并非互斥分类。E 是 Alice 的其他资料，是否被带回取决于本次起点和扩展范围，不会沿所有关系无限查下去。

“按事实类型”是分别处理以下三种记忆，不是说图只有三种关系：

| 类型 | 含义 | 举例 |
|---|---|---|
| world | 外部世界的事实 | Atlas 使用 PostgreSQL |
| experience | Agent 自己参与的行动或经历 | 我执行了 Atlas 的索引检查 |
| observation | 根据来源事实整理出的结论 | Atlas 的主要瓶颈在关键词检索 |

图检索从向量检索选出的起点记忆出发。本次三个类型各有 20 个起点，执行以下查询：

| 调用 | 类型 | SQL | SQL 返回行数 |
|---|---|---|---:|
| R14 | observation | SQL-041 | 300 |
| R15 | world | SQL-042，绑定 world | 345 |
| R16 | experience | SQL-042，绑定 experience | 34 |
| **合计** | **3 次查询** | **两种 SQL 形态** | **679 行** |

三个任务由应用并发调度，但本次连接池上限为 2，仅有部分调用区间重叠，不能描述成“三条图 SQL 同时执行”。

#### 2.5.2 SQL-041：Observation 先通过来源事实寻找关联，执行 1 次

Observation 是整理后的结论，共享实体信息可能存在于其来源事实中。这条 SQL 先展开 `source_memory_ids`，通过来源事实的共享实体找到关联来源事实，再映射回 Observation；另外两条分支直接按起点 Observation ID 查询语义边和因果边，最后汇总三类结果。

`$1` 为本类型的 20 个起点 ID，`$2` 为图候选预算。

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
                    FROM ctxdb_ws_agent_memory.memory_links ml JOIN ctxdb_ws_agent_memory.memory_units mu ON
    mu.id = ml.to_unit_id
                    WHERE ml.from_unit_id = ANY($1::uuid[])
                      AND ml.link_type = 'semantic' AND mu.fact_type = 'observation'
                      AND mu.id != ALL($1::uuid[])

                    UNION ALL
                    SELECT mu.id, mu.text, mu.context, mu.event_date,
                           mu.occurred_start, mu.occurred_end, mu.mentioned_at, mu.fact_type,
                           mu.document_id, mu.chunk_id, mu.tags, mu.proof_count,
                           ml.weight
                    FROM ctxdb_ws_agent_memory.memory_links ml JOIN ctxdb_ws_agent_memory.memory_units mu ON
    mu.id = ml.from_unit_id
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
                FROM ctxdb_ws_agent_memory.memory_links ml JOIN ctxdb_ws_agent_memory.memory_units mu ON
    ml.to_unit_id = mu.id
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

#### 2.5.3 SQL-042：普通事实查共享实体、语义边和因果边，执行 2 次

world 和 experience 使用相同 SQL，分别绑定各自的类型及起点。SQL 内包括三条关联路径：共享实体计数、双向语义边最大权重、因果边去重，并对各路径限流。每个实体的扩展上限为 200。

`$1` 为当前类型的起点 ID 数组，`$2` 分别为 world 或 experience，`$3` 为该类型图预算。

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

**返回与后续处理。** 三次图查询共返回 679 行，各关系来源可能重复命中同一记忆。应用按以下规则合并图分数、去重并裁剪，得到 **622 条图候选**：

```text
图分数 = tanh(共享实体数 × 0.5) ＋ 语义关系最大权重 ＋ 因果关系最大权重
```

最后的三路评分合并仍在 Python，图关系查询本身已经在 PG。图结果还涉及应用中的标签过滤与截断顺序，不能仅看 SQL 就宣称全部过滤已在索引内部完成。各图任务完成后，应用才进入四路融合。

### 2.6 第五步：合并候选、决定顺序，再限制返回的文本长度——0 次业务 SQL

本节描述应用计算及模型调用，不新增本请求的业务 SQL。PG 当前在召回时已返回正文，候选裁剪后的 `hydrate_results` 对 PG store 是空操作，不能再算一次补读正文 SQL。

#### 2.6.1 RRF 先合并重复候选，再限制排序预算

四路交给 RRF 的候选分别为向量 642、关键词 502、图 622、时序 149，合计 1,915 条记录。应用按记忆 ID 合并，并用各路名次计算 RRF：

```text
RRF 分数 = 该记忆在各命中路中 1 / (60＋名次) 的总和
```

同一记忆跨路出现时只保留一个候选，但保留各路排名贡献。由此得到 1,032 条不同记忆；再按融合排名保留 300 条，剩余 732 条不进入后续排序处理。

#### 2.6.2 两种排序配置：RRF 主样本与 MaaS 对照

| 步骤 | 请求 21：RRF 主样本 | 请求 23：独立 MaaS 对照 |
|---|---|---|
| 合并、裁剪后 | 300 条候选 | 300 条候选 |
| 是否调用神经 reranker | 否，RRF passthrough | 是，`bge-reranker-v2-m3` |
| 基础相关性信号 | 由 RRF 名次建立基础分 | 模型对 300 组 query/text 返回 300 个评分 |
| 之后做什么 | 新近度、时间、证据等加权，再排序 | 相同类别的后续加权，再排序 |
| 应用选出正文总长度不超过 4,000 Token 的记忆；这一步不调用模型 | **38 条，3,992 Token** | **35 条，3,999 Token** |
| 整个 HTTP 请求耗时 | 1.585 秒 | 10.294 秒，其中模型调用及等待约 7.78 秒 |

本次 MaaS 对照的完整数字路径是：

```text
1,915 条多路候选记录
    → RRF 合并为 1,032 条不同记忆
    → 裁剪为 300 条模型候选
    → 模型返回 300 个评分，应用加权并重新排序
    → 应用按顺序选择返回内容：正文总长度上限 4,000 Token，本次选出 35 条
    → 补全并返回
```

**35 条主要由最终内容预算决定，不代表模型只认为 35 条相关。** 每条记忆长度不同，排序后优先装入的内容也不同，所以同样预算能容纳不同条数。两次请求的向量和候选细节可能变化，38 与 35 不能直接作为质量高低的依据。

RRF 配置仍可能经过名称为 `CrossEncoderReranker` 的包装类，trace 也可能写着 cross-encoder；不能只据这个阶段名认定调用了神经模型。具体评分与 provider 关系见第五章。

#### 2.6.3 排序与返回长度控制的执行边界

**先决定哪些记忆排在前面，再决定这次能返回多少内容。**

- **决定顺序：** RRF 路径不用重排模型，按融合排名和时间、证据等规则排序；MaaS 路径先调用模型评分，再结合这些规则排序。
- **控制长度：** 应用计算候选记忆正文的 Token 数，按排名优先选择能放进长度上限的内容。本次上限是 4,000 Token，所以不会把所有 300 条候选的正文都返回。**这一步只是应用程序选择内容，不调用 reranker 模型，也不新发业务 SQL。**

Token 是文本长度的计量单位，不等于汉字数，因此 4,000 Token 不能写成“4,000 字”。这里统计的是返回记忆的正文长度，不是包含全部实体、元数据和 trace 的 HTTP 响应总长度。

**返回集合由排序结果和正文 Token 预算共同确定。** 两条排序路径分别返回 38 条和 35 条记忆，均为实际筛选结果，不是预设返回条数。

### 2.7 第六步：补全最终结果——3 次 SQL

以主样本请求 21 为例，应用按顺序和正文总长度上限选定了 38 条记忆，随后只为这些结果补充关联信息。

#### 2.7.1 SQL-043：补全实体名称，执行 1 次（R17）

查询直接事实的实体；对于没有直接实体关联的 Observation，可从来源事实推导实体。`$1` 为要补全的结果 ID 数组。

```sql
(SELECT ue.unit_id, e.id AS entity_id, e.canonical_name FROM ctxdb_ws_agent_memory.unit_entities ue JOIN
    ctxdb_ws_agent_memory.entities e ON e.id = ue.entity_id WHERE ue.unit_id = ANY($1::uuid[])) UNION
    (SELECT obs.id AS unit_id, e.id AS entity_id, e.canonical_name FROM ctxdb_ws_agent_memory.memory_units
    obs CROSS JOIN LATERAL unnest(obs.source_memory_ids) AS src_id JOIN ctxdb_ws_agent_memory.unit_entities
    src_ue ON src_ue.unit_id = src_id JOIN ctxdb_ws_agent_memory.entities e ON e.id = src_ue.entity_id WHERE
    obs.id = ANY($1::uuid[]) AND obs.fact_type = 'observation' AND obs.source_memory_ids IS NOT NULL AND NOT
    EXISTS (SELECT 1 FROM ctxdb_ws_agent_memory.unit_entities d WHERE d.unit_id = obs.id))
```

本次返回 **218 行事实—实体关联**，不是新增 218 条记忆。应用将关联整理后附加到返回结果中。

#### 2.7.2 SQL-044：读取文档与附件引用，执行 1 次（R18）

`$1=agent_memory`，`$2` 为最终 38 条记忆 ID。SQL 只返回 `id、document_id、attachment_ids`，**不在这里补读正文**。

```sql
SELECT id::text AS id, document_id, attachment_ids FROM ctxdb_ws_agent_memory.memory_units WHERE bank_id =
    $1 AND id = ANY($2::uuid[])
```

本次返回 38 行引用信息。

#### 2.7.3 SQL-045：检查当前 Bank 是否存在附件，执行 1 次（R19）

这是通用返回组装路径的一部分，`$1=agent_memory`。

```sql
SELECT 1 WHERE EXISTS (SELECT 1 FROM ctxdb_ws_agent_memory.attachments WHERE bank_id = $1)
```

本次返回 0 行，表示这次检查没有发现附件，不表示查询没有执行。组装完成后，主样本仍返回 38 条记忆。

### 2.8 技术复核：19 次调用明细与统计口径

#### 2.8.1 按应用发送顺序逐条定位

下表只对应 **RRF 请求 21**。qid 对应发送记录，PID 是 PG 后端连接；每行均匹配到 1 次 PG execute。相对起止时间是从 HTTP 请求开始算的驱动调用区间，含等待、结果读取和调度；PG 执行耗时另列，二者不能混为一谈。

| 调用 / qid | 本次步骤 | SQL | 相对起止时间 s | PG PID | 应用侧调用 ms | PG execute ms | SQL 返回行/项数 |
|---|---|---|---|---:|---:|---:|---:|
| R01 / 184 | 读取 Bank 身份与目标 | [SQL-036](../SQL执行记录.md#sql-036) | 0.020～0.023 | 49673 | 3.510 | 0.078 | 1 |
| R02 / 186 | 读取 Bank 配置 | [SQL-037](../SQL执行记录.md#sql-037) | 0.044～0.047 | 49673 | 3.657 | 0.110 | 1 |
| R03 / 188 | 合并向量与关键词召回 | [SQL-038](../SQL执行记录.md#sql-038) | 0.435～0.974 | 49673 | 539.147 | 212.779 | 1144 |
| R04 / 189 | 查找时间窗内的入口事实 | [SQL-039](../SQL执行记录.md#sql-039) | 0.980～1.005 | 49673 | 25.473 | 18.875 | 162 |
| R05 / 190 | observation 第 1 批 | [SQL-040](../SQL执行记录.md#sql-040) | 1.006～1.011 | 49673 | 4.297 | 0.148 | 0 |
| R06 / 191 | experience 第 1 批 | [SQL-040](../SQL执行记录.md#sql-040) | 1.011～1.020 | 49673 | 9.001 | 5.272 | 93 |
| R07 / 192 | experience 第 2 批 | [SQL-040](../SQL执行记录.md#sql-040) | 1.021～1.037 | 49673 | 16.800 | 12.395 | 184 |
| R08 / 193 | experience 第 3 批 | [SQL-040](../SQL执行记录.md#sql-040) | 1.038～1.048 | 49673 | 9.998 | 5.498 | 101 |
| R09 / 194 | world 第 1 批 | [SQL-040](../SQL执行记录.md#sql-040) | 1.049～1.059 | 49673 | 10.512 | 5.347 | 100 |
| R10 / 195 | world 第 2 批 | [SQL-040](../SQL执行记录.md#sql-040) | 1.060～1.078 | 49673 | 17.743 | 11.839 | 200 |
| R11 / 196 | world 第 3 批 | [SQL-040](../SQL执行记录.md#sql-040) | 1.079～1.096 | 49673 | 17.008 | 11.936 | 170 |
| R12 / 197 | world 第 4 批 | [SQL-040](../SQL执行记录.md#sql-040) | 1.097～1.109 | 49673 | 12.059 | 7.510 | 181 |
| R13 / 198 | world 第 5 批 | [SQL-040](../SQL执行记录.md#sql-040) | 1.110～1.120 | 49673 | 10.158 | 5.072 | 110 |
| R14 / 200 | Observation 图扩展 | [SQL-041](../SQL执行记录.md#sql-041) | 1.130～1.207 | 49673 | 76.827 | 20.810 | 300 |
| R15 / 203 | world 图扩展 | [SQL-042](../SQL执行记录.md#sql-042) | 1.217～1.267 | 49673 | 50.016 | 32.524 | 345 |
| R16 / 205 | experience 图扩展 | [SQL-042](../SQL执行记录.md#sql-042) | 1.227～1.346 | 49742 | 119.436 | 6.859 | 34 |
| R17 / 207 | 补全实体名称 | [SQL-043](../SQL执行记录.md#sql-043) | 1.460～1.469 | 49742 | 9.054 | 2.787 | 218 |
| R18 / 209 | 读取附件引用 | [SQL-044](../SQL执行记录.md#sql-044) | 1.493～1.497 | 49742 | 3.387 | 0.164 | 38 |
| R19 / 210 | 检查 Bank 是否有附件 | [SQL-045](../SQL执行记录.md#sql-045) | 1.497～1.501 | 49742 | 4.031 | 0.031 | 0 |

图阶段的证据是：Observation 调用区间为 1.130～1.207 秒；world 为 1.217～1.267 秒；experience 为 1.227～1.346 秒。后两条使用不同 PID，驱动调用区间有重叠，但这不能证明整个区间都在同时消耗 PG CPU。

#### 2.8.2 SQL 次数、返回行数与候选数量的统计口径

- **SQL 次数：** 本次是 19 次已采集业务 SQL，不是全实例日志条数。parse/bind 不重复算为业务执行，其他请求和后台轮询也不混入。
- **SQL 返回行数：** 向量＋关键词 1,144 行，时间入口 162 行，时序扩展多批返回的目标可能重复，图查询共 679 行。这些是阶段的原始返回量。
- **各路候选与最终结果：** 上述结果经过各路应用处理后才形成 1,915 条融合候选，再变成 1,032、300 和最终 38/35。不能将所有 SQL 返回行数直接相加，作为唯一记忆数。

19 次不是固定常数。时间路径是否启用、事实类型、扩展批次、种子是否复用、配置缓存及实体/来源/片段等返回选项，都会影响调用次数；模型调用数也不能直接算成 PG SQL 次数。

证据：[主样本接口响应与 trace](../evidence/21-dual-rrf-recall.json)、[MaaS 对照响应与 trace](../evidence/23-dual-maas-recall.json)、[19 次调用顺序](../evidence/recall-21-sequence.json)、[应用发送与 PG 执行对照](../双向审计对照.md#21-dual-rrf-recall)、[模型调用记录](../evidence/sender-siliconflow.jsonl)。本章 SQL 可与 [SQL 全文目录](../SQL执行记录.md)逐项复核。

### 2.9 基于执行耗时的优化优先级

下列判断只针对这次带 trace 和日志采集的单次样本，不是延迟分位数，也不等于已经实现的收益。

| 优先分析的对象 | 时间证据 | 可研究的改造 | 不能据此推导什么 |
|---|---|---|---|
| **向量＋关键词 SQL-038** | PG execute 212.779 ms，约占本样本 PG 执行合计的 59.1%；应用侧 539.147 ms，返回 1,144 行 | 按六个分支分析扫描/排序成本；候选只返回必要字段；融合裁剪后再取正文；排查接收、解码和调度 | 不能把 212.779 ms 全算给向量或全文；也不能把约 326 ms 差额直接当作网络耗时 |
| **9 批时序扩展 SQL-040** | PG execute 合计 65.017 ms，应用调用合计 107.575 ms | 把多批循环与状态更新留在库内；复用节点读取与邻接访问，减少应用往返 | 9 批变成一次前台调用，不意味着只做一批计算；也不是提速 9 倍 |
| **图 SQL-041/042** | PG execute 合计 60.193 ms；应用调用合计 246.279 ms，第一条发送到最后一条完成约 216 ms | 优化来源反查、宽行读取和图评分合并；区分执行、结果解码、调度与等待 | 不能将 246.279 ms 全部视为图算法或可节省的时长；三个调用存在重叠 |
| **阶段串行等待** | 时间入口到最后一个扩展批次完成约 140 ms，此后才启动图任务 | 时间路径可与向量/关键词重叠；图在语义起点确定后启动，不必等待时间路径结束 | 约 140 ms 是本样本可研究的重叠窗口，不是保证节省量；资源竞争可能抵消收益 |
| **2 次准备＋3 次补全** | PG execute 合计仅 3.170 ms | 随统一接口合并配置/关联访问，主要减少调用组织与往返 | 本次不应把这部分包装成主要执行性能瓶颈 |

应用 trace 给出的主样本生成向量约 **369 ms**，检索阶段约 **923 ms**；检索阶段还包含查询编排、连接获取和结果处理，并非纯 PG 执行。一次 recall 的优化，应将数据库执行成本、应用等待和整个请求的关键路径分别观察。

另一条 MaaS 请求 23 中，检索阶段约 **493 ms**，模型重排阶段约 **7,782 ms**。因此数据库检索更快，并不会自动消除模型等待。对于启用模型的路径，还要评估候选规模、模型用量与限流；同时保持检索质量，而非只追求少返回候选。

**本次建议的顺序是：先定位最重的组合查询及结果搬运，再验证图/时间的库内状态共享与并行；统一接口作为这些改造的载体。** 是否值得继续投入，应由固定输入下的质量、实际扫描/回表量、传输字节、多请求吞吐和 p95/p99 决定。

---

<a id="chapter7"></a>

## 3. PostgreSQL 检索与模型执行增强方案

**目标执行流程与优化位置（拟建设）**

```text
                          Hindsight / Agent
                                  |
                                  v
                MemoryRecall(问题, 向量, 条件, 预算)
                                  |
                                  v
                           PG 融合执行计划
                [重点一：查询内并行，减少客户端往返]
                                  |
          +-----------------------+-----------------------+
          |                       |                       |
          v                       v                       v
      向量检索                全文检索                时序检索
          |                       |                       |
  保留候选 + 图扩展       分数上界提前剪枝          时间关系扩展
   [依赖向量起点]      [重点二：少做无效计算]        [库内迭代]
          |                       |                       |
          +-----------------------+-----------------------+
                                  |
                                  v
                 按 ID 去重 + RRF 融合 + Top-K(300)
                                  |
                                  v
                        仅为入选候选读取正文
                  [重点三：延迟物化，减少数据搬运]
                                  |
                                  v
                批量模型重排 <--> 本地 / 远程模型服务
                                  |
                                  v
                加权排序 + Token 预算筛选 + 信息补全
                                  |
                                  v
                           返回记忆及来源
```

| 优化重点 | 执行机制 | 目标收益 |
|---|---|---|
| **1. 并行调度与库内迭代** | 向量、全文、时序检索在条件允许时并行；图扩展等待语义起点后启动。扩展进度和预算保留在库内 | 缩短串行等待，减少客户端逐批交互 |
| **2. Top-K 提前剪枝** | 在全文访问阶段，利用可靠分数上界与当前入选阈值，跳过不可能进入前 K 名的记录或索引块 | 减少评分计算、倒排访问和记录读取 |
| **3. 投影列延迟物化** | 融合与 Top-K 阶段仅传递 ID、分数及必要属性，候选入选后再读取正文 | 减少宽字段搬运、物化与重复读取 |

图中展示模型重排策略；RRF 策略不调用模型，直接进入结果组装。提前剪枝作用于具备可靠上界的访问路径，不表示可以直接关闭整条检索分支。MemoryRecall 承担业务适配，PG 底层执行机制保持通用。

### 3.1 能力定义、研发重点与收益

**建议建设一个 PG 侧的 `MemoryRecall` 入口，让 Hindsight 一次提交检索要求，由 PG 提供记忆检索融合执行和批量模型重排两项能力，组织找记忆、排序筛选和结果返回。首期争取的收益是接入简单、检索和模型执行更高效、资源与数据搬运更省。排序质量取决于模型、候选与评分策略，不能归因于执行位置。**

#### 3.1.1 统一适配入口：MemoryRecall

这是 **Hindsight 调 PG 的入口**，属于拟建设能力，尚未实现。它接收问题与查询向量、Bank/标签条件、时间路径参数、候选与返回 Token 预算、排序策略与模型配置，返回筛选后的记忆及其来源。

```text
现在：Hindsight 分步调用 PG → 取回候选 → 应用融合、筛选和补全
目标：Hindsight 调一次 MemoryRecall → PG 组织整次检索 → 返回选中记忆
```

**收益：** 应用少编排、少往返，并能统一查看各阶段成本。本次样本保留 2 次 Bank/配置准备查询，把 14 次检索和 3 次补全收进一次调用，前台目标为 **19→3**。这只是调用目标，内部扫描和耗时是否下降，要靠下面的执行研发证明。

#### 3.1.2 融合检索执行与批量模型重排两项能力

| 能力 | PG 具体做什么 | 预期收益 |
|---|---|---|
| **能力一：记忆检索融合执行** | 组织向量、关键词、图、时间四路检索及关系扩展；保留各路贡献，按 ID 合并、RRF 排序并裁剪候选；随后按返回长度预算选择、补全结果 | **主要解决性能与成本。** 少传落选正文、争取少重复读数据、减少串行等待；以同等检索质量为基线 |
| **能力二：批量模型重排执行** | 将模型评分纳入查询执行计划，统一组织输入取数、推理批次、预算、取消、配额与失败处理，再把模型分数交给结果排序 | **主要收益是执行效率、资源控制和稳定性。** 减少应用编排、重复推理与无效搬运，争取更高吞吐和更稳定延迟；同一模型、同一输入迁入 PG 不产生准确率增益 |

**两项能力均列入数据库建设与交付范围。** 每次查询先完成四路检索与 RRF 融合裁剪，再由执行策略决定直接采用融合排序，还是继续调用模型重排；全过程由同一个 MemoryRecall 入口组织。

```text
MemoryRecall
    → 四路检索与关系扩展 → 融合、裁剪候选
    → 批量模型重排〔由查询策略调度〕
    → 按正文 Token 预算选择、补全 → 返回
```

普通加权、Token 计数和结果补全属于结果处理，优先复用现有逻辑，不各自立一个内核项目。启用同一模型后，把调用位置迁到 PG 本身不代表质量提高或模型变快。

#### 3.1.3 三项研发重点：延迟物化、查询内并行与库内迭代、Top-K 动态剪枝

按照数据库执行技术，三项分别对应**数据物化时机、执行调度、索引访问剪枝**。目标是在既定质量要求下，减少数据搬运、客户端交互和无效评分；模型执行的调度、预算与评分复用见第 3.3.4 节。

| 研发方向与通用术语 | 本次 SQL 依据 | 执行机制 | 预期收益 |
|---|---|---|---|
| **一、过滤与 Top-K 裁剪前置，投影列延迟物化（Late Materialization）** | SQL-038、040、041/042 较早返回正文等宽字段。四路交给融合的 1,915 条记录按 ID 合并为 1,032 条，再保留 300 个候选 | 沿用既定过滤与限流语义，前段仅传递 ID、分数及计算必需属性；完成候选融合与 Top-K 裁剪后，再按 ID 批量读取正文等投影列，并复用已读取的数据 | 减少宽字段物化、结果传输、复制与重复回表；存储 I/O 收益需结合实际访问与布局验证 |
| **二、依赖感知的查询内并行与库内迭代（Intra-query Parallelism / Iterative Execution）** | SQL-040 的时间扩展由应用推进 9 批，SQL-041/042 有 3 次图查询；现场尚有串行阶段和语义起点依赖 | 按检索依赖组织执行：向量、全文、时序在资源与语义允许时并行；图扩展等待向量提供起点后启动。扩展节点内部保留进度、各路传播状态和预算，连续推进后续批次 | 并行调度缩短关键路径；库内迭代减少客户端逐批往返和状态传递。两项收益分别测量 |
| **三、基于分数上界的 Top-K 动态剪枝（Score-bound Pruning）** | SQL-038 的关键词分支执行 `@@` 匹配、`ts_rank_cd` 评分及 `ORDER BY ... LIMIT`；LIMIT 本身不保证跳过无效评分 | 以当前可见候选的第 K 名分数作为竞争阈值；访问方法提供可靠分数上界，跳过上界低于阈值的记录或索引块。可借鉴 WAND / Block-Max WAND，并结合过滤条件进行代价选择 | 减少评分次数、倒排表遍历及记录读取；只有上界可靠且评分、过滤与排序语义一致时，才能作为保持 Top-K 结果的剪枝优化 |

**延迟物化的执行边界：在过滤、候选融合与 Top-K 裁剪后，读取入选记录的投影列。** 过滤下推减少参与后续运算的行，列裁剪/投影下推减少不需要的列；延迟物化则把“最终需要、当前阶段还不需要”的列推迟读取。正文必须在模型评分之前取出；筛选、评分或图/时间计算必需的列不能一并延后。仅修改 SELECT 输出列，也不自动消除 PG 的 heap 访问。可参考业界 Top-N 延迟物化设计，但不能直接套用其列存 I/O 收益。[ClickHouse Lazy Materialization](https://clickhouse.com/blog/clickhouse-gets-lazier-and-faster-introducing-lazy-materialization)

**“延迟物化”的术语出处与本报告用法：** ICDE 2007 的 *Materialization Strategies in a Column-Oriented DBMS* 在第 1 节使用 `late materialization`，第 3.1 节系统讨论其优势：先处理列值/位置等中间表示，延后构造行元组。这是经典研究依据，不据此宣称它首次提出该术语。[作者公开论文，§1、§3.1](https://www.cs.umd.edu/~abadi/papers/abadiicde2007.pdf)

中文产品文档也直接使用该名称：Apache Doris 3.x《TOPN 查询优化》将“先读排序列、确定行号后再读取入选行的其他列”称为延迟物化；ClickHouse 的相关实现使用 `lazy materialization` 名称。它们说明业界确有这一类优化，但不同系统的物理实现不能直接等同。[Doris 中文官方文档](https://doris.apache.org/zh-CN/docs/3.x/query-acceleration/optimization-technology-principle/topn-optimization/)

在本 PG 方案中，具体指**候选融合/Top-K 裁剪后，再按 ID 读取正文等后续阶段所需的投影列**。这是对该思想的借鉴，不表示 PG 已有完整的列存式延迟物化执行。也不要与 PG 的 `Materialize` 节点混淆：后者用于保存子计划结果供重复读取。[PG Materialize 节点说明](https://www.postgresql.org/docs/16/using-explain.html)

**查询内并行与库内迭代分别优化关键路径和客户端交互：**

| 机制 | 本场景的执行关系 | 技术边界 |
|---|---|---|
| **查询内并行调度** | 时间路径可提前启动；图扩展取得语义起点后，可与时间路径重叠。向量与全文分支也纳入并行计划评估 | 图不能在缺少起点时独立执行；不是四路无依赖同时启动。现场 SQL-038 的六分支回放为普通 Append，不能据此称已实现分支并行 |
| **库内迭代执行** | 对有前后依赖的扩展批次，在数据库内更新进度并继续执行，避免每批返回应用再发起下一批 SQL | 有依赖的批次仍顺序推进；9 批不等于 9 个可并行任务。单个函数入口也不会自动提供共享状态与并行协作 |

可以复用 PG 的部分并行与扩展机制；整次检索的依赖调度、共享状态和资源预算仍需设计。[PG Parallel Plans](https://www.postgresql.org/docs/16/parallel-plans.html#PARALLEL-APPEND)

**Top-K 动态剪枝的执行边界：依据可靠分数上界，跳过不可能进入前 K 名的记录或索引块。** WAND/Block-Max WAND 跳过的是不具竞争力的记录或索引块；若要裁掉整条 UNION 分支、图路或时间路，还必须额外证明不会影响候选与 RRF 排名贡献。没有证明时，直接关闭分支属于有损策略，不能与排名剪枝混为一谈。现场 GIN＋`ts_rank_cd` 尚未证明具备这种上界及剪枝路径。[Block-Max WAND 原理](https://www.elastic.co/blog/faster-retrieval-of-top-hits-in-elasticsearch-with-block-max-wand)

三项的研发范围与验收在第 3.3.1～3.3.3 节展开：现有过滤、JOIN、RRF 与索引先作为基线；以共享执行状态、依赖调度及访问方法协作为重点，先验证 SQL/扩展原型，再按实际限制确定 PG 核心改动。上述候选数不是全部 SQL 原始行数之和；收益尚未测出，不能直接按 1,915→300 换算 I/O 或加速比。

### 3.2 行业实现与接口对标

#### 3.2.1 产品能力与执行边界对比

统一入口位于 **Hindsight→数据引擎** 之间。Hindsight 已提供 Recall HTTP 接口，本方案重点减少其与 PG 之间的逐步查询交互。

| 产品与真实入口 | 一次业务请求可由系统组织的流程 | 可借鉴的能力与边界 |
|---|---|---|
| **Redis `FT.HYBRID`** | 文本＋向量 → RRF → 前 K 条 | 两路融合入口已产品化；该命令不包含神经模型重排。[命令](https://redis.io/docs/latest/commands/ft.hybrid/) |
| **Elasticsearch `_search`** | 关键词全文（standard.query.match）＋稠密向量（knn） → RRF → 模型重排 → 返回 | 本章示例是两路；最直接的完整搜索流程参考，8.16 已有明确发布依据。[发布说明](https://www.elastic.co/blog/whats-new-elasticsearch-platform-8-16-0/) |
| **OpenSearch `_search`＋pipeline** | 检索 → RRF → 取候选正文 → 模型处理 → 截断 | 流程提前配置，每次搜索只发一次；不同阶段仍有内部工作。[RRF](https://docs.opensearch.org/2.19/search-plugins/search-pipelines/score-ranker-processor/)、[模型阶段](https://docs.opensearch.org/2.19/search-plugins/search-pipelines/rerank-processor/) |
| **Vespa query＋rank-profile** | 检索 → 分阶段排序/模型评分 → 返回 | 将便宜与昂贵计算分阶段安排；公式可配置，不限于 RRF 先于模型。[分阶段排序](https://docs.vespa.ai/en/ranking/phased-ranking.html) |
| **PostgresML `pgml.rank`** | 已有候选正文 → PG 内模型评分、重排 | 本例只证明 PG 可以运行 Cross-Encoder，不负责寻找候选与四路融合。[实现](https://github.com/postgresml/postgresml/blob/v2.9.2/pgml-extension/src/bindings/transformers/transformers.py) |
| **Qdrant Query API** | 稠密向量（dense）＋稀疏向量（sparse） 两个 prefetch → RRF → 前 K 条 | 本文示例是两路向量检索；稀疏编码器未指定，不能认定为 BM25。条数 limit 不是 Token 预算。[版本固定 API](https://api.qdrant.tech/v-1-10-x/api-reference/search/query-points) |
| **Memlake recall（内部 gRPC）** | 四路记忆检索 → 应用下发的融合、模型重排、权重与 Token 预算策略 → 返回 | 当前官方描述最接近完整 MemoryRecall；模型位置、预算细节和 RPC 参数尚未独立核实。[架构](https://docs.hindsight.vectorize.io/enterprise/memlake/architecture/) |

**这里的“路”是同一次查询中生成候选的一种检索方式，不是 SQL 次数或网络连接数。** 本章 ES 示例的两个子检索器分别按正文中的词和向量相似度查找；Qdrant 示例的两个子请求分别使用稠密向量与稀疏向量。稀疏向量由特征编号及权重构成，编码方式决定它表达什么，不能仅凭 sparse 名称认定为 BM25。两例均未包含 Hindsight 的图和时间路径，不能统称为相同的四路检索。

三个核验结果会直接影响设计：

- **一次请求不等于一个物理算子。** ES/OpenSearch 的协调层可以组织多个阶段，模型还可运行在 ML 节点或外部服务；一次搜索也不保证只发一次模型请求。
- **少返回字段不等于少读磁盘。** Redis v8.4.0 显式 LOAD 被移到融合前的两路分支；Vespa 也说明缩减 summary 字段可能只减少网络量。延迟物化必须验证真实加载位置与存储访问。[Redis 源码](https://github.com/RediSearch/RediSearch/blob/v8.4.0/src/hybrid/parse_hybrid.c)、[Vespa 字段获取](https://docs.vespa.ai/en/querying/document-summaries.html)
- **前 K 条不等于 4,000 Token。** Memlake 当前架构声明支持预算策略，但完整 tokenizer/超限合同未公开核实到基准日历史版本；其公开 recall 性能明确排除了 Cross-Encoder，不能直接推算本方案的模型或 PG 加速比。[基准口径](https://hindsight.vectorize.io/blog/2026/10/13/memlake#performance)

<a id="example-es"></a>

#### 3.2.2 Elasticsearch 混合检索与模型重排接口

下面按 Elasticsearch 8.16 已支持的接口改写。假设 `memory_idx` 已有正文和向量索引，`memory_reranker` 是已配置的模型推理端点。三维向量只说明参数位置，实际必须使用与索引相同模型生成的向量；索引、模型名称均为本例自取。**这是官方接口示例，不是本轮实际集群运行结果。**

```http
POST /memory_idx/_search
{
  "size": 10,
  "retriever": {
    "text_similarity_reranker": {
      "retriever": {
        "rrf": {
          "retrievers": [
            {
              "standard": {
                "query": {"match": {"text": "PostgreSQL memory"}}
              }
            },
            {
              "knn": {
                "field": "embedding",
                "query_vector": [0.1, 0.2, 0.3],
                "k": 100,
                "num_candidates": 200
              }
            }
          ],
          "rank_window_size": 100,
          "rank_constant": 60
        }
      },
      "field": "text",
      "inference_id": "memory_reranker",
      "inference_text": "Why does Atlas use PostgreSQL for agent memory?",
      "rank_window_size": 100
    }
  }
}
```

| 参数 | 含义 |
|---|---|
| `standard` 与 `knn` | 关键词全文（standard.query.match）和稠密向量（knn）两路检索；向量由应用准备 |
| `k=100`、`num_candidates=200` | 向量结果规模、每分片 ANN 候选参数；不是两个模型批次 |
| 内层 RRF 的窗口 100 | 各子路参与融合的排名窗口；常数 60 控制名次分值差异 |
| 外层模型的窗口 100 | 从融合结果取最多 100 条给模型，不是两个窗口相乘 |
| `field`、`inference_text`、`inference_id` | 给模型的正文字段、用户问题、已配置的推理端点 |
| `size=10` | 最终返回最多 10 条；没有指定 Token 预算 |

**应用交一份完整请求，ES 组织“关键词全文＋稠密向量找候选→RRF→最多 100 条模型评分→最多返回 10 条”。** 可借鉴的是完整要求一次表达、候选窗口和模型阶段集成；不能由此推断 Hindsight 的图/时间/Observation 来源语义已经被覆盖。[8.16 参数合同](https://www.elastic.co/guide/en/elasticsearch/reference/8.16/retriever.html)

其他产品的可读调用、参数与前置条件已合并在本文附录 A。理解本章不需要先读完全部厂商语法。

### 3.3 SQL 成本依据与研发方向

请求 21 使用 RRF，HTTP 约 **1,585 ms**，trace 检索阶段约 **923 ms**；19 次已采集业务 SQL 的 PG execute 合计 **360.034 ms**，应用侧调用耗时合计 **942.112 ms**。后两项包含重叠调用，均不是请求关键路径；差额不能全部归因网络。下表来自同一请求，逐条证据见第 2.8 节。

| 现场工作 | SQL 次数 | PG execute 合计 | 应用调用合计 | 对应问题 |
|---|---:|---:|---:|---|
| 向量＋关键词 SQL-038 | 1 | 212.779 ms | 539.147 ms | 六分支扫描/排序及 1,144 行宽候选输出 |
| 时间入口 SQL-039 | 1 | 18.875 ms | 25.473 ms | 独立时间路径被串行安排 |
| 时间扩展 SQL-040 | 9 批 | 65.017 ms | 107.575 ms | 状态与下一批节点由应用推进 |
| 图扩展 SQL-041/042 | 3 | 60.193 ms | 246.279 ms | 来源映射、查边、聚合与正文读取；调用存在重叠 |
| 准备与补全 | 5 | 3.170 ms | 23.639 ms | 可以集成，但不是主要 SQL 执行瓶颈 |

#### 3.3.1 延迟物化与候选共享：融合裁剪后读取投影列

SQL-038 已经用一条 `UNION ALL` 组合六个检索分支，并非还缺少“一条 SQL 查多路”。下面是其中 world 关键词分支的结构节选，省略了部分输出字段；完整原文在第 2.3 节：

```sql
SELECT id, text, context, metadata,
       ts_rank_cd(search_vector, to_tsquery('english', $4)) AS bm25_score
FROM ctxdb_ws_agent_memory.memory_units
WHERE bank_id = $2
  AND fact_type = 'world'
  AND search_vector @@ to_tsquery('english', $4)
ORDER BY ts_rank_cd(search_vector, to_tsquery('english', $4)) DESC
LIMIT $3;
```

图和时间查询也较早返回正文。应用最后才把各路 **1,915 条记录按 ID 合并为 1,032 条，再保留 300 条**。这些是交给 RRF 的记录数，不是所有 SQL 原始行数之和。

**先复用：** 各路 SQL、RRF 求和/去重、按 ID 批量读取都可用现有能力做基线。候选阶段保留 ID、分数、来源及计算必需的时间/证据属性，融合裁剪后再读取入选正文；模型启用时先为模型候选取正文，最终结果确定后再补实体、附件等字段。

**值得研发：** 让融合执行器在同次请求中共享候选 ID 与读取状态，减少不同路径重复回表、复制和正文物化，并把这些成本纳入优化器选择。仅把输出列改少是 SQL 改造；让多个子计划复用同一候选/取数状态，才是执行器层面的工作。初版先收齐既定窗口再融合；跨路提前停止必须有正确的排名上界或明确的质量损失约定，不能某一路凑满 300 条就停止其他路。

**收益验收：** 正文传输字节、重复回表/TOAST 读取、CPU 和检索时间下降，同时候选与排序符合预期。**1,915→300 不代表 I/O 按同比例下降**；ANN 距离与可见性检查仍需执行。

#### 3.3.2 查询内并行与库内迭代：按依赖调度检索，减少客户端交互

SQL-040 的核心片段说明 PG 已会批量查邻居，应用则负责更新“访问过谁、传播分数、还剩多少预算、下一批查谁”：

```sql
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
```

这是第 2.4.3 节 SQL 的片段，不是可独立执行的语句。现场是 9 个批次，不是同一节点走 9 跳。Observation 的 SQL-041 还要经过“起点结论→来源事实→共享实体→关联来源→反查结论”，其中包含：

```sql
WHERE m.source_memory_ids @> ARRAY[cs.source_id]
```

**先复用：** 现有 JOIN、LATERAL、边索引和来源数组索引，先用库内循环/SQL 保持传播与限流顺序。SQL-040 是先按源节点限边，再过滤目标事实；将过滤提前属于语义变化，应单独评测。

**值得研发：** 执行器保留批次、传播和预算状态，支持批量邻接/来源读取；优化器与调度器识别依赖，安排工作和资源。读取缓存可共享，图与时间的排名、已访问和传播状态仍须按各自策略保留。把同一 ID 出现多次简单删掉，可能丢失不同路径的排名贡献。

```text
向量检索 → 语义起点 → 图扩展 ─┐
关键词检索 ───────────────────┼→ 融合
时间入口＋时间/因果扩展 ──────┘
```

时间入口不依赖语义候选；图等待语义起点，不必等时间路径结束。本样本时间入口到最后一批扩展约 **140 ms**，是一段可研究重叠的工作，不是保证节省量。`Parallel Append` 和 CustomScan 可以提供部分基础，但不会自动实现整套调度。[PG 并行计划](https://www.postgresql.org/docs/16/parallel-plans.html#PARALLEL-APPEND)

**收益验收：** 外部往返、内部批次数、真实查边/回表量、单请求关键路径及并发 p95/p99。9 批收进一次调用不等于一次扫描；多 worker 也不等于吞吐必然上升。

#### 3.3.3 Top-K 动态剪枝与代价选择：减少无效评分和索引访问

SQL-038 单次 PG execute 已占本样本合计的 **59.1%**，减少其他 SQL 次数无法替代对它的优化。但六分支同时含向量与关键词，不能把 212.779 ms 全算给全文，也不能据此归因某个索引。

上面的 `@@` 负责找匹配，`ORDER BY ts_rank_cd(...) LIMIT` 负责挑排名。现场不是 BM25；普通 GIN 不直接提供按查询相关度排列的输出，写了 LIMIT 也不保证能只访问前 K 个匹配。[PG 索引与排序](https://www.postgresql.org/docs/16/indexes-ordering.html)

**这里应区分两种剪枝：** 全文检索内部可研究“记录/索引块的分数上界低于当前第 K 名，就跳过评分”的 Top-K 排名剪枝。Lucene 通过最大可能得分与最小竞争得分协作支持这类执行，可借鉴 WAND/Block-Max WAND 的方法和访问接口；不能据此认定现场 `ts_rank_cd` 可直接套用。[Lucene 最大分数与竞争阈值接口](https://lucene.apache.org/core/9_10_0/core/org/apache/lucene/search/TermScorer.html)

若要裁掉 SQL-038 的一个 UNION 分支、停止图/时间路，或提前结束整路检索，还必须证明该路不会再改变候选集合及 RRF 排名贡献；单路原始分数上界也不能直接充当模型相关性分数上界。没有这样的依据时，停止某一路属于有损策略，需要另行质量评测，不能写成已证明的无损优化。

**先复用：** 验证分词/索引一致性和可用全文插件，分析各分支真实计划；现场 pgvector 0.6.0 的升级与过滤填充策略也先做兼容验证。中文子词探针失败提示质量题集应覆盖中文和混合语料，不能只测速度。

**值得研发：** 评估能按相关度上界剪枝的全文 Top-K 访问方法，以及结合过滤选择率、向量候选填充、关系扇出和剩余预算的路径选择。目标是让引擎知道“继续读哪一路还有价值”，而不只是执行应用固定下发的多个 LIMIT。更换 `ts_rank_cd` 为 BM25 会改变排序语义；候选缩减或近似剪枝也必须单独衡量质量。

**收益验收：** 大 Bank 下的实际评分/访问行数、CPU/I/O、候选满额率、Recall@K 和排序质量。只有现有 SQL/插件的成本曲线证明必要，才推进专用访问方法或核心接口改动。当前 2,002 行样本不能证明规模优势；存储/索引布局与查询、维护资源分工放在规模实验后决定。

#### 3.3.4 批量模型重排执行：价值在执行效率，质量由模型与策略决定

**把相同模型、相同候选、相同预处理和排序规则从应用移到 PG，不会自动提高准确率。** 模型可能比 RRF 更善于识别问题与正文的相关性，这是模型/策略变化带来的收益，在应用侧调用同样可以获得。Hindsight 已经在应用侧调用 MaaS；数据库新增的价值应由执行成本与服务能力证明。

本轮 MaaS 请求 23 已将 300 组“问题＋正文”提交模型评分，重排阶段约 **7,782 ms**，检索约 **493 ms**，最终返回 **35 条、3,999 个正文 Token**。这既不是逐条请求模型的低效基线，也不证明模型比 RRF 更准确；35 条是最终长度筛选结果。仅把调用者换成 PG，不能推断 7.8 秒会下降。另一次模型 reflect 因 20,000 TPM 配额失败，说明总用量控制也是实际问题。此处时间不能拼入请求 21 的 19 次 SQL。

**数据库要提供的高级能力，是把模型评分作为可估算、可调度、可复用、可取消的查询执行阶段。** PostgresML 的模型函数、现有推理服务和调用协议先复用；在此之上研发下列执行机制，均尚未实现、尚未测出收益：

| 执行机制 | 结合本场景具体做什么 | 争取的收益与边界 |
|---|---|---|
| **候选与模型输入协同** | SQL-038/040/041/042 先产生轻量候选；融合确定模型输入集合后，按 ID 批量取正文并准备模型输入，避免应用反复接收和组装落选正文 | 减少搬运和重复物化；维持同样 300 个模型输入时，不减少这 300 组模型计算，也不能免除远端正文传输 |
| **模型感知批处理与资源调度** | 按模型版本、输入长度和服务能力组织批次；管理队列、并发和取消。自建推理服务时研究跨查询合批与 GPU 调度；外部 MaaS 按其 API、配额和取消能力执行 | 争取吞吐、资源利用和延迟稳定性；当前 MaaS 已接收一批 300 条，不能把“首次批量化”当收益。同步 SQL 仍可能占用连接/快照，释放等待资源需另行设计 |
| **输入代价与全流程预算管理** | 执行计划记录模型候选数、输入长度、预计开销；同一 reflect 的多次 recall 累计记账，在发送前排队或控制用量 | 减少配额冲击和超时后继续做的无效工作。模型输入预算与最终 4,000 Token 输出预算分开；缩减 300 个候选或截短正文会改变输入，质量必须重评 |
| **有效评分复用** | 对可独立复用的成对评分，按问题、正文版本、模型版本和预处理配置建立缓存，复用前核验 Bank/权限；正文或模型变化后失效 | 降低重复问题的推理量；只在有重复且评分语义允许时有收益，不能把旧分数跨版本或越权复用；本轮尚未证明命中率 |

上述批处理、缓存等也可以由推理服务或应用实现。**ContextBase 的研究价值在于将其与候选计划、索引取数、作用域和用量统一协同，而不是声称这些机制只有数据库能做。** 缓存、协议接入先做组件原型；跨执行节点的资源协作、代价估计与等待机制，才按扩展边界确定执行框架或核心改动。

**分别验收两类结果：** 固定模型和输入，测搬运字节、重复推理量、吞吐、p95/p99、配额失败和等待资源，验证数据库执行收益；改变模型、候选或排序策略时，另测排序与回答质量。当前证据只确认了 MaaS 调用成功和耗时/配额问题，没有证明 PG 已具备这些高级机制，也没有证明准确率提升。

### 3.4 现有能力复用与研发边界

以下是**设计范围，尚未实现**。输入包括问题与向量、Bank/标签作用域、事实类型、时间路径参数、候选和返回 Token 预算、排序策略和模型配置；输出是选中记忆、来源及阶段诊断。模型名称/端点通过配置选择，不增加第二个业务接口。

```text
Hindsight
  │ 2次 Bank/配置准备查询
  │ 1次 MemoryRecall〔目标；尚未实现〕
  ▼
PG：组织四路检索与关系扩展 → 融合裁剪
    → 批量模型重排〔由查询策略调度〕 → 按正文长度预算选择、补全 → 返回
```

本样本保留 2 次准备查询，把 14 次检索和 3 次补全收进一次调用，前台目标 **19→3**。这首先是接口和往返收益；内部执行、读取量和耗时必须另测。融合检索和批量模型重排都是交付能力；权重、Token 计数、实体补全优先复用现有逻辑。

| 层次 | 具体交付 | 何时属于真正数据库研发 |
|---|---|---|
| **优先复用现有 SQL/组件** | JOIN/LATERAL/索引、RRF 求和、ID 去重、批量取正文、权重与结果补全；参考现有模型函数/服务 | 行为与成本基线；不是重复发明一种 RRF |
| **扩展/执行器与优化器重点** | 共享候选和物化状态；关系扩展状态；依赖与资源调度；排名感知访问与路径选择 | 真正改变内部重复工作、访问行数或关键路径。先评估 CustomScan/访问方法等扩展入口 |
| **必要时改 PG 核心** | 扩展无法有效表达的跨执行节点共享执行状态、并行协作或等待恢复机制 | 原型证明确有收益，且扩展边界成为限制后再确定核心范围；不预先把全部工作归入核心 |
| **批量模型重排执行** | 模型与协议优先复用；建设候选/输入协同、批次与资源调度、全流程预算和有效评分复用，明确取消与失败行为 | 两项交付能力之一；先组件/扩展验证，再按调度与等待瓶颈深化执行框架。质量不归因于模型执行位置 |

PG 提供 Custom Scan 扩展的规划与执行入口，但不会因此自动具备以上融合能力。[PG Custom Scan](https://www.postgresql.org/docs/16/custom-scan.html)

必须保持的行为也要同时明确：保持各路排名贡献、来源与过滤/限流顺序，Token 计数兼容现有实现。新的单次执行要明确快照与并发可见性，不能默认与原多个语句时刻完全相同。引擎提供通用候选、关系扩展与预算机制，Hindsight 的事实类型、公式和来源策略仍由配置/SQL 表达。

### 3.5 实施优先级与验收指标

| 顺序 | 交付 | 判断是否值得继续投入 |
|---|---|---|
| **第一步：建立兼容基线** | 一个入口组织原有 SQL；固定候选、排名与 Token 规则；建立中文/关系/时间题集 | 指定样本前台调用目标可核验；内部执行仍单列，不把封装算作扫描优化 |
| **第二步：验证融合执行收益** | 窄候选、按需取正文、库内关系扩展和受控并行；同步分析全文/向量分支 | 同等质量下，正文传输、访问量、CPU/I/O、检索延迟与并发性能有可复现改善 |
| **第三步：有证据再深化** | 对瓶颈建设访问方法、代价模型；按需推进核心共享/并行/任务机制与规模布局 | 十万/百万级、多 Bank 和持续写入下仍有收益；质量、恢复与一致性通过验证 |
| **模型能力交付与评测** | 固定模型/输入测执行收益；模型、候选或排序变化后单独质评；统计多轮 reflect 总用量 | 验证吞吐、延迟、重复推理、预算及失败管理；质量收益归因于模型/策略变化，不归因于入库执行 |

**建议立项的是“PG 记忆检索与模型执行能力”，通过一个 MemoryRecall 入口交付融合检索和批量模型重排；行业方案作为可行性依据，现场 SQL 作为研发取舍依据，实测成本与质量作为验收依据。** 不预先承诺固定加速比或准确率提升百分比。

---

<a id="api-appendix"></a>

## 附录 A. 友商真实接口与参数

本附录给出真实接口的最小使用示例，便于理解调用边界。**Redis、Elasticsearch、OpenSearch、Vespa、PostgresML、Qdrant 示例依据官方接口改写，本轮未在对应集群执行；Hindsight 的请求参数在前轮现场调用中已经使用。Memlake 的私有 gRPC 参数未公开核实，不编造调用。**

为方便阅读，多数例子围绕“Atlas 为什么使用 PostgreSQL 存储 Agent 记忆”，用英文查询展示。索引、数据、模型和认证需要提前准备；示例只计算每次检索的业务调用，不把建索引、部署模型算成每次查询。除 Vespa 官方样例外，`memory_idx`、`memory_reranker` 等名称均是本例自取的部署名称，不是产品内置对象。

向量 `[0.1, 0.2, 0.3]` 是用于说明参数的三维示例，不能代替真实问题的 embedding；实际维度、模型和字段应与建库时一致。候选 100、返回 10 均为示例参数，不构成实测数量或质量建议。各检索索引/集合假设仅包含一个演示 Bank 的数据。

### A.1 接口输入、执行职责与返回内容

| 例子 | 应用交什么 | 引擎做什么 | 应用收到什么 |
|---|---|---|---|
| Redis | 文本条件＋问题向量 | 两路检索、RRF、取前 K 条 | 入选 ID 与分数 |
| Elasticsearch | 文本、稠密向量、融合窗口、模型端点、最终条数 | 关键词全文＋稠密向量→RRF→模型重排 | 最多 10 个结果及字段、分数 |
| OpenSearch | 文本、向量和已配置 pipeline 名 | 检索→RRF→取正文→模型重排→截断 | 最多 10 个结果 |
| Vespa 官方样例 | 问题、检索表达式和 rank-profile | 检索、分阶段模型评分及排名融合 | 最多 10 个结果 |
| PostgresML | 问题＋**已经准备好的候选正文数组** | 模型评分与重排 | 候选数组位置、模型分数等 |
| Qdrant | 稠密/稀疏查询向量与候选限制 | 稠密向量＋稀疏向量→RRF | 最多 10 个 point |
| Hindsight／Memlake | Hindsight 接收问题、预算与 Bank | 使用 Memlake 时，内部把记忆检索策略交给引擎 | 选中的记忆；直接 gRPC 参数未核实 |

### A.2 Redis：一次命令完成两路检索与融合

**前置条件：** Redis 8.4 能力可用，已创建名为 `memory_idx` 的搜索索引，正文可全文检索，`embedding` 为三维 FLOAT32 向量字段。Python 安装了 `redis` 客户端。为展示二进制向量如何传递，用 Python 调用真实 Redis 命令。

```python
import struct
import redis

client = redis.Redis(host="localhost", port=6379)
query_vector = struct.pack("<3f", 0.1, 0.2, 0.3)

result = client.execute_command(
    "FT.HYBRID", "memory_idx",
    "SEARCH", "PostgreSQL memory",
    "VSIM", "@embedding", "$qv",
    "KNN", 2, "K", 100,
    "COMBINE", "RRF", 4, "WINDOW", 100, "CONSTANT", 60,
    "LIMIT", 0, 10,
    "PARAMS", 2, "qv", query_vector,
)
print(result)
```

| 参数 | 人能看懂的含义 |
|---|---|
| `SEARCH "PostgreSQL memory"` | 以这些词做全文检索，默认文本评分为 BM25STD |
| `VSIM @embedding $qv` | 用传入的问题向量搜索相似记忆 |
| `KNN 2 K 100` | 向量路请求 100 个邻近候选；`2` 是后面 `K 100` 的参数项数量 |
| `WINDOW 100` | 设置参与融合的排名窗口；不是 Token 上限 |
| `CONSTANT 60` | RRF 公式的平滑常数，控制不同名次的分值差异 |
| `COMBINE RRF 4` | 使用 RRF；`4` 是 `WINDOW 100 CONSTANT 60` 的参数项数量 |
| `LIMIT 0 10` | 从第 0 条开始，最多返回 10 条 |
| `PARAMS 2 qv ...` | 绑定名为 qv 的二进制参数；`2` 是名称和值两项 |

**实际职责：** 应用调用一次，Redis 做文本与向量检索、融合和条数裁剪，返回 key/ID 与分数。本例未加载正文、未调用 rerank 模型。100 是向量候选/融合窗口参数，10 是返回条数，60 不是候选数。

[官方 FT.HYBRID 语法](https://redis.io/docs/latest/commands/ft.hybrid/)。关于 8.4.0 显式 LOAD 会进入融合前分支的边界，见 [第三章核验结论](#chapter7)。

### A.3 Elasticsearch：检索、融合与模型重排接口

完整请求、参数含义和执行流程见 [第 3.2.2 节](#example-es)。索引和模型需提前配置，单次搜索不等于单次模型 HTTP 调用。

### A.4 OpenSearch：配置一次流程，之后每次只发一次搜索

**前置条件：** 以 2.19 文档为依据；`memory_idx` 的 `text` 可全文检索，`embedding` 为已配置的三维 k-NN 字段；本地 Cross-Encoder 已部署，下面的 `DEPLOYED_MODEL_ID` 必须换成其真实模型 ID。

先创建 pipeline。**这是部署配置动作，不是每次查询都创建。**

```http
PUT /_search/pipeline/memory_recall
{
  "request_processors": [
    {"oversample": {"sample_factor": 10}}
  ],
  "phase_results_processors": [
    {
      "score-ranker-processor": {
        "combination": {"technique": "rrf", "rank_constant": 60}
      }
    }
  ],
  "response_processors": [
    {
      "rerank": {
        "ml_opensearch": {"model_id": "DEPLOYED_MODEL_ID"},
        "context": {"document_fields": ["text"]}
      }
    },
    {"truncate_hits": {}}
  ]
}
```

每次检索只发送下面这一条：

```http
POST /memory_idx/_search?search_pipeline=memory_recall
{
  "size": 10,
  "query": {
    "hybrid": {
      "queries": [
        {"match": {"text": "PostgreSQL memory"}},
        {"knn": {"embedding": {"vector": [0.1, 0.2, 0.3], "k": 100}}}
      ]
    }
  },
  "ext": {
    "rerank": {
      "query_context": {
        "query_text": "Why does Atlas use PostgreSQL for agent memory?"
      }
    }
  }
}
```

| 参数 | 人能看懂的含义 |
|---|---|
| `search_pipeline=memory_recall` | 选择前面已经配置的执行流程 |
| `hybrid.queries` | 定义文本、向量两路检索 |
| `oversample.sample_factor: 10` | 把请求 `size=10` 放大成内部 `size=100`，给后续重排留候选 |
| `score-ranker-processor` | 在 query 与 fetch 之间执行 RRF |
| `document_fields: [text]` | 读取并提供给模型的文档字段 |
| `model_id` | 已部署模型，不是任意 MaaS URL |
| `query_text` | 模型读取的完整问题 |
| `truncate_hits: {}` | 模型重排之后，恢复到原始请求的最多 10 条 |

**引擎执行：** 两路检索 → RRF → fetch 最多 100 个候选文档 → 模型重排 → 截成最多 10 个结果。实际不足 100 条时按现有结果处理；内部候选与处理次数仍受分片、查询配置影响。

本例说明“统一入口”还需要正确配置内部窗口：如果只设置 `size=10`，没有扩大候选，模型就不能自动在 100 条中挑选。配置能力已经由官方组件支持，本组合尚未集群实测。

[RRF](https://docs.opensearch.org/2.19/search-plugins/search-pipelines/score-ranker-processor/)、[本地模型 rerank](https://docs.opensearch.org/2.19/search-plugins/search-pipelines/rerank-processor/)、[oversample](https://docs.opensearch.org/2.19/search-plugins/search-pipelines/oversample-processor/)、[truncate_hits](https://docs.opensearch.org/2.19/search-plugins/search-pipelines/truncate-hits-processor/)。

### A.5 Vespa：用官方样例，看一次查询怎样选择整个模型排序流程

这里使用官方 `msmarco-ranking` 样例实际定义的 schema、embedder 和 rank-profile 名称，避免编造 ONNX 输入绑定。**前置条件：** 按该样例部署应用、模型及数据，查询参数替换语法要求 Vespa 8.299 或以上；使用当前样例时还需满足其 GPU 配置要求。下面是调用格式示例，本轮未部署该样例。

```bash
vespa query \
  'query=Why does Atlas use PostgreSQL for agent memory?' \
  'yql=select * from passage where userQuery() or ({targetHits:100}nearestNeighbor(e5_embedding,q))' \
  'input.query(q)=embed(e5_embedding_model,@query)' \
  'input.query(qt)=embed(colbert_embedding_model,@query)' \
  'input.query(query_token_ids)=embed(tokenizer,@query)' \
  'ranking=e5-colbert-cross-encoder-rrf' \
  'hits=10'
```

| 参数 | 人能看懂的含义 |
|---|---|
| `query` | 用户的问题 |
| `userQuery() or nearestNeighbor(...)` | 用关键词和向量共同寻找候选 |
| `targetHits:100` | 向量检索的目标命中参数；不是全流程最终返回条数 |
| `input.query(q)` | 让已配置的 E5 embedder 生成查询向量 |
| `input.query(qt)` | 为 ColBERT 阶段生成查询的多向量表示 |
| `input.query(query_token_ids)` | 为 Cross-Encoder 准备问题的 token ID |
| `ranking` | 选用整个预定义排序方案，而不是只指定一个模型名称 |
| `hits=10` | 最多返回 10 条 |

**这个官方 profile 的顺序是：** 文本/向量找候选 → 向量相似度初排 → ColBERT 对每节点最多 1,000 个候选评分 → 全局最多 12 个候选执行 Cross-Encoder，并将向量、ColBERT、Cross-Encoder 的三种名次作 RRF 融合 → 返回结果。

**融合与模型评分的先后顺序由具体执行计划决定。** Vespa 该样例在全局模型阶段融合三种评分的排名，不采用固定的“RRF→Cross-Encoder”顺序。profile 的 1,000 和 12 为所核验当前官方源码中的配置值，不作为本方案推荐参数；其基准日历史配置尚未固定。

[官方可部署样例及查询](https://github.com/vespa-engine/sample-apps/tree/master/msmarco-ranking)、[profile 实际定义](https://github.com/vespa-engine/sample-apps/blob/master/msmarco-ranking/schemas/passage.sd)。

### A.6 PostgresML：一个 SQL 调模型，但候选已由调用者准备

**前置条件：** 安装包含 `pgml.rank` 的 PostgresML 扩展及 Python/模型依赖，模型权重可获得。v2.9.2 固定源码能确认这一能力。

```sql
SELECT *
FROM pgml.rank(
    'cross-encoder/ms-marco-MiniLM-L-6-v2',
    'Why does Atlas use PostgreSQL for agent memory?',
    ARRAY[
        'Atlas stores agent memories in PostgreSQL to reuse transactions and SQL.',
        'Alice prefers hiking on weekends.',
        'Atlas uses vector and full-text indexes to retrieve stored facts.'
    ],
    '{"top_k": 2, "return_documents": true}'::jsonb
);
```

| 参数 | 人能看懂的含义 |
|---|---|
| 第一个参数 | 模型名称；不是外部 MaaS 接口地址 |
| 第二个参数 | 要判断相关性的用户问题 |
| `ARRAY[...]` | 已准备的候选正文；本例使用 3 条示例文本 |
| `top_k:2` | 评分排序后返回最多 2 条；不代表只对 2 条输入推理 |
| `return_documents:true` | 同时返回候选正文 |

返回包含 `corpus_id`、`score`、`text`：分别表示候选在输入数组中的位置、模型相关性分数和正文。实际分数由模型运行得到，本文不伪造分数或排序结果。

**职责边界：** PG 扩展完成模型推理；候选检索、四路融合、图/时间扩展、4,000 Token 筛选，都不是这个函数自动完成的。本例的 3 条正文可以由前面的 SQL 查询得到，也可以像这里由应用直接传入。

[固定版本 SQL 定义](https://github.com/postgresml/postgresml/blob/v2.9.2/pgml-extension/sql/pgml--2.8.5--2.9.0.sql)、[Cross-Encoder 调用实现](https://github.com/postgresml/postgresml/blob/v2.9.2/pgml-extension/src/bindings/transformers/transformers.py)。

### A.7 Qdrant：一次 Query API 完成两路候选与 RRF

**前置条件：** 以 1.10 Query API 的基础语法为依据，collection `memory_bank` 已配置名为 `dense` 的三维稠密向量和名为 `sparse` 的稀疏向量，payload 含 `text`。下面的稀疏坐标也是示例；真实查询需要同一编码器生成。

```http
POST /collections/memory_bank/points/query
{
  "prefetch": [
    {
      "query": [0.1, 0.2, 0.3],
      "using": "dense",
      "limit": 100
    },
    {
      "query": {"indices": [7, 23], "values": [0.6, 0.9]},
      "using": "sparse",
      "limit": 100
    }
  ],
  "query": {"fusion": "rrf"},
  "limit": 10,
  "with_payload": ["text"]
}
```

| 参数 | 人能看懂的含义 |
|---|---|
| `prefetch` | 引擎先执行的候选检索子请求 |
| `using` | 查询哪个命名向量索引 |
| 子请求 `limit:100` | 每路最多输出 100 个候选给后续处理 |
| `indices/values` | 稀疏向量的坐标及权重；不能直接当成原始关键词 |
| `fusion:rrf` | 引擎按两路排名融合 |
| 最外层 `limit:10` | 融合后最多返回 10 个 point |
| `with_payload:[text]` | 返回相应正文字段 |

**引擎执行：** 接收两种已生成的查询向量 → 两路各取最多 100 个候选 → RRF → 返回最多 10 个 point 与正文。本例没有发送原始问题给 Cross-Encoder，也没有指定 Token 预算。

[1.10 Query API](https://api.qdrant.tech/v-1-10-x/api-reference/search/query-points)。当前文档还展示了其他、新版本的 RRF 表达方式；此处故意采用已核验早期版本的 `fusion` 语法，避免把新语法当成所有版本都支持。

### A.8 Memlake 与 Hindsight 的接口边界

Memlake 官方说明 Hindsight 通过 gRPC 调用 Query Node，但本轮没有找到可公开核实的完整 protobuf/service 定义。因此不能提供一个声称真实可调用的 `MemlakeRecall(...)` 方法及参数表。

用户可使用的是 Hindsight 的真实 Recall HTTP 接口。下面的请求结构在此前 PG 后端环境中已使用；要走 Memlake，必须是已由服务端配置成 Memlake 后端的企业部署，**不能靠增加一个猜测的请求参数切换后端**。

```bash
curl -X POST \
  "${HINDSIGHT_API_URL}/v1/default/banks/agent_memory/memories/recall" \
  -H "Authorization: Bearer ${HINDSIGHT_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "2026年9月至11月，团队为什么选择 Hindsight 作为 ContextBase 底座，而不是 OpenViking 和 cognee？有哪些已明确的选型边界？",
    "budget": "mid",
    "max_tokens": 4000,
    "trace": true,
    "temporal_window": {
      "start": "2026-09-01T00:00:00Z",
      "end": "2026-11-10T00:00:00Z"
    }
  }'
```

| 参数 | 人能看懂的含义 |
|---|---|
| URL 中的 `agent_memory` | 从哪个 Bank 检索 |
| `query` | 用户问题；由 Hindsight 准备向量等后续输入 |
| `budget:mid` | 检索努力程度档位，影响候选/扩展配置；不是 4,000 Token 上限 |
| `max_tokens:4000` | 本次返回记忆的 Token 预算，现场口径以记忆正文为主，不是 HTTP 响应所有字段总长度 |
| `temporal_window` | 时间路径的窗口参数；不是保证所有图/时间扩展结果都落在窗口内的全局过滤器 |
| `trace:true` | 请求返回可用的过程诊断信息 |

**调用边界：** 应用→Hindsight 是上面这个 HTTP；Hindsight→Memlake 是另一个内部 gRPC。官方架构称后者带上检索与排序策略；上面 HTTP 不能直接证明内部 protobuf 字段和模型批次。

该成功请求在 PG 后端验证，不构成 Memlake 实测证据。请求体不包含 `reranker_model` 字段；模型调用策略由部署/Bank 支持的配置确定。

[官方 Memlake 架构](https://docs.hindsight.vectorize.io/enterprise/memlake/architecture/)、[此前真实接口调用记录](../接口调用记录.md#10-agent-recall-four-arms)。

---

<a id="independent-review"></a>

## 附录 B. 架构边界与技术选型评估

2026-11-12。评估依据为现场 SQL、API trace、官方技术文档与公开源码。本文讨论架构边界和实施优先级；AGE 与本地模型尚未进行对照测试，拟研发机制的收益有待验证。

**核心判断：建设通用的检索与模型执行能力，MemoryRecall 保留为业务适配入口；按端到端瓶颈决定投入，不以一个接口、本地模型或图插件本身作为竞争力。**

### B.1 业务适配与通用内核的职责边界

**风险存在，建议明确分层。** `world / experience / observation`、Observation 如何追溯来源、不同事实如何加权，以及 Reflect 如何规划工具，均属于 Hindsight 的业务策略。PG 只需理解 ID、属性、过滤、排名、边、时间范围、投影列和资源预算。

现场 SQL-041 通过来源事实的共享实体映射回 Observation，SQL-042 则对普通事实直接扩展。这两条不同路径应由适配层表达，而非成为 PG 内核内置的记忆类型分支。

| 层次 | 放什么 | 对其他应用的复用价值 |
|---|---|---|
| **Hindsight 适配层** | MemoryRecall、事实类型映射、来源规则、评分/Token 策略、Reflect 工具编排 | 可随记忆框架演进，不牵动通用内核语义 |
| **PG 通用执行层** | 接收多路候选子计划；融合、Top-K、延迟物化、关系扩展、并行/迭代、模型调用与观测 | 可服务混合搜索、推荐、RAG 和记忆检索 |
| **独立模型 runtime** | Embedding/Rerank、版本、批处理、缓存、GPU/CPU 与服务配额 | 与数据库解耦部署，本地和远程均可接入 |

MemoryRecall 可以是适配层函数、SQL 包装或产品入口；不能把“一次调用”直接等同于内核融合。先用 SQL/扩展建立候选流基线，共享状态与调度确实受限时再确定核心研发。PG 的 Custom Scan 是可用扩展入口，不是现成的记忆执行器。[PG Custom Scan](https://www.postgresql.org/docs/16/custom-scan.html)

### B.2 端到端瓶颈与模型部署策略

**需要按路径判断。模型路径优先解决模型成本，RRF 路径仍有独立检索优化价值。** “19 条 SQL 耗时约一秒”不够准确：请求 21 的 PG execute 累计为 360.034 ms，驱动调用累计为 942.112 ms，HTTP 为 1.585 s，累计数含重叠，均不能直接当作数据库关键路径。

| 同一请求内的证据 | 直接说明什么 |
|---|---|
| 请求 21：RRF；HTTP 1.585 s，检索 trace 923 ms；SQL-038 一次 PG execute 212.779 ms | 不调用神经重排时，检索是重要成本；优先分析大查询及宽候选处理，而不只减 SQL 数量 |
| 请求 23：MaaS；HTTP 10.294 s，重排 7.782 s，Embedding 1.834 s，检索 493 ms | 此路径的主瓶颈在模型侧；检索优化不能消除重排等待 |

例如，**假设请求 23 的 493 ms 检索全部位于关键路径、可以完全消除，其占 HTTP 总时间也只有约 4.8%**。这是条件性的时间预算分析，不是实测可达加速，更不能与请求 21 拼接。

**本地/同区域模型值得对照，但不是必然更快。** 它可能减少网络、供应商排队和外部配额依赖；也可能因 CPU、GPU不足、冷启动或并发干扰而变慢。模型、输入长度、精度、batch 与硬件都必须固定或明确记录。官方 Cross-Encoder 文档同样要求针对具体模型、硬件和输入测量不同后端的收益。[Sentence Transformers 推理优化](https://www.sbert.net/docs/cross_encoder/usage/efficiency.html)

Hindsight 当前代码已支持本地 Embedding 和 Cross-Encoder；单纯增加本地调用入口难以形成差异化优势。[Embedding 实现](https://github.com/vectorize-io/hindsight/blob/34a138684a899b6ec34175f7a2b633860466d289/hindsight-api-slim/hindsight_api/engine/embeddings.py)、[Rerank 实现](https://github.com/vectorize-io/hindsight/blob/34a138684a899b6ec34175f7a2b633860466d289/hindsight-api-slim/hindsight_api/engine/cross_encoder.py)

数据库的竞争力应体现在：**同等质量下，更少候选搬运与重复取数，更有效的模型输入、批处理和预算管理，以及稳定的多请求吞吐。** 当前 300 组输入已一次批量提交，不能再把“首次批量化”计为新增收益。优先采用独立模型服务，避免与 PG Backend、事务和在线查询资源强耦合。

### B.3 Apache AGE 的适用场景与对照评估

**AGE 应纳入选型实验，不能因为它是图插件就推定更快。** AGE 是 Apache 顶级项目及 PG 属性图扩展，提供 Cypher 和 SQL 混合查询；其架构把 Cypher 转换为 PG Query tree，并复用 PG 事务与存储，底层也使用图对应的 schema、顶点表和边表。[官方架构](https://age.apache.org/overview/)、[图存储结构](https://age.apache.org/age-manual/master/intro/graphs.html)

Hindsight 当前主要是有限种子、共享实体、预计算语义边、因果/时间边的受限扩展，用 JOIN/LATERAL 表达本身合理。**尚未找到作者明确比较并否决 AGE 的一手记录。** “减少依赖、复用关系结构、满足有限扩展”属于架构推断，不能冒充作者结论。

本次三条图查询 PG execute 累计约 60 ms，物理边仅 6,085 行，尚不足以决定图引擎选型。未来若出现复杂多跳、路径约束或 Cypher 开发需求，AGE 的价值更值得验证；当前应与优化后的 SQL 对照，而非直接替换。

评测必须保持：边方向、去重、每源/每实体上限、事实过滤、Observation 来源映射、权限和超时语义相同。AGE 的模式表达能力与查询性能分别验收。实测环境是 PG 16，官方下载矩阵列出的对应稳定候选为 AGE 1.6.0；不要把其他 PG 分支或预发行版本的能力直接归给它。[版本兼容矩阵](https://age.apache.org/download/)

**本轮没有实施 AGE 迁移。** 下一步是固定 PG16/AGE 版本，把 SQL-040/041/042 的完整语义逐项映射后，比较小图、高扇出、多跳、大图、并发写入与删除场景。

### B.4 Reflect 多轮取证的数据库支撑能力

**加强多轮取证，保持 LLM 规划与生成在策略/模型层。** Reflect 不只是执行一次 Recall；数据库、工具调度、LLM 时间和证据质量要分别观察。

原始响应中的工具与 LLM trace 统计如下：

| 请求 | HTTP | 工具 trace | LLM trace |
|---|---:|---|---|
| 11：默认工具 | 135.374 s | 9 次，均为 search_mental_models；累计 4.568 s | 11 次调用，累计 130.729 s |
| 22：raw-only / low | 34.862 s | 4 次，均为 recall；累计 2.514 s | 5 次调用，累计 32.231 s |

这是同一请求各自的 trace 累计，不是 PG execute，也不宣称严格的关键路径分解。两请求工具和预算条件不同，**不能把 135 秒到 35 秒写成优化加速**。但这些证据表明，当前两个 Reflect 样本中 LLM 与多轮编排的成本显著，不能只盯数据库。

| 目标 | 数据库提供的通用能力 | 策略层仍决定什么 |
|---|---|---|
| **更快取证** | 批量证据读取、知识新鲜度检查、请求内向量/候选复用、按数据水位失效的缓存 | 哪些子问题互相独立、哪些查询可以一起提交 |
| **改善证据覆盖** | 多查询检索、分路窗口、关系/时间扩展、增量继续检索、返回各路贡献与截断原因 | 何时扩大窗口、改写问题、继续检索或停止 |
| **支撑可追溯回答** | 来源、版本、时间、派生依赖及从摘要展开原始证据的读取能力 | 如何解释证据、处理矛盾并生成回答 |
| **控制整次成本** | 按请求标识累计模型候选、输入 Token、次数及预算，支持取消与限流协同 | 总预算与超限后的业务行为 |

模型 Reflect 已出现 20,000 TPM 限制，100 候选第一轮成功、第二轮仍超额；因此需要整次 Reflect 的累计输入预算，而非只有每次 Recall 的候选上限。Recall 最终返回记忆正文的约 4,000 Token 预算也不能替代模型输入预算。

数据库可以支持更广的候选检索，但不能单独保证召回率或回答准确率提升。重排找不回未进入候选的证据；扩大窗口也可能增加噪声和模型成本，应分别测候选覆盖、排序、引用正确性与最终回答质量。

### B.5 实施优先级与验证计划

1. **先明确分层与端到端基线。** RRF Recall、模型 Recall、Reflect 分开统计，记录模型、工具、DB execute、驱动和队列时间。
2. **并行验证模型部署与通用候选管线。** 同模型同候选比较远程/同区域/本地；比较宽候选与 ID/分数管线，报告质量、资源与时间。
3. **把 AGE 作为对照候选。** 固定版本和语义后实测，再决定是否引入。
4. **按瓶颈深化执行器/访问方法。** 共享状态、依赖调度和排名剪枝有收益且扩展受限后，再投入核心改动。

MemoryRecall 应定位为 Hindsight 适配/SQL 包装入口，PG 核心提供通用检索与执行机制，避免固化 Agent Memory 业务类型。研发投入以端到端成本、质量和并发瓶颈为依据，性能收益须经原型和同质量对照验证。


---

原始证据保留在[主报告](../PG增强分析报告.md)、[SQL 执行记录](../SQL执行记录.md)及原 evidence 目录。正文已包含展示所需的 SQL 与关键数据；单文件 HTML 将外部本地证据引用作为编号展示，不依赖这些附件才能阅读。
