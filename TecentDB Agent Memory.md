# TecentDB Agent Memory

## 核心功能

三个容器组成完整链路（对应代码模块 MemoryProxy / MemoryCore / MemoryKnowledge+MemoryPanel）：

**memory-proxy（:8096，MemoryProxy）— 透明的 LLM 请求代理**

- 原样转发 OpenAI `/v1/chat/completions` 和 Anthropic `/v1/messages`，Agent 只改 base URL 即接入，零代码、无插件
- 转发前后顺手做：会话初始化（首次对话弹表单选 team → agent → task）、system prompt 注入（Skill / Knowledge / Memory L2/L3）、对话回流（写 L0 + 送 Skill 归档）、鉴权（`x-tdai-user-key` 校验）、限流与用量上报
- 自身不落任何记忆数据，所有读写都调 memory-core
- 核心模块：注入器（injection/）、会话初始化、Skill/Memory Bridge（反向代理 core 工具并隐藏 serviceToken）、ProxyStorage（Redis/COS/SQLite/FS/Memory 五种后端）

**memory-core（:8420，MemoryCore）— 记忆与元数据核心，唯一的数据面**
- Memory：L0 对话、L1 原子记忆、L2 场景记忆、L3 核心画像，逐层沉淀
- Knowledge 元信息登记（只存标识/状态/关联，不存内容）
- 资产元数据管理：User / Team / Agent / Task / Skill / Knowledge Asset 及 ACL
- 召回：关键词 + Embedding + BM25 混合检索，无 Embedding Provider 时退化为 BM25
- 存储：SQLite（vectors.db + 每实例 metadata.db）+ 本地文件（jsonl 对话、skill 资源）
- 核心模块：HTTP Gateway、记忆分层 Pipeline（L0→L3）、Skill Memory（版本/资源/路由/对话抽取）、自定义 Memory Prompt（按 Agent > Team > Instance 解析）、生成溯源

**memory-hub（:8125 面板 + :8424 知识服务，MemoryPanel + MemoryKnowledge 合并镜像）**
- :8125 Panel（MemoryPanel）：无状态的团队记忆管理控制台，Web UI + Control API，管团队/用户/Agent/资产分配；不存登录会话，业务数据落外部服务
- :8424 Knowledge Service（MemoryKnowledge）：知识内容引擎
  - LLM-Wiki：上传/拉取文档 → LLM 抽结构化页面 → FTS5 检索 + 知识图谱
  - Code-Graph：git clone → 符号/调用/文件树索引 → 探索查询
  - 存储分两层：knowledge.db（SQLite 元数据）+ `team-*/` 目录（wiki / code-graph 内容本体是文件/仓库）

一句话分工：**Proxy 管接入与转发，Core 管记忆的存储与处理，Hub 管知识内容与管理界面**。Proxy 和 Panel 都无状态，记忆数据只在 Core，知识内容只在 Knowledge。

**Team 是什么概念**

**Agents**是什么概念





## 核心机制





## 记忆写入与提取：先沉淀，才能召回

### 一句话理解

**Memory Proxy 负责拦截模型请求并注入长期记忆，Memory Core 负责把对话逐步沉淀成 L0→L3，再供后续会话召回。**

```text
对话回流
  → L0 原始对话：记住“说过什么”
  → L1 原子记忆：提炼出“结论/偏好/规范”
  → L2 场景记忆：整理成“某个主题下的完整场景”
  → L3 核心画像：压缩成“这个用户/团队是谁，怎么协作”
```

**写入流程（精简版）**

```text
Agent 请求
  → Proxy 注入 system prompt
  → Proxy 转发 LLM 并返回结果
  → Proxy 把本轮对话写回 Core /v3/conversation/add
  → Core 同步写 L0（SQLite 当前态 + JSONL 审计）
  → Core 异步触发 L1 → L2 → L3
```

实测：向 MySQL-Code-Review Agent 连讲 5 条团队规范，从对话到 L3 生成约 3 分钟。

### 模型调用示例：为什么注入到 `system`

一个普通 OpenAI 兼容调用本来是这样：

```python
from openai import OpenAI

client = OpenAI(
    api_key="MAAS_API_KEY",
    base_url="https://api.modelarts-maas.com/openai/v1",
)

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "你好"},
    ],
)

print(response.choices[0].message.content)
```

