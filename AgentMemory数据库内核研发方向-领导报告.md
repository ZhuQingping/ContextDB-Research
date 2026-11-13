# ContextBase 面向 Agent Memory 的增强规划：提升性能，降低成本

分析日期：2026 年 11 月 13 日。对象：数据库产品与内核研发决策。

本文基于 Hindsight 的真实接口与 PG SQL 审计、当前工作区源码，以及 Elasticsearch、BigQuery、Snowflake 等一手资料，提出研发规划。文中区分三类内容：**现场观察、业界已有机制、ContextBase 建议方案**。友商实现证明技术有参考价值，不代表本项目已经实现或取得同等收益。

## 1. 决策摘要：只保留性能与成本两条主线

> **ContextBase 面向 Agent Memory，重点提升性能、降低成本：通过数据库融合执行缩短记忆召回与处理时间；通过减少不必要的模型工作，降低持续构建、更新和使用记忆的运行成本。两项目标均需满足约定的召回与回答质量要求。**

| 方向 | 要解决的问题 | 建议能力与手段 | 预期收益 | 当前证据与规划状态 |
| --- | --- | --- | --- | --- |
| **提升性能** | 多次 SQL 交互、串行调度、提前读取正文等增加召回开销；调用模型时还可能受模型阶段限制 | 延续一个 `MemoryRecall` 入口、融合检索执行与批量模型重排两项能力；内部采用延迟物化、依赖感知的并行执行和适用的剪枝 | 减少数据搬运、往返等待和无效计算，缩短召回时间 | 现场已有 SQL 与阶段耗时证据；Elasticsearch 提供统一检索树和重排参照。具体提速待验证 |
| **降低成本** | 抽取、比较、整合和回答持续使用模型，费用长期累积；目前尚不清楚哪些工作还能节省 | 先找出高成本、可避免或可简化的任务，再选择结果复用、增量处理、任务分流；适合时采用模型蒸馏 | 减少昂贵模型处理量及重复计算，降低每次写入、整合和问答的总成本 | BigQuery、Snowflake 已有降本机制；当前源码存在相关任务入口，但 ContextBase 尚无蒸馏降本实测 |

**模型成本感知、蒸馏、并行、剪枝都是手段，不再分别列为新的大方向。** 模型成本感知与原有融合执行规划整合，避免重复立项；蒸馏是否采用，由实际任务与总成本决定。

两条主线有交叉：少做模型计算可能同时改善性能和成本；提高并发也可能增加资源费用。因此需要同时报告耗时、费用和质量，不能只展示 QPS。

## 2. 现场证据：哪些问题已经确认

### 2.1 接口耗时表明，数据库与模型需要分开分析

| 已采集请求 | 接口耗时 | 阶段证据 | 对规划的含义 |
| --- | ---: | --- | --- |
| **RRF recall，21 号** | 1.585 秒 | 检索约 0.923 秒；19 次业务 SQL，PG 执行时间合计 0.360 秒，驱动等待合计 0.942 秒 | 融合执行有可研究的交互与调度空间；两个 SQL 合计不是请求关键路径，不能相减当作纯网络时间 |
| **MaaS recall，23 号** | 10.294 秒 | embedding 约 1.834 秒，检索约 0.493 秒，模型重排约 7.782 秒 | 重排阶段约占接口时间 75.6%；优化 SQL 或移动模型调用位置，不代表这部分计算会自动缩短 |
| **RRF reflect，22 号** | 34.862 秒 | 4 次 recall 工具记录合计 2.514 秒，5 次模型调用记录合计 32.231 秒 | 模型交互约占接口时间 92.5%；降低整体等待，还需要研究模型处理量与可复用结果 |
| **retain，20/26 号** | 11.107 / 9.017 秒 | 有 SQL 审计，缺少可靠的模型阶段分解 | 可以定位 SQL 交互，不能把接口时间减去 SQL 时间直接解释为模型时间或费用 |

模型调用记录包含通信、排队、输入处理和输出生成，不等于纯 GPU 计算时间。耗时占比也不等于费用占比。以上来自不同请求，不构成优化前后对照。

