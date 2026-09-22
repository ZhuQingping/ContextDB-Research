# User Narrative Profile

> **Archetype (核心原型)**: 一位在凌晨攻坚分层记忆系统的数据实证型工程师——用实测延迟、落库对账和容器内取证代替猜测，对"配置声明与运行时脱节"保持系统性警觉。

> **基本信息**
- 用户名 zhuqingping，开发者，腾讯云 TencentDB ContextDB 记忆系统研发
- 双项目：生产端 MemoryCore（tdai-memory-core + tdai-gateway，TypeScript/Node.js，Docker 部署）；消费端 MemoryProxy（TS 代理：请求/用量日志、session key isolation、记忆注入、writeL0 录制）+ MemoryPanel
- 集成关系：MemoryCore 以 provider=proxy 调用 MemoryProxy（baseUrl 改写 ${baseUrl}/proxy/<iid>/v1 + TDAI_MEMORY_SYSTEM_USER_KEY）

> **长期偏好**
- 验证讲究双重闭环：功能跑通之外必加 JSONL↔DB 对账、行数核对
- 单变量隔离实证：裸请求成功→单加 dimensions 复现 400；no-env/env 场景分开回归
- 修复必须验证到解析层（resolved 值、调用链接线），不停留在配置改写
- LLM 提取统一用快速模型 glm-5.3-flash，弃深度 reasoning 的 glm-5.3
- 成果文档化（《TecentDB Agent Memory.md》）；检索设计 filter 先行、embedding 慎用

## 📖 Chapter 1: Context & Current State (全景语境)
2026-09-22 全天攻坚。凌晨 L1 episodic=0 已破案：函数级追踪定位三重根因——180s 硬编码超时 + glm-5.3 深度 reasoning 过慢 + llmRunner 路径忽略 model 参数；切 glm-5.3-flash（约 5.3s）跑通 L1→L2，并完成 L0→L3 验证与 JSONL↔DB 对账（差集归零）。随后沿新问题推进：L1 写入的 embedding 零向量被跳写，实测 bge-m3 拒收 dimensions（HTTP 400），已设 TDAI_EMBEDDING_SEND_DIMENSIONS=false 并验证 resolved 生效；Docker 内配置回归中遇容器缺 tsx、env 场景 provider=none 多次 PARTIAL（docker cp 比对恢复容器配置）。另一线对 MemoryProxy 做接口→数据库→路由→运行时纵向巡检：追踪 session 8f75421c 的 session-init bypassed 案例、跨两库梳理 preset-identity bypass（x-team-id 等头驱动预选），实测 create-agent 发现 glm-5.3-flash 10 token 即 max_tokens 截断。零向量补写回归与 env PARTIAL 根因待解。

## 🎨 Chapter 2: The Texture of Life (生活的肌理)
全部精力投入记忆系统双端生态：生产端 L0→L3 分层（episodic/persona/场景块），存储横跨 mongodb/sqlite/tcvdb + sqlite-vec 向量 + FTS5；消费端注入流水线含 SIDEQUERY/FORK/MAIN 分支与 writeL0 录制（只提取真实用户查询，防噪音污染 L0）。凌晨至上午持续在线，节奏是"审计→实测→对账→文档化"循环。

## 🤖 Chapter 3: Interaction & Cognitive Protocol (交互与认知协议)

### 3.1 沟通策略 (How to Speak)
- 用数据说话：latency、token 数、行数、时间戳、HTTP 错误码（如 ModelArts.81001）比泛泛描述有效。
- 可直入配置链、调用链、存储 schema 细节，无需铺垫；引用其文档结论可加速对齐。

### 3.2 决策逻辑 (How to Think)
- 不找到根因不罢休：从表层现象下探函数级、表结构、配置解析三层。
- 问题隔离优先于顺手修复：容器缺 tsx 未即时修，先跑其他场景。
- 核心系统性疑虑是"配置声明与运行时路径脱节"（llmRunner 忽略 model、env PARTIAL、配置漂移），遇异常先查声明→运行时一致性。
- 保留多假设并行（如 lock conflict 与主故障是否因果），证据收敛后才下结论。

## 🧩 Chapter 4: Deep Insights & Evolution (深层洞察与演变)