接入 Memory 后，业务代码通常只需要把 `base_url` / 接入路由指向 Memory Proxy（下面用占位地址表示）。Proxy 会在转发前把 L3 画像、L2 索引和检索工具说明追加/组装到 `system` 内容里，等效于：

```python
client = OpenAI(
    api_key="MAAS_API_KEY",
    base_url="https://<memory-proxy-host>/openai/v1",  # 按实际部署地址配置
)

system_prompt = "\n".join([
    "You are a helpful assistant.",
    "",
    "<tdai_profile_memory>",
    "  <l3_core_memory>用户长期画像：偏好源码级排查，禁止物理删除...</l3_core_memory>",
    "  <l2_scene_index>",
    "    - scene_blocks/mysql-review.md — MySQL 代码评审历史",
    "    - scene_blocks/memory-core.md — MemoryCore 调试历史",
    "  </l2_scene_index>",
    "</tdai_profile_memory>",
])

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "帮我 review 这条 DELETE FROM orders"},
    ],
)
```

**为什么放在 `system`：**

- `system` 表示“给助手的长期指令和背景”，语义上比把记忆伪装成用户消息更正确。
- 模型会先看到 `system`，再看到 `user`，所以 Agent 能在回答前就掌握稳定画像和规范。
- L3 全文和 L2 索引在一个会话内基本稳定，放在 `system` 有利于 prompt cache 复用。
- 业务 Agent 不需要自己查库、拼 prompt；Proxy 统一完成注入、鉴权和身份隔离。

### 分层存储速览

| 层 | 给听众的解释 | 主要存储 | 注入/召回方式 |
|---|---|---|---|
| L0 | 原始对话流水 | SQLite 当前态；JSONL 审计日志 | 按需 `/conversation/search` |
| L1 | 从对话中提炼的原子记忆，如偏好、规则、事实 | SQLite 当前态；JSONL 追加历史 | 按需 `/atomic/search` |
| L2 | 按主题整理的场景记忆 | `scene_blocks/*.md` + `scene_index.json` | 只注入索引，正文按需读取 |
| L3 | 高度压缩的核心画像 | `persona.md` | 全文注入 `system` |

**关键结论：SQLite 不是“多存一份”，而是在线召回的当前态和索引；JSONL 是审计/兜底；Markdown 是 L2/L3 内容本体。**

### 写入路径：写什么、为什么写

| 步骤 | 写入内容 | 为什么要写 |
|---|---|---|
| 1. 写 L0 | 用户/助手原文，加上 `sessionKey`、`teamId`、`userId`、`agentId`、`taskId`、角色和时间 | 保留完整事实和证据；后续 L1 提取失败时还能重放；没有 L0 就无法可靠回答“我们之前原话说了什么” |
| 2. 提取 L1 | `content`、`type`、`priority`、`scene_name`、`source_message_ids`、时间、`metadata` | L0 噪声大，不能直接注入；L1 把“说过什么”变成“值得长期记住的偏好/规则/事实/事件” |
| 3. L1 去重/合并 | 新记忆与相似旧记忆比较，执行 `store / skip / update / merge` | 避免同一事实反复膨胀或互相矛盾；SQLite 保留当前态，JSONL 保留历史 |
| 4. 生成 L2 | 相关 L1 聚合成场景 Markdown，并生成摘要索引 | 单条 L1 太碎；按主题组织后，Agent 可以按需获取完整背景 |
| 5. 生成 L3 | 汇总场景块，压缩成 `persona.md` | 每轮不可能注入全部场景；稳定画像适合每次对话都放进 `system` |

**存储分工：**

| 存储 | 作用 | 为什么需要 |
|---|---|---|
| `vectors.db` | L0/L1 当前态、FTS 索引、向量索引、生成溯源 | 支持租户过滤、Top-K 检索、更新/删除、BM25 和向量 KNN |
| `conversations/*.jsonl` | L0 追加日志 | 便于审计、重放和故障排查 |
| `records/*.jsonl` | L1 追加历史 | 保留去重/合并前的历史；SQLite 是召回当前态 |
| `scene_blocks/*.md` | L2 内容本体 | 场景记忆是长文本，适合按文件读取 |
| `persona.md` | L3 内容本体 | 稳定画像直接注入 `system` |