证据：[关键请求复核](reports/agent-memory-performance-cost-20261113/evidence/local-evidence-reverification.json)、[SQL 双侧审计](reports/agent-memory-performance-cost-20261113/evidence/audit-summary.json)、[Recall 时间明细](reports/agent-memory-performance-cost-20261113/evidence/recall-21-timing-analysis.json)。

### 2.2 19 次 SQL 说明了哪些工作发生在 PG

| 业务步骤 | SQL 编号 | 调用次数 | PG 执行时间合计 | 作用 |
| --- | --- | ---: | ---: | --- |
| 准备 | 036、037 | 2 | 0.188 ms | 读取 Bank 配置等前置数据 |
| 向量与关键词检索 | 038 | 1 | 212.779 ms | 一条 SQL 内含六个分支，分别取三类事实的向量与全文结果 |
| 时间入口 | 039 | 1 | 18.875 ms | 找到时间范围内的候选记忆 |
| 时序扩展 | 040 | 9 | 65.017 ms | 沿时间、因果等指定关系继续扩展，逐批取得候选 |
| 图扩展 | 041、042 | 3 | 60.193 ms | 从已有候选寻找共享实体或其他关联记忆 |
| 结果补全 | 043—045 | 3 | 2.982 ms | 为最终结果补充实体、片段等信息 |
| **合计** | | **19** | **360.034 ms** | 各语句时间相加，不能直接作为请求的串行关键路径 |

当前采集路径主要表现为混合检索后继续时序扩展，再进入图扩展；图部分存在并发。不能把“逻辑上四路检索”理解为“PG 内已经四路同时运行”。规划时应识别真实依赖：图扩展需要候选种子，独立分支才能并行。[逐次调用顺序](reports/agent-memory-performance-cost-20261113/evidence/recall-21-sequence.json)

SQL-038 当前关键词分支使用 `ts_rank_cd`，别名虽为 `bm25_score`，但不等于已经采用 BM25。优化时应与合适的全文插件比较，不能把旧查询的代价当作最新 PG 组合的必然上限。完整 SQL 保留在第 7 节和[原始目录](reports/agent-memory-performance-cost-20261113/SQL执行记录.md)。

### 2.3 候选怎样变成最终记忆

```text
四路检索：642 向量 + 502 全文 + 622 图 + 149 时序
                         |
                         v
                 1,915 条分路候选
                         |
                         v
                 RRF 按 ID 合并：1,032 条
                         |
                         v
                  保留 300 条参与后续排序
                         |
              +----------+----------+
              |                     |
         RRF 排序路径          MaaS 模型重排路径
                            300 条全部送入 bge 模型
                                一次批量请求
              |                     |
              +----------+----------+
                         |
                         v
          综合评分，选择正文能放入 4,000 Token 的记忆
                         |
                         v
              本次分别返回 38 条 / 35 条
```

Token 是文本长度的模型计量单位。4,000 Token 预算表示只保留能装入该文本预算的记忆，不是再调用一次重排模型。当前预算统计口径是记忆正文，不能等同于整个最终提示词的全部 Token。

35 与 38 是本次输入下的结果，不是固定返回数量，也不能据数量判断模型方案的质量更高。MaaS 路径已经一次批量处理 300 条，不存在把“300 次逐条 RPC”合并为一次的新增收益。[RRF 请求摘要](reports/agent-memory-performance-cost-20261113/evidence/21-dual-rrf-recall-summary.json)、[MaaS 请求摘要](reports/agent-memory-performance-cost-20261113/evidence/23-dual-maas-recall-summary.json)

## 3. 性能方向：统一执行检索与重排，减少整条流程的等待

### 3.1 建设什么能力

延续既定方案：**通过一个 `MemoryRecall` 入口，提供融合检索执行和批量模型重排两项能力。** 此处是 Hindsight 到数据库侧的规划入口，并非增加七个业务 API。当前用户调用 recall 本来就只有一次 HTTP 请求，待优化的是其内部到 PG 的多次业务 SQL 交互与跨层处理。

建议执行过程如下，尚未实现：