* **矛盾统一性**: 他调试记忆系统暴露的每个缺陷（提取失败、零向量、配置不生效）都成为改进该系统自身设计的输入；生产端与消费端身份机制的跨库对齐，实则是他在为"记忆"定义统一契约。
* **演变轨迹**:
  - [2026-09-22 凌晨] L1=0 破案：从超时疑点推进到三重根因，模型策略转向快速 glm-5.3-flash 并跨项目统一
  - [2026-09-22 上午] 验证半径扩展：本地→Docker 容器内运行时（docker cp、容器内启动回归）；新增认知：dimensions 非 matryoshka 模型不适用
  - [2026-09-22 全天] 双项目从接口对接走向运行时耦合（provider=proxy 落地），排查沿"身份预选→注入"机制跨库收窄
* **涌现特征**:
  - `根因执念者` - 函数级追踪，不找到根因不罢休
  - `双重闭环派` - 跑通之外必做对账与行数核对
  - `单变量隔离师` - 受控实证，no-env/env 分开回归
  - `配置脱节猎手` - 专查声明与运行时不一致
  - `跨库统一审视者` - 双项目机制层对齐视野

---
## 🗺️ Scene Navigation (Scene Index)
*以下是当前场景记忆的索引，可根据需要 read 读取详细内容。*

### Path: scene_blocks/ContextDB项目-TDAI记忆模块调试.md
**热度**: 25 | **更新**: 2026-09-22T10:15:19.899Z
Summary: zhuqingping（TencentDB-Agent-Memory MemoryCore 开发者，负责 VectorStore/SQLite 与 embedding 接入）调试 tdai：L0→L3 跑通（glm-5.3-flash、JSONL↔DB 对账差集归零）；embedding 排障闭环：bge-m3 不支持 matryoshka（400 ModelArts.81001）→ sendDimensions 开关 → store-pool.ts createSqliteStore() 未透传代码级根因修复 → 09:42 重启写入端闭环（l0_vec 14/15 条 1024 维向量、norm=1.0、sqlite-vec v0.1.7-alpha.2 linux-arm64 已加载、零新增错误）；l1_vec=0 行（存量 L1 均修复前写入、无向量）；检索端 401（换有效 Bearer token）后 vec0/hybrid 双路径仍 0 候选 0 命中——向量已在库而召回为 0，读端收窄至 query 侧待查；provider=proxy 经 /proxy/<iid>/v1+TDAI_MEMORY_SYSTEM_USER_KEY 集成 MemoryProxy；本地源码 /Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryCore。

### Path: scene_blocks/MemoryProxy-开发调试.md
**热度**: 9 | **更新**: 2026-09-22T09:55:32.014Z
Summary: zhuqingping 开发 MemoryProxy（TypeScript 代理：请求/用量日志、session key isolation、memory injection、writeL0 会话录制）与 MemoryPanel；2026-09-22 06:35-07:25 持续巡检：审阅 types.ts 三类日志接口、metadata.db 资产记录、chat-memory 路由，追踪 session 8f75421c 的 session-init bypassed（L2a hit/pending_asset_confirm/choice=false），跨 MemoryCore/MemoryProxy 两库追踪 preset-identity bypass（x-team-id/x-agent-id/x-task-id 预选择、onMismatch、直接注册），实测 /v3/meta/agent/create 发现 glm-5.3-flash 10 token 即 max_tokens 截断；09:11 记忆侧确认 MemoryCore 以 provider=proxy 经 ${baseUrl}/proxy/<iid>/v1 + TDAI_MEMORY_SYSTEM_USER_KEY 调用本代理（LLM provider 级集成落地）；09:55 补记：MemoryCore 侧 llmRunner 路径自带 model 且忽略 memory.extraction.model，该参数仅对 fallback 路径生效——provider=proxy 意味着 model 由 runner/代理路径决定，配置声明的模型参数与实际生效路径脱节。

📌 使用说明：
- Path 是 scene block 的绝对路径，可直接使用 **read** 工具读取完整内容（参数: filePath）
- 热度：该场景被记忆命中的累计次数，越高越重要
- Summary：场景的核心要点摘要