SQLite 数据库中相关表信息如下：

| 表                 | 作用                                                 |
| ------------------ | ---------------------------------------------------- |
| `l0_conversations` | 保存 L0 当前态：原文、角色、时间、租户隔离字段       |
| `l0_fts`           | 给 L0 原文建 BM25 全文索引                           |
| `l0_vec`           | 给 L0 原文建向量索引，支持语义相似检索               |
| `l1_records`       | 保存 L1 当前态：提炼后的记忆、类型、优先级、租户字段 |
| `l1_fts`           | 给 L1 内容建 BM25 全文索引                           |
| `l1_vec`           | 给 L1 内容建向量索引，支持语义相似检索               |

向量和全文索引相关表结构如下：

```sql
-- 简化后的 schema
-- `embedding_meta` 显示当前配置：
-- {"provider":"openai","model":"bge-m3","dimensions":1024}
l0_vec(record_id TEXT PRIMARY KEY,
       embedding float[1024] distance_metric=cosine,
       recorded_at TEXT)

l1_vec(record_id TEXT PRIMARY KEY,
       embedding float[1024] distance_metric=cosine,
       updated_time TEXT)
       
-- 全文索引
-- 
CREATE VIRTUAL TABLE l0_fts USING fts5(
          message_text,
          message_text_original UNINDEXED,
          record_id UNINDEXED,
          session_key UNINDEXED,
          session_id UNINDEXED,
          team_id UNINDEXED,
          task_id UNINDEXED,
          user_id UNINDEXED,
          agent_id UNINDEXED,
          role UNINDEXED,
          recorded_at UNINDEXED,
          timestamp UNINDEXED
        )
/* l0_fts(message_text,message_text_original,record_id,session_key,session_id,team_id,task_id,user_id,agent_id,role,recorded_at,timestamp) */;

CREATE VIRTUAL TABLE l1_fts USING fts5(
          content,
          content_original UNINDEXED,
          record_id UNINDEXED,
          type UNINDEXED,
          priority UNINDEXED,
          scene_name UNINDEXED,
          session_key UNINDEXED,
          session_id UNINDEXED,
          team_id UNINDEXED,
          task_id UNINDEXED,
          user_id UNINDEXED,
          agent_id UNINDEXED,
          version UNINDEXED,
          timestamp_str UNINDEXED,
          timestamp_start UNINDEXED,
          timestamp_end UNINDEXED,
          metadata_json UNINDEXED
        )
/* l1_fts(content,content_original,record_id,type,priority,scene_name,session_key,session_id,team_id,task_id,user_id,agent_id,version,timestamp_str,timestamp_start,timestamp_end,metadata_json) */;
```

### metadata.db 与 vectors.db 的分工

| 数据库 | 职责 | 常见表 |
|---|---|---|
| `vectors.db` | 记忆数据面 + 检索索引 + 生成溯源 | `l0_conversations`, `l0_fts`, `l1_records`, `l1_fts`, `memory_generation_refs`, `memory_audit`, `skills`, `skill_fts`, `entity_*` |
| `metadata/tdai_metadata_<instance>/metadata.db` | 控制面：鉴权、资产、团队、Agent、配置 | `meta_users`, `meta_user_keys`, `meta_teams`, `meta_team_members`, `meta_agents`, `meta_assets`, `meta_config_params` |

`vectors.db` 中的记忆行通过 `team_id/user_id/agent_id/task_id` 与控制面实体 ID 关联；控制面不存记忆正文。

## 记忆召回

**记忆召回不是“每次把所有历史塞给模型”，而是“稳定背景直注 + 线索索引直注 + 细节按需检索”。**

```text
新会话绑定 Agent
  → Proxy 读取该 Agent 的记忆
  → system 注入：L3 全文 + L2 索引 + 检索工具说明
  → 模型先看到长期画像和场景线索，再回答用户问题
  → 需要细节时，模型调用 L0/L1 检索或读取 L2 正文
```

**注入对象**

- 默认是当前 Agent（`role=self`）。
- 如果当前 Agent 绑定了其他 Agent 的 `chat_memory` 资产，最多额外注入 2 个同团队来源 Agent（`role=imported_from`）。
- 控制面不可用时降级为只注入当前 Agent。