```text
MemoryRecall 请求
    |
    +-- 向量检索 ------> 图扩展（等待向量候选种子）
    +-- 全文检索
    +-- 时间入口 ------> 有界时序扩展
    |
    v  上述分支按依赖执行，独立工作并行，完成后汇合
RRF 去重、融合、Top-K 裁剪
    |
    v
只读取入选候选需要的正文与属性
    |
    v
统一组织请求所需的批量模型重排
    |
    v
综合评分、文本预算筛选、最终信息补全
    |
    v
返回最终记忆与执行统计
```

### 3.2 具体减少什么工作

| 技术手段 | 对应现场问题 | 争取的收益与边界 |
| --- | --- | --- |
| **融合执行＋延迟物化** | SQL-038 在候选阶段就读取 `text`、`context` 等较宽字段，后续还会融合与裁剪 | 先用 ID、分数等必要信息筛选，再取入选记录正文，减少搬运。普通 SQL 也可先做这部分改写，不能全部算作内核创新 |
| **依赖感知的查询内并行** | 19 次交互包含独立工作和逐批扩展，也包含必须等待种子的任务 | 在资源允许时并行独立分支、批量执行关联访问；不能把有前后依赖的步骤强行同时启动 |
| **适用的分数上界剪枝** | 部分检索可能计算了最终不会入选的记录 | 在具有有效分数上界的算子中跳过不可能入选的记录；不能直接认定任意 RRF、时间权重或模型评分都能安全剪枝 |
| **模型成本感知的计划选择** | 模型阶段可能比数据库阶段更贵，单独追求 SQL 更快可能偏离总体目标 | 将模型输入量、费用与时延纳入整条计划；这是融合执行的深化，不另立重复方向 |

已有离线结果提供了边界：按已取回字段估算，候选正文与上下文从全部分路记录到前 300 条，UTF-8 字节量有较大差异，但这不是网络、磁盘或耗时收益；两种保守 RRF 上界策略在本条轨迹中均未提前终止。应验证实际减少的工作，不能先承诺剪枝提速。[候选负载分析](reports/agent-memory-performance-cost-20261113/evidence/20261112-candidate-payload-offline-analysis.json)、[RRF 回放](reports/agent-memory-performance-cost-20261113/evidence/20261112-rrf-pruning-offline-replay.json)

### 3.3 业界依据：Elasticsearch 已经怎样组织检索

Elasticsearch 的 `_search` 可以组织检索树：用全文与向量子检索生成候选，通过 `rrf` 融合，再将候选交给 `text_similarity_reranker`。全文与向量是这里明确的两路，不等于它已经复现 Hindsight 的图与时间两路。[RRF 官方接口](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/rrf-retriever)、[模型重排接口](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/text-similarity-reranker-retriever)

下面按官方接口结构组合一个演示请求。需要预先建好索引与推理端点；三维向量只用于展示，实际必须匹配索引维度。该请求本次未执行。

```http
POST memories/_search
{
  "size": 35,
  "retriever": {
    "text_similarity_reranker": {
      "retriever": {
        "rrf": {
          "retrievers": [
            {"standard": {"query": {"match": {"text": "数据库选型风险"}}}},
            {"knn": {"field": "embedding", "query_vector": [0.1, 0.2, 0.3],
                     "k": 300, "num_candidates": 600}}
          ],
          "rank_window_size": 300
        }
      },
      "field": "text",
      "inference_id": "my-rerank-model",
      "inference_text": "数据库选型风险",
      "rank_window_size": 300
    }
  }
}
```

`standard`、`knn` 分别表达全文和向量检索；RRF 的窗口控制分支参与融合的数量，重排窗口控制交给模型的文档数量，`size` 控制返回条数。这里的 35 是示例条数，不是 Hindsight 的 4,000 Token 预算。模型由推理端点提供，不代表 GPU 模型在数据库执行进程中直接运行。

对剪枝，Lucene/Elasticsearch 的 Block-Max WAND 通过词项块的分数上界跳过不可能进入 Top-K 的块，为“少做无效全文评分”提供了明确依据；它不证明本项目的四路融合可以整体套用同一上界。[Elastic 技术说明](https://www.elastic.co/blog/faster-retrieval-of-top-hits-in-elasticsearch-with-block-max-wand)

**借鉴结论：统一组织检索与重排有成熟产品参照；ContextBase 的研发价值，应体现为在 PG 体系中处理好关系、时间、文本和向量访问的协同，并证明减少了真实工作量。**

## 4. 成本方向：先找出能省的模型工作，再选择手段

### 4.1 要解决的问题

长期记忆不断写入和更新，抽取事实、比较已有结论、整合观察及回答问题都会持续使用模型。当前需要查清：**哪些费用是必要的，哪些输入没有变化，哪些任务只需简单判断，哪些必须保留原模型处理。**

目标是降低每次写入、整合和问答的总成本。模型蒸馏只是候选手段，不能先决定蒸馏，再为它增加业务任务；已有结果复用和增量处理也不能重新算作新增研发成果。

### 4.2 ContextBase 有什么实际使用场景

**优先分析记忆整合中的重复判断。** 当前工作区的 `consolidation/triage.py` 已判断新事实是否重述已有观察；可确认的重复事实追加证据，其余进入后续整合。`reflect/agent.py` 也有按问题筛选证据的路径。这说明存在固定判断任务，不证明已经完成蒸馏、部署已启用或已实际省钱。[源码核对与文件哈希](reports/agent-memory-performance-cost-20261113/evidence/performance-cost-current-code-evidence.json)

例如，下列是解释业务的构造例子：

```text
已有观察：项目 X 使用 PG16，部署在华东。

新事实 A：X 的生产数据库仍是 PG16，运行在华东。
  -> 确认为重复表述：追加来源证据，避免重复生成观察内容。

新事实 B：项目 X 计划升级到 PG18。
  -> 有新信息：继续交给原模型整合，不能按重复内容丢弃。
```

建议先测量整合前判断与整合生成各自的 Token、耗时、费用和处理量。如果简单判断占比高，且现有判断模型仍然昂贵，才进一步评估更低成本的模型。若当前分流已经有效，新增方案只能计入相对该基线的进一步节省。

Reflect 的证据筛选可作为第二个验证场景：减少回答模型阅读的无关内容，但必须检查关键证据漏判和最终回答质量。不能因为输入 Token 少了，就认定答案质量不变；也不能认为五次 Agent 决策都能被分类器替代。

### 4.3 业界依据一：BigQuery 用蒸馏降低批量分类成本

BigQuery 官方文档描述：对 `AI.IF`、`AI.CLASSIFY`，用 Gemini 标注部分样本，以 embedding 为特征训练轻量分类器，质量检查通过后处理大部分记录，必要时回到远程模型。该功能目前为预览，输入约需至少 3,000 行。[官方机制与限制](https://docs.cloud.google.com/bigquery/docs/optimize-ai-functions?hl=zh-cn)

这证明了“固定批量判断可以转为更便宜的计算方式”已有产品实现。对 ContextBase，适合探索长期积累同类任务样本、验证后复用模型，而不是每次 recall 对 300 条候选临时训练。后者既不满足该 BigQuery 产品的行数条件，也尚无收益依据。

蒸馏与级联应区分：蒸馏负责训练低成本模型，级联负责运行时决定哪些记录继续交给原模型。训练成本、轻量推理、回退与质检都必须计入。BigQuery 的例子不能直接证明事实生成、长摘要或 bge 重排都可用分类器替代。

### 4.4 业界依据二：Snowflake 将模型成本纳入查询执行

Snowflake 的 Cortex AISQL 工业论文描述了模型成本感知的计划优化、代理模型级联，以及特定语义关联向分类任务的改写。其共同目标是减少昂贵模型工作，相关机制已经用于该产品，但并非所有机制都适用于所有任务。[Cortex AISQL 论文](https://arxiv.org/abs/2511.07663) §5

对 ContextBase 的启发是：当应用提交明确的判断、分类或关联任务时，执行引擎可以将过滤、连接和模型操作一起比较，选择更合适的顺序和算法。普通过滤、函数代价等基础 PG 已有；新增工作是模型任务的实际代价、可替代路径、质量约束和运行反馈与计划选择相结合。

该能力同时服务性能与成本，应归入融合执行的后续优化，不与其重复立项。若 Hindsight 只执行已确定的 300 条 bge 评分，目前仍没有依据自动跳过其中某些评分。

### 4.5 怎样判断是否真能降本

```text
原方案总成本
       对比
新增训练与校准成本摊销
  + 轻量模型推理成本
  + 剩余原模型调用成本
  + 质检、回退和新增状态维护成本
```

两边采用相同业务任务、质量要求和统计周期；模型费用按实际 Token 或账单计算，自托管模型还应计入算力利用率。先与已经启用缓存、批处理和分流的方案比较，避免夸大收益。

**当前可以立项验证“降低记忆维护的模型成本”，但不能把蒸馏直接写成已确认的降本方案。** 只有找到足够规模、规则稳定且仍有优化空间的任务，才继续投入训练和自动化能力。

## 5. 证据与规划的对应关系

| 证据来源 | 已确认的内容 | ContextBase 可以借鉴什么 | 尚不能据此断言什么 |
| --- | --- | --- | --- |
| **现场接口与 SQL 审计** | 19 次 SQL、候选变化与阶段耗时 | 确定性能研究的具体入口，建立前后对照 | 改为一次融合请求就能消除全部 SQL 和模型时间 |
| **Elasticsearch 官方接口** | 检索树、RRF、模型重排与窗口控制 | 将检索和排序交给引擎统一组织 | 已有同等图/时序能力，或与 PG 相同硬件下必然更快 |
| **Lucene/Elastic 技术说明** | Block-Max WAND 在适用评分条件下跳过无竞争力块 | 设计全文 Top-K 的少算机制 | 任意 RRF 或模型排序都可安全提前停止 |
| **BigQuery 官方产品文档** | 批量分类的蒸馏、质量检查和必要回退 | 对高频固定判断任务验证低成本模型 | 单次 300 条重排可直接复制，或当前项目已证明降本 |
| **Snowflake 工业论文** | 模型成本感知的执行优化、级联和特定算法改写 | 让模型处理量、费用和质量参与执行方案选择 | 论文倍率就是 ContextBase 的可达指标 |
| **当前工作区源码** | 已有判断分流、证据筛选、增量与批处理等基础 | 选择真实任务并建立强基线 | 源码存在等于部署已启用、蒸馏已完成或已有财务收益 |

Elasticsearch、BigQuery、Snowflake 的材料分别支撑不同机制，不能拼接成“友商已经实现完整 Agent Memory 数据库”的结论。更多论文、Memlake 和存储研究保留在[来源与证据索引](reports/agent-memory-performance-cost-20261113/来源与证据索引.md)，不在本次规划中另列第三条主线。

## 6. 研发边界、推进顺序与验收

### 6.1 已有能力与新增工作分开

| 范围 | 可以复用的能力 | 需要研发或验证的内容 |
| --- | --- | --- |
| **性能：数据库执行层** | PG 关系算子、优化器扩展点、已有向量/全文/图插件及模型运行时 | 跨检索分支的执行状态、融合与延迟取列协同、依赖并行、适用剪枝，以及模型任务批次生命周期 |
| **成本：任务与数据状态管理** | 已有内容 hash、增量刷新、任务队列、判断模型接口和批处理 | 对实际高成本任务建立输入版本、处理量与费用统计，比较替代执行路径并验证额外节省 |
| **成本：训练与推理服务** | 成熟训练框架、推理服务、已有专用模型 | 按任务收集与校验样本，训练/评估、版本管理和失效更新；不要求在 PG backend 内训练模型 |

PG 18 已有函数 `COST`、`ROWS`、`SUPPORT`，可以支持动态代价等扩展信息；不能将“有一个成本参数”作为新内核能力。[PG 官方文档](https://www.postgresql.org/docs/18/xfunc-optimization.html)

pgvector 的迭代扫描、pgvectorscale 的磁盘向量访问、VectorChord 的过滤/多向量能力、pg_search 的文本与向量查询均应纳入基线。具体版本审计见[插件核验](reports/agent-memory-performance-cost-20261113/evidence/plugin-source-audit.json)，不可用现场旧版本代替最新组合。

一个入口并不要求内核理解 `world`、`observation` 的业务含义；应用声明范围和策略，数据库提供通用执行机制。先用 SQL 改写和扩展验证，只有现有接口无法表达或无法有效执行时，再提出具体主干改动。普通 SQL 调优或服务集成的收益，应如实归类。

### 6.2 按两条主线推进，不先承诺倍率

| 方向 | 第一步 | 第二步 | 必须交付的证据 |
| --- | --- | --- | --- |
| **性能** | 在固定数据和查询上，对现有 SQL 与最新合理插件组合建立基线 | 对比融合请求、延迟物化和独立分支并行；再验证剪枝和模型代价优化 | P50/P95/P99、SQL 交互次数、读出字节/页面、CPU、模型输入量；候选与答案质量 |
| **成本** | 先分析整合判断与生成，以及 reflect 证据筛选的真实费用分布和现有分流效果 | 有足够收益空间时，再比较复用/增量、专用模型或蒸馏等方案 | 每次 retain/整合/reflect 的总费用、Token、模型处理量、训练摊销、回退率与关键证据漏判率 |

性能比较必须同时固定质量要求、数据、模型与资源；改变模型或候选窗口应作为另一组实验。成本比较必须计入新增工作，不能仅报告昂贵模型调用减少了多少。

更新、删除、权限变化和模型/提示词升级后，要验证复用结果失效与来源追溯；模型任务在事务外处理时，需明确定义输入版本和完成结果的发布方式，避免长时间等待模型占用数据库快照。源表 ACID 与派生记忆的新鲜度要求分开，不以牺牲 PG 基础事务正确性换取表面提速。

**阶段决策：性能主线已有可定位的 SQL 问题，优先做原型对照；成本主线先补齐费用与任务分布，再确定最合适的手段。** 若只证明接口可以调用模型、普通缓存生效或既有分流有效，不足以宣称新增内核创新。

## 7. 关键 SQL 与原始证据

以下均来自已采集 SQL，仅调整空白排版。完整 63 类 SQL、调用归属及已观测的其他路径保留在[SQL 执行记录](reports/agent-memory-performance-cost-20261113/SQL执行记录.md)。

### 7.1 SQL-038：候选阶段同时读取正文与评分

一条语句含向量、全文各三个事实类型分支。它解释了为什么可以先验证“候选阶段少取正文”，但不证明普通 SQL 无法完成该改写。

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

### 7.2 SQL-053：按 ID 批量读取证据

数据库当前可见的是证据读取；如果后续模型任务不被明确提交，数据库不能凭此推测其语义并自动减少调用。

```sql
SELECT
    id, text, fact_type, context, document_id, chunk_id, tags, metadata,
    proof_count, event_date, occurred_start, occurred_end, mentioned_at,
    created_at, updated_at, source_memory_ids, consolidated_at, observation_scopes

        FROM ctxdb_ws_agent_memory.memory_units
        WHERE bank_id = $1 AND id = ANY($2::uuid[])
```

### 7.3 SQL-006、007：文档和片段已经支持变化识别

这些 hash 查询支撑 Hindsight 已有的幂等与增量判断，不能作为新增成果重复计算。

```sql
SELECT content_hash FROM ctxdb_ws_pg_trace_20261112.documents WHERE id = $1 AND bank_id = $2
```

```sql
SELECT chunk_id, chunk_index, content_hash
        FROM ctxdb_ws_pg_trace_20261112.chunks
        WHERE document_id = $1 AND bank_id = $2
        ORDER BY chunk_index
```

### 7.4 SQL-047：读取整合状态

读取整合/写入时间以及待处理、失败数量。它提供状态信息，但单独的最大时间戳不是无缺口完成证明；部署源码还有其他增量窗口和保护机制。

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

### 7.5 SQL-059：已经可以检索预先整理的知识

Reflect 已能检索 Mental Model，预计算本身是已有能力。该 SQL 有 PG 审计与工具 trace 交叉确认，但没有该请求的应用发送侧记录，不能加入双侧 SQL 计数。

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

原始资料与归档：[来源索引](reports/agent-memory-performance-cost-20261113/来源与证据索引.md)。验证范围及未运行项目：[交付与评审记录](reports/agent-memory-performance-cost-20261113/交付与评审记录.md)。本报告未执行新的生产接口或付费模型实验，规划收益均待验证。