源码：`MemoryProxy/src/injection/injectors/tdai-profile-memory-injector.ts`、`tdai-fixed-asset.ts`。

```
新对话 → sessionInit 绑定 agent → 每轮请求注入 system prompt：
  <tdai_profile_memory>
    <agent name="MySQL-Code-Review" role="self">
      <l3_core_memory> persona.md 全文（约 1-2k token）
      <l2_scene_index> 场景块路径+摘要列表（不含全文）
    </agent>
  </tdai_profile_memory>
  <tdai_memory_tools> 检索工具说明（L0/L1 按需 curl 召回）
```

- **L3 直注**：稳定画像每次对话都带，Agent 天然“知道”用户是谁、有什么规范。
- **L2 只给索引**：L3 是压缩后的结论，L2 索引告诉模型“还有哪些详细场景”。模型判断相关后，再按路径拉取正文。
- **L0/L1 工具按需召回**：每次只注入固定指令，不把 L0/L1 内容塞进 system；模型遇到需要历史证据的问题时，用当前问题调用 `/atomic/search` 或 `/conversation/search`，Proxy 再补齐身份并转发 Core。

一句话解释 L2 索引的价值：**L3 让 Agent 记住“用户禁止物理删除”，L2 索引让 Agent 知道“这条规范来自哪几个历史评审场景”，需要上下文证据时再读对应 Markdown。**

### 为什么召回要靠 SQLite，而不是只靠文件

L2/L3 是 Markdown，直接读文件没问题。但 L0/L1 是高频写入、频繁更新、按租户过滤、按相似度 Top-K 查询的数据，只用 JSONL 会遇到三个问题：

1. **不能高效过滤**：每次都要按 `team_id/user_id/agent_id/task_id/session_id` 扫文件。
2. **不能高效更新**：L1 会去重、合并、删除旧版本；append-only JSONL 无法表达当前态。
3. **不能高效检索**：FTS5 和向量 KNN 都需要索引，JSONL 只适合顺序扫描。

所以 SQLite 承担“在线召回数据库”的角色：

| 表 | 作用 |
|---|---|
| `l0_conversations` | 保存 L0 当前态：原文、角色、时间、租户隔离字段 |
| `l0_fts` | 给 L0 原文建 BM25 全文索引 |
| `l0_vec` | 给 L0 原文建向量索引，支持语义相似检索 |
| `l1_records` | 保存 L1 当前态：提炼后的记忆、类型、优先级、租户字段 |
| `l1_fts` | 给 L1 内容建 BM25 全文索引 |
| `l1_vec` | 给 L1 内容建向量索引，支持语义相似检索 |

JSONL 不是被废弃：它保留审计和兜底能力。但在线 `/atomic/search`、`/conversation/search` 查询的是 SQLite 当前态和索引。

### 一次记忆召回的完整流程

**阶段 1：模型先决定需要哪一层记忆。**

新会话初始化后，system 里已经有 L3 画像、L2 场景索引和工具说明。用户问题到达时，模型先判断：如果当前问题只需要通用能力，就不调工具；如果 L2 索引里已经出现相关场景，就走 `scenario/read` 读取对应 Markdown；如果需要用户长期偏好、提炼后的结论，或某次对话的原文细节，才发起 L0/L1 检索。

**阶段 2：模型发起检索请求，Proxy 负责补齐可信身份。**

模型不会直接构造 `team_id/user_id/agent_id/task_id`，只按注入的工具说明发起请求，典型请求是：

```text
/memory-bridge/v3/atomic/search?q=DELETE FROM orders 是否允许物理删除
Header: x-conversation-id=<当前会话>, x-tdai-service-id=<当前服务>
```

`MemoryProxy/src/memory/memory-bridge.ts` 收到请求后，从 session store 或 binding repo 找到这次会话绑定的身份，然后强制补上 `team_id/user_id/agent_id/task_id` 再转发 Core。这样即使模型输入了错误身份，也不会越过租户隔离；这也是 Proxy 在链路中的第二个作用——除了注入，还负责“可信上下文补全”。

**阶段 3：Core 在 SQLite 里做租户过滤和双路召回。**

以 L1 为例，Core 的检索入口先按身份过滤，再并行查两类索引：

```text
l1_records 当前态
  → FTS5 路线：query 分词后查 l1_fts，按 BM25 排序
  → Vector 路线：query 用 bge-m3 转 1024 维向量，查 l1_vec，按 cosine 排序
  → RRF 合并两路排名
  → 按请求里的 type / scene 等条件收窄
  → 返回 Top-K 候选
```

L0 的流程一样，只是数据源换成 `l0_conversations/l0_fts/l0_vec`。如果请求显式带 `session_id`，L0 会再按会话收窄；不带则跨 session 查同一身份的历史，但租户过滤始终保留。

**阶段 4：Top-K 回到模型，由模型决定是否使用。**

SQLite 返回的是“候选”，不是最终事实判断。当前 `/atomic/search` 和 `/conversation/search` 在混合检索后没有 Cross-Encoder、LLM rerank，也没有硬相关阈值。模型拿到 Top-K 后继续做语义判断：

- 候选和当前问题一致：直接作为回答依据，例如引用“禁止物理删除，改用软删”。
- 候选只是相似但不是当前问题要的：忽略，不强行使用。
- 所有候选都不相关或返回空数组：按工具规范明确说“没有找到记忆”，不能编造。

这个设计把职责分开：**SQLite 负责把最可能的少量候选从大量历史里捞出来；模型负责判断这些候选能否回答当前问题。**

### 两路候选的融合排序

两路检索解决的是不同失败模式：FTS5 擅长命中“物理删除”“DELETE FROM orders”这类明确词；向量擅长命中“数据库能不能直接删数据”这类语义改写。两条路都跑完后，Core 用 RRF 融合排名：

```text
RRF score = 1 / (60 + rank + 1)
```

一条记忆如果同时被 FTS 和向量命中，两个排名得分会相加，所以通常比只被一路命中的记忆更靠前。RRF 只做排名融合，不重新理解语义；当前链路没有 Cross-Encoder 或 LLM rerank。

两路的原始分数含义不同：

| 检索路 | 排序方式 | 分数含义 |
|---|---|---|
| FTS5 | BM25 rank | 关键词匹配强度，经 `bm25RankToScore()` 归一化 |
| Vector | cosine distance | `score = 1 - distance`，越接近 1 越相似 |
| 合并后 | RRF score | 只表示综合排名，不能解释成“相关概率” |

### L0/L1 与数据库的真实分工

L1 查询适合回答“用户有什么长期偏好、规范、结论”。例如新问题问 review 规范，Core 从 `l1_records` 找当前有效记忆，`l1_fts` 提供关键词路，`l1_vec` 提供语义路。

L0 查询适合回答“当时具体聊了什么、报错现场是什么”。Core 从 `l0_conversations` 找原文片段，`l0_fts` 和 `l0_vec` 提供两条召回路线。

数据库的价值不是“再存一份文件”，而是把在线检索需要的四件事做在一起：

1. 当前态：去重、更新、合并后只保留最新有效记录；
2. 隔离：按 `team_id/user_id/agent_id/task_id` 过滤；
3. 全文索引：BM25 快速找明确关键词；
4. 向量索引：语义相似 Top-K。

JSONL 保留写入历史和审计线索，但在线检索不会逐个扫 JSONL。

### 写入时如何复用同一套检索做去重

召回前的同一套双路检索也会用在 L1 写入去重。L1 提取出来后，Core 执行 `batchDedup`：先用 FTS + 向量找出相似旧记忆，再把“新记忆 + 相似旧记忆”交给 LLM 判断。

LLM 判断的依据包括主体是否相同、事实是否一致、时间是否属于同一演化过程、`scene_name` 是否相似；不同 `type` 之间也可以跨类型合并。LLM 会返回四种决策：

| LLM 决策 | 含义 | 写入行为 |
|---|---|---|
| `store` | 新信息 | 插入一条新 L1 |
| `skip` | 旧记忆更好，新记忆无增量 | 不写入新记忆 |
| `update` | 同一事实，新记忆更准确/更新 | 删除目标旧记忆，写入新版本 |
| `merge` | 多条信息互补 | 删除多条旧记忆，合并成一条新记忆 |

这也解释了真实数据里 `records/*.jsonl` 行数大于 `l1_records` 行数：JSONL 保留历史轨迹，SQLite 只保留去重/合并后的当前态。

### 常见疑问澄清

旧插件自动召回路径有 `scoreThreshold=0.3`，但那是单路 FTS/向量过滤；当前工具化召回链路主要靠 Top-K + RRF，混合检索后没有再套 0.3 阈值。

只有部分记录进 `l0_vec/l1_vec`，是因为向量功能后期才开启；开启前写入的旧记录需要 reindex/backfill 后才能进入向量表。当前最新拷贝里，L0 向量只有 49 条、L1 向量只有 14 条，而全文索引分别覆盖 742 条和 31 条。

### 内核源码与检索数据源

| 召回类型 | Proxy / Core 源码 | 数据源 |
|---|---|---|
| L2/L3 直注 | `MemoryProxy/src/injection/injectors/tdai-profile-memory-injector.ts` → `renderBlocksForContext()` | Proxy 调 Core 拉当前 Agent 的 `persona.md` 全文和 `scene_index.json` 摘要；L2 正文不预读 |
| L2 按需读全文 | `MemoryProxy/src/memory/memory-bridge.ts` allowlist 中的 `scenario/read` | 按 `profiles/<team|agent>/scene_blocks/*.md` 读取 Markdown |
| L1 按需检索 | `MemoryProxy/src/memory/memory-bridge.ts` → Core `/v3/atomic/search`；Core `v2-router.ts` → `handleAtomicSearch()` | 主数据源是 `vectors.db.l1_records`；`l1_fts` 提供关键词路，`l1_vec` 提供向量路；只查 SQLite 当前态，不会扫 append-only JSONL 旧版本 |
| L0 按需检索 | `MemoryProxy/src/memory/memory-bridge.ts` → Core `/v3/conversation/search`；Core `v2-router.ts` → `handleConversationSearch()` | 主数据源是 `vectors.db.l0_conversations`；`l0_fts` 提供关键词路，`l0_vec` 提供向量路；JSONL 只做兜底/审计，不是在线检索主路径 |
| L1 检索执行 | `MemoryCore/src/core/tools/l1-candidate-recall.ts` → `recallL1Candidates()` | SQLite 无 native hybrid 时，`searchL1Fts()` 与 `searchL1Vector()` 并行；两者都有结果时用 RRF 合并 |
| L0 检索执行 | `MemoryCore/src/core/tools/conversation-search.ts` → `executeConversationSearch()` | 逻辑与 L1 类似：`searchL0Fts()` 与 `searchL0Vector()` 并行，再用 RRF 合并 |

**检索退化链**：

```text
原生 Hybrid（TCVDB 等后端）
  → SQLite FTS5 + 向量双路，RRF 合并（当前最新拷贝属于这类）
  → 仅 FTS5 BM25（SQLite + 无 Embedding Provider）
  → 返回空（FTS 不可用且 Embedding 不可用）
```

隔离规则：

- L1 `/atomic/search` 过滤 `teamId/userId/agentId/taskId`，不传 `sessionId`，所以能跨 session 找到同一 Agent 的历史记忆。
- L0 `/conversation/search` 请求里显式给 `session_id` 时按会话收窄；不给时跨 session，但始终做租户隔离。
- L2/L3 的 scope 是 `team + agent`，与具体用户和 session 无关。

**节省 Token**：假设积累了 50 个场景块（每个 2k token），全注入 = 10 万 token/轮；索引注入 + 按需读取 = 固定约 1-2k + 命中时 2k。多轮对话下 system prompt 被 prompt cache 复用，边际成本更低。

**提升准确率**：实测 5 条团队规范沉淀为 2 条 instruction 记忆 + 1 个场景块后，新会话问 "review 这条 DELETE FROM orders" —— Agent 直接按已记住的规范（禁止物理删除、改软删）给出修改意见，无需用户重复说明。规范类记忆 priority=95（高优先），召回排序靠前。







## 知识库处理、提取



## 知识库处理、召回





## 疑问

Agent 与 TecentDB Agent Memory 之间的交互是否都走 Restful 请求？

TecentDB Agent Memory 实现是否支持多租户？是否满足云场景下、为多个租户服务的场景，当前的基础设施能满足性能要求吗？
