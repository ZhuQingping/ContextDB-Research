# Claude Code × Hindsight 交互机制分析（recall / retain）

> 分析对象：当前环境中 Claude Code 客户端通过 `hindsight-memory` 插件与 Hindsight 服务端的实际交互机制。
> 分析方法：基于插件源码（`hindsight-integrations/claude-code/scripts/`）与运行时状态文件实证，非推测。
> 配置实例：bank = `company1-project-alpha`，API = `http://10.83.11.134:8888`，auto-recall / auto-retain 均开启。
> 日期：2026-09-29

---

## 0. 结论速览（TL;DR）

Hindsight 给 Claude Code 接入了一个**跨会话的长期记忆库**，它不是改 LLM 模型本身，而是通过 **Claude Code 的 hook 机制**，在"用户提交 prompt"和"模型回答结束"这两个时机，分别做**注入（recall）**和**沉淀（retain）**：

| 过程 | 触发时机 | 实现机制 | 对 LLM 交互的影响 |
|------|---------|---------|------------------|
| **Recall** | 用户每次提交 prompt 时（`UserPromptSubmit` hook） | 跑 `recall.py`，把当前 prompt 作为 query 去 Hindsight 召回相关记忆，包裹成 `<hindsight_memories>` 文本，通过 hook 的 `additionalContext` 字段返回 | **该记忆文本会作为额外上下文，拼在用户本次 prompt 之前一起发给 LLM**。LLM 在生成回答时就"看得见"这些历史记忆了——这是它影响交互的唯一方式 |
| **Retain** | 模型每次回答结束、停下时（`Stop` hook，异步） | 跑 `retain.py`，把本次会话的 transcript（对话记录）切片后 POST 到 Hindsight，由服务端做向量化/抽取/入库 | **完全异步、对 LLM 透明**。不参与当前这轮 LLM 调用，只为未来会话的 recall 准备原料 |

一句话：**recall 是"读"——把过去注入现在；retain 是"写"——把现在存给未来。两者都不触碰模型权重，只在 prompt 的输入侧 / 会话的输出侧做上下文增补。**

> 这与 ContextDB 的目标（"给 Agent 一个持久、可检索、按需召回的上下文层"）是同构的：Hindsight 充当了 ContextDB 的后端存储 + 检索引擎，Claude Code 通过 hook 把它无缝接入 Agent 的 I/O 流。这正是"基于 hindsight 实现 ContextDB 功能"的落点。

---

## 1. 整体架构

### 1.1 组件关系

```
┌──────────────────────────────────────────────────────────────────┐
│                      Claude Code 客户端                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  hook 系统 (hooks.json 注册)                                │  │
│  │   ├─ SessionStart       → session_start.py  (准备)          │  │
│  │   ├─ UserPromptSubmit   → recall.py         ← Recall 通道   │  │
│  │   ├─ Stop               → retain.py         ← Retain 通道   │  │
│  │   └─ SessionEnd         → session_end.py    (收尾)          │  │
│  └──────────────────────────────┬─────────────────────────────┘  │
│                                 │ hook stdin/stdout (JSON)        │
│  ┌──────────────────────────────▼─────────────────────────────┐  │
│  │  MCP server (run_mcp.sh → mcp_server.py)                    │  │
│  │   └─ 暴露 agent_knowledge_* 工具 (手动查/写, 非自动)         │  │
│  └──────────────────────────────┬─────────────────────────────┘  │
│                                 │                                 │
│  ┌──────────────────────────────▼─────────────────────────────┐  │
│  │  LLM 调用 (本次会话)                                        │  │
│  │   system prompt + recall注入的<hindsight_memories> + 用户prompt │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬───────────────────────────────┘
                                   │ HTTP
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  Hindsight 服务端  (http://10.83.11.134:8888)                    │
│   ├─ /v1/default/banks/{bankId}/memories/recall  (recall)        │
│   ├─ /v1/default/banks/{bankId}/memories         (retain, async) │
│   └─ /v1/default/banks/{bankId}/config           (set mission)   │
│   ─────────────────────────────────────                         │
│   内部: 向量化(embed) + 抽取(成 observation 记忆) + 向量/混合检索 │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 两条通道，必须区分

插件提供**两条独立通道**，初学者最易混淆：

1. **自动通道（hook）**——`recall.py` / `retain.py`，纯 Python 标准库（`urllib`），**不需要 mcp 包**。这是本分析的主体，也是"自动 ContextDB"的核心。
2. **手动通道（MCP）**——`mcp_server.py`，注册 `agent_knowledge_*` 系列工具，LLM 可以**主动调用**去查/写记忆（例如 `agent_knowledge_recall`、`agent_knowledge_create_*`）。需要 `mcp` pip 包，在当前环境是离线安装的（见记忆 `hindsight-offline-mcp-install`）。

> 重点：**recall 的自动注入和 MCP 工具是两套独立的东西**。即使 MCP server 没装好，自动 recall/retain 依然工作（因为它只用 stdlib）。本环境的 `last_recall.json` 就是自动通道在工作的实证。

### 1.3 配置来源（当前实例）

配置**只放在项目级** `.claude/settings.json` 的 `env` 块（刻意不写全局 `~/.hindsight/claude-code.json`，避免污染）：

```jsonc
{
  "env": {
    "HINDSIGHT_API_URL": "http://10.83.11.134:8888",   // external 模式: 直连服务端, 不起本地 daemon
    "HINDSIGHT_API_TOKEN": "key-zhang3",               // Bearer token
    "HINDSIGHT_BANK_ID": "company1-project-alpha",     // 静态 bank (团队共享库)
    "HINDSIGHT_BANK_MISSION": "Company1 project alpha shared memory (zhang3)",
    "HINDSIGHT_AUTO_RECALL": "true",                   // 开 recall
    "HINDSIGHT_AUTO_RETAIN": "true",                   // 开 retain
    "HINDSIGHT_DEBUG": "true"                          // stderr 打调试日志
  }
}
```

加载顺序（`lib/config.py` 的 `load_config()`）：
```
内置默认值(DEFAULTS)  <  插件自带 settings.json  <  ~/.hindsight/claude-code.json(本环境无)  <  环境变量(env块)
```
**环境变量优先级最高**，所以 `env` 块里的 `HINDSIGHT_*` 覆盖一切。这也是为什么"只配 env 就够"。

---

## 2. Recall 过程：hindsight 如何影响 Claude Code 与 LLM 的交互

### 2.1 触发时机与连接方式

- **触发点**：Claude Code 的 `UserPromptSubmit` hook —— 即**用户按下回车提交一条 prompt 的那一刻**，在 prompt 被组装发给 LLM **之前**。
- **注册**（`hooks/hooks.json`）：
  ```json
  "UserPromptSubmit": [{ "hooks": [{ "type": "command",
    "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/recall.py\"",
    "timeout": 45 }] }]
  ```
- **进程模型**：Claude Code 每次提交 prompt，**临时起一个 `recall.py` 进程**，通过 stdin 喂给它一段 JSON，读 stdout 拿结果。进程是即起即灭的（ephemeral）——这也是为什么状态要落盘（见 retain 一节）。
- **API 解析**（`lib/daemon.py:get_api_url`）：本环境配了 `HINDSIGHT_API_URL`（external 模式），`get_api_url` 直接返回该 URL，**不会**尝试启动本地 daemon。即：recall 直接打 `http://10.83.11.134:8888`。

### 2.2 recall.py 的完整流程（逐行对应源码）

```
① 读 stdin 的 hook 输入 JSON
   字段: prompt(用户本次输入), session_id, transcript_path, cwd
   (recall.py:117-127)

② 若 autoRecall 关闭 → 直接 return，什么都不注入
   (recall.py:112)

③ 若 prompt 为空或长度 < 5 → 跳过（太短不值得召回）
   (recall.py:128)

④ 解析 API URL + 构造 HindsightClient(带 Bearer token)
   (recall.py:136-151)

⑤ 推导 bank_id
   静态模式(dynamicBankId=false, 本环境即此): 直接用 HINDSIGHT_BANK_ID
   = "company1-project-alpha"
   (lib/bank.py:125-128)

⑥ ensure_bank_mission: 首次使用某 bank 时, 把 mission 写进 bank 配置
   靠 state 文件 bank_missions.json 记"这个 bank 设过 mission 没"
   设过就跳过 —— 本环境已设, 见 state 实证
   (lib/bank.py:168-201)

⑦ 组装 recall 的 query
   - recallContextTurns 默认=1 → query 就是当前 prompt 本身
   - 若 >1: 读 transcript, 把最近 N 轮对话拼进 query(带"Prior context:"前缀)
   - 截断到 recallMaxQueryChars(默认800), 超长时优先保最新那轮
   (lib/content.py:compose_recall_query / truncate_recall_query)

⑧ 调 Hindsight recall API
   POST /v1/default/banks/{bankId}/memories/recall
   body: { query, max_tokens(默认1024), budget:"mid", types:["observation"], tags?... }
   Authorization: Bearer key-zhang3
   (lib/client.py:recall, recall.py:187-197)

⑨ 处理结果
   - 取 response.results[]
   - 可选: recallAdditionalBanks 跨库召回(本环境未配)
   - filter_by_min_scores: 按 score 阈值过滤(本环境未配阈值)
   - 没结果 → return, 什么都不注入(静默)
   (recall.py:202-243)

⑩ 格式化记忆为文本
   每条: "- <text> [<type>] (<mentioned_at>)"
   (lib/content.py:format_memories)

⑪ 拼成最终注入文本
   <hindsight_memories>
   <recallPromptPreamble>             ← 引导语,告诉LLM怎么用这些记忆
   Current time - 2026-09-29 06:52 UTC
   <memories...>
   </hindsight_memories>
   (recall.py:252-258)

⑫ 落盘 last_recall.json (诊断用, 不影响功能)
   (recall.py:261-269)

⑬ 输出 hook 结果给 Claude Code
   stdout 输出 JSON:
   {
     "hookSpecificOutput": {
       "hookEventName": "UserPromptSubmit",
       "additionalContext": "<上面的 hindsight_memories 文本>"
     }
   }
   (recall.py:272-278)

⑭ 退出码: 始终 0 (失败静默降级, 不阻塞用户)
   debug 模式下意外错误才 exit 2 暴露给 Claude
```

### 2.3 【核心】additionalContext 如何影响 LLM 调用

这是回答"recall 如何影响 Claude Code 与大模型交互"的关键：

**Claude Code 的 `UserPromptSubmit` hook 契约**：hook 进程在 stdout 返回的 JSON 里，若带 `hookSpecificOutput.additionalContext`，则 Claude Code 会把这段文本**作为额外上下文，拼接到本次发给 LLM 的请求里**——位置在用户实际 prompt 之前（作为 system/前置上下文的一部分）。

也就是说，对 LLM 而言，它收到的本次输入实际是：

```
[system prompt: 你是 Claude Code...]
[hindsight_memories]                    ← recall 注入的, LLM "以为"这是上下文的一部分
Relevant memories from past conversations...
Current time - 2026-09-29 06:52 UTC
- innodb_flush_log_at_trx_commit 取值决定 redo 刷盘强度... [observation] (...)
[/hindsight_memories]
[用户真正的 prompt: "insert 语句会记录 undo 吗?"]   ← 你这次问的
```

**影响机制小结**：
- recall **不修改模型、不修改 system prompt 的主体**，只在每次调用时**临时往输入里塞一段记忆文本**。
- LLM 是否采纳这段记忆，由模型自己决定（preamble 明确说"Only use memories that are directly useful; ignore the rest"）。
- 注入是**每次 prompt 都做**（不是只在会话开头），所以随着对话推进，每轮都能召回不同的相关记忆。
- **延迟代价**：每次提交 prompt 都要同步等一次 HTTP recall（timeout 10s，但通常几百 ms）。hook 级 timeout 设 45s。recall 失败则**不注入**，用户无感（exit 0 降级）。

### 2.4 recall 的几道"安全/防呆"设计

1. **prompt 太短（<5 字符）不召回**——避免无意义查询。
2. **失败静默降级**——recall 挂了不影响用户正常用 Claude Code，最多就是没注入记忆。
3. **记忆来自服务端的语义检索**——不是把整个库倒进来，而是按当前 prompt 做向量+关键词混合召回，只返回 top 相关的几条（受 `max_tokens`/`budget` 控制）。
4. **preamble 引导**——明确告诉 LLM "冲突时优先用最近的、只取有用的"，防止旧记忆污染判断。

### 2.5 实证：本环境真的在注入

`~/.claude/plugins/data/hindsight-memory/state/last_recall.json` 内容（节选）：
```json
{
  "context": "<hindsight_memories>\nRelevant memories from past conversations...\n
   Current time - 2026-09-29 06:52 UTC\n\n
   - innodb_flush_log_at_trx_commit 取值决定 redo 刷盘强度: 1(默认)=每次提交都 fsync... [observation]\n
   ...",
  "saved_at": "2026-09-29T06:52:..Z",
  "bank_id": "company1-project-alpha",
  "result_count": <N>
}
```
这条记忆正是**之前某次会话 retain 进去的**内容，现在被 recall 拿出来注入了——证明 recall↔retain 闭环是通的。

---

## 3. Retain 过程：内容如何自动写入 Hindsight

### 3.1 触发时机

- **触发点**：Claude Code 的 `Stop` hook —— 即**模型回答完一轮、停下来的时候**（不是会话结束）。
- **注册**：
  ```json
  "Stop": [{ "hooks": [{ "type": "command",
    "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/retain.py\"",
    "timeout": 15,
    "async": true }] }]
  ```
  **`async: true` 是关键**：Claude Code 不等 retain.py 跑完就继续，retain 在后台默默执行——所以用户感觉不到延迟，retain 对当前 LLM 交互**完全透明**。
- **额外触发**：`SessionEnd` hook 调 `session_end.py`，会以 `force=True` 触发一次最终 retain（保证会话结束前把剩余内容存进去）。本环境 `turns.json`/`retention_tracking.json` 当前为空，是因为本会话还没满足触发节奏（见下）。

### 3.2 retain.py 的完整流程

```
① 读 stdin hook 输入: session_id, transcript_path, cwd
   (retain.py:249-255)

② 若 autoRetain 关闭 → return
③ 读 transcript_path 这个 JSONL 文件, 拿到全部 messages
   Claude Code 的 transcript 格式: 每行一个 JSON, 形如
     {type:"user", message:{role:"user", content:"..."}, uuid:"..."}
   (retain.py:read_transcript, 38-69)

④ 节奏控制: retainEveryNTurns(默认 10)
   - increment_turn_count(session_id) 把计数器+1
   - 若 turn_count % 10 != 0 → 本次不真正 retain, 直接 return
   (retain.py:101-106, lib/state.py:increment_turn_count)
   ※ Stop 每轮都触发 hook, 但不是每轮都真写——靠这个节流

⑤ 增量切分: 只发"上次 retain 之后新增"的消息
   - plan_retention(session_id, 当前消息总数)
     读 retention_tracking.json 里该 session 上次记的 message_count
     - 若 transcript 变长了: start_index=上次count, chunk+1, 只发后缀
     - 若 transcript 变短了(=被 Claude Code 压缩/compact 了):
       chunk+1, start_index=0, 把压缩后的整段当新 chunk 发
     - 若没变: start_index=总数 → 无新消息, 跳过
   (lib/state.py:plan_retention, retain.py:128-145)
   ※ 这是"增量写入"的核心, 避免每次都全量重发

⑥ document_id 策略
   - chunk 0: 用 session_id 本身
   - 后续 chunk: session_id-c1, session_id-c2, ...
   ※ 不能复用 document_id——服务端同 id 会"替换"而非"追加"
   (retain.py:140)

⑦ 格式化 transcript
   - 默认 retainToolCalls=false → 纯文本格式 [role: user]...[user:end]
   - true → JSON 格式, 含 tool_use/tool_result 结构
   - 关键: strip_memory_tags —— 把 <hindsight_memories> 块删掉!
     防止"recall 注入的记忆"又被原样 retain 回去, 形成反馈循环
   - strip_channel_envelope: 剥掉 channel 消息的 XML 外壳
   - 过滤 operational tool (recall/retain/search 等 MCP 工具调用不存)
   (lib/content.py:prepare_retention_transcript / strip_memory_tags)

⑧ 解析 API URL(同 recall, external 模式直连)
   ※ 注意: retain 的 allow_daemon_start=true, recall=false
     ——理论上 retain 若无 external URL 会尝试起 daemon, 本环境不触发

⑨ 推导 bank_id + ensure_bank_mission(同 recall)

⑩ 组装 tags/metadata(支持 {session_id}/{bank_id}/{timestamp}/{user_id} 模板)

⑪ POST 到 Hindsight retain API
   POST /v1/default/banks/{bankId}/memories
   body: {
     items: [{
       content: <格式化后的 transcript>,
       document_id: <session_id 或 session_id-cN>,
       context: "claude-code",          ← 标记来源
       metadata: {retained_at, message_count, session_id, ...},
       tags: [...]
     }],
     async: true                         ← 服务端异步处理(向量化/抽取)
   }
   (lib/client.py:retain, retain.py:232-241)

⑫ 成功后 commit_retention: 把"本次已存到第几条"写回 retention_tracking.json
   ※ 失败则不 commit → 下次会重试这批没存成功的消息
   (lib/state.py:commit_retention, retain.py:242-243)

⑬ 退出码: 始终 0 (失败静默)
```

### 3.3 【核心】retain 是不是"自动触发写入"？—— 是，但有节流

回答用户的问题"相关内容是自动触发写入到 hindsight 中的"：

**是的，自动触发**，但不是"每说一句话就写一次"，而是：

1. **触发源**：模型每回答完一轮（`Stop`），自动起 `retain.py`，无需用户/LLM 主动操作。
2. **节流**：默认 `retainEveryNTurns=10`，即每 10 轮才真正发一次 retain 请求（前 9 次 hook 被计数器跳过）。这是为了避免频繁写库开销。
3. **增量**：真正写的时候，只写"上次之后新增的消息"，不是全量重发。
4. **异步**：`async:true`（hook 侧）+ `async:true`（服务端 body）双重异步——hook 不阻塞 Claude Code，服务端收到后后台慢慢做向量化/抽取。
5. **会话结束兜底**：`SessionEnd` 时 `force=True` 强制把剩余未存的消息存掉。

**所以 retain 对 LLM 交互是零影响的**：它发生在回答结束之后、后台执行、不参与当前这轮 prompt/回答的构造。它的产物（向量化后的记忆）要等**未来某次会话的 recall** 才会被用上。

### 3.4 服务端做了什么（retain 之后）

插件只负责把 transcript 文本 POST 过去。服务端（Hindsight）收到后会（这是黑盒，但从 API 行为可推断）：
- 对文本做 **embedding（向量化）**
- 用 LLM **抽取**出结构化的"记忆条目"（类型如 `observation`，这也是 recall 默认召回 `types:["observation"]` 的原因）
- 存入该 bank 的向量库 + 关键词索引，供未来 recall 的混合检索

`context:"claude-code"` 和 `metadata` 帮助服务端按来源/会话聚类和过滤。

### 3.5 防反馈循环的关键设计

这是工程上很重要的一点，源码里反复处理：

- **recall 注入用的是 `<hindsight_memories>` 标签**；**retain 时 `strip_memory_tags` 会把这两个标签块整体删掉**（`<hindsight_memories>` 和 `<relevant_memories>`）。
- 否则就会出现：上一轮 recall 注入的记忆 → 进入 transcript → 本轮 retain 又把它存回去 → 下轮 recall 再召回 → 雪球越滚越大。
- 同时还会过滤掉 `mcp__` 开头的操作型工具调用（recall/retain/search/CRUD 等），只保留**对话性内容**。

---

## 4. 两个过程的对照与闭环

### 4.1 recall vs retain 全对比

| 维度 | Recall | Retain |
|------|--------|--------|
| 方向 | 读（从 Hindsight 取） | 写（往 Hindsight 存） |
| hook | `UserPromptSubmit` | `Stop` (+ `SessionEnd` 兜底) |
| 时机 | prompt 提交**前** | 回答结束**后** |
| 同步性 | **同步**（要等结果才能拼 prompt） | **异步**（`async:true`，不阻塞） |
| 节流 | 无（每次 prompt 都召回） | `retainEveryNTurns=10` |
| 增量 | 不适用（每次都是新 query） | 增量（只发新消息，靠 `retention_tracking.json`） |
| 对 LLM 影响 | **有**（`additionalContext` 注入本次输入） | **无**（纯后台，本次调用不感知） |
| 失败行为 | 静默不注入，exit 0 | 静默不写入，exit 0，不 commit |
| API | `POST .../memories/recall` | `POST .../memories`（`async:true`） |
| 状态文件 | `last_recall.json`（诊断） | `turns.json` + `retention_tracking.json` + `bank_missions.json` |

### 4.2 闭环示意

```
会话 A (过去)
  用户提问 → [recall: 召回更早的记忆注入] → LLM 回答
              → [Stop: retain] → transcript 存入 Hindsight → 服务端向量化/抽取
  ... 会话结束 [SessionEnd: force retain 剩余]

        ↓ Hindsight bank 里现在有了会话A的记忆

会话 B (未来, 可能是另一个 session/另一天)
  用户提问 → [recall: 用本次 prompt 去召回]
              → 命中会话A存进去的记忆 → 注入 <hindsight_memories>
              → LLM 回答时"记得"会话A的内容
```

**这就是"长期记忆"的本质**：单次会话内，LLM 的上下文是会话级的（受 context window 限制会丢）；hindsight 把跨会话的内容沉淀下来，在新会话里按相关性召回注入，**绕过了 context window 的遗忘问题**。

### 4.3 当前实例的状态文件实证

`~/.claude/plugins/data/hindsight-memory/state/`：
```
bank_missions.json        {"company1-project-alpha": true}   ← mission 已设(首次使用时写的)
last_recall.json          6663 字节, 含真实记忆内容            ← recall 确实跑过且注入了
turns.json                (空)                                ← 本会话未达 retain 节奏
retention_tracking.json   (空)                                ← 本会话还未真正 retain 过
```
这完全符合预期：recall 每轮都在跑（有 last_recall），retain 因为节流（每 10 轮）且本会话轮数还少，还没真正写入——但机制是 ready 的。

---

## 5. 把它对应到 ContextDB 的概念

ContextDB 的诉求是"为 Agent 提供持久化、可检索、按需注入的上下文"。hindsight 的这套机制恰好是一个**最小可用的 ContextDB 实现**：

| ContextDB 概念 | hindsight 对应 |
|---------------|----------------|
| 上下文存储 | bank（`company1-project-alpha`），服务端向量库 |
| 写入（沉淀） | retain hook（自动，Stop 触发） |
| 检索（召回） | recall API（语义+关键词混合检索） |
| 注入（提供给 LLM） | `additionalContext`（UserPromptSubmit 注入） |
| 隔离/命名空间 | bank_id（静态或按 agent/project/session 动态） |
| 去重/防污染 | `strip_memory_tags` + 增量 retain + score 过滤 |
| 多用户/团队共享 | 同一 bank_id 即共享（本实例正是团队库） |

**基于 hindsight 实现 ContextDB 功能的要点**：
1. **存储与检索交给 Hindsight 服务端**，Claude Code 侧只做"接入"——不重复造向量库。
2. **接入方式是 hook，不是改 Agent 代码**——这是它能"无侵入"接入 Claude Code 的关键，也意味着同样的模式可复用到任何支持 hook/拦截机制的 Agent。
3. **recall 是"按需注入"而非"全量灌入"**——每次只召回与当前 prompt 相关的少量记忆，控制了对 context window 的占用和噪声。这符合 ContextDB"按需供给上下文"的理念。
4. **retain 是"自动沉淀"而非"手动标注"**——Agent 不用显式"记笔记"，对话自然流淌即被沉淀。代价是：存的是原始对话，质量依赖服务端的抽取能力。

### 5.1 当前实现的局限（值得在 ContextDB 设计中考虑）

1. **recall 的相关性质量取决于服务端**——客户端只发 query、收 results，召回准不准是黑盒。`recallMinScores` 提供了客户端侧兜底过滤，但本环境未配。
2. **retain 是全量对话沉淀，非结构化**——虽然有 `strip_memory_tags` 等清洗，但本质还是把对话原文丢给服务端抽取。如果服务端抽取/向量化质量一般，recall 就会召回噪声。ContextDB 若要更精准，可能需要在 retain 前做更结构化的提炼（hindsight 也提供了 MCP `agent_knowledge_create_*` 工具走"手动精写"路线，与自动 retain 互补）。
3. **节流可能丢内容**：`retainEveryNTurns=10` 意味着如果会话在第 5 轮 crash 且没到 SessionEnd，那 5 轮内容可能没存。SessionEnd 的 force retain 是兜底，但 crash 场景仍可能丢。
4. **每轮 prompt 的同步 recall 延迟**：虽然通常几百 ms，但 recall 服务慢时会拖慢用户每次提交（hook timeout 45s）。ContextDB 设计中需考虑 recall 的超时与降级（hindsight 已做：失败静默）。
5. **注入位置是"前置上下文"，受 LLM 服从性影响**：LLM 可能忽略 `<hindsight_memories>`。preamble 是软约束，不是强约束。
6. **多 bank / 跨项目隔离**：当前用静态 bank（团队共享一个库）。若要按项目隔离，可开 `dynamicBankId=true` + `dynamicBankGranularity=["agent","project"]`，bank_id 会按 `agent::project` 自动组合——这是 ContextDB 做"上下文命名空间"的现成机制。

---

## 6. 调试与验证方法（便于后续排查）

1. **看 recall 是否工作**：查 `~/.claude/plugins/data/hindsight-memory/state/last_recall.json`，有内容说明 recall 跑过。
2. **看 retain 节奏**：查同目录 `turns.json`（当前轮计数）和 `retention_tracking.json`（已存到第几条）。
3. **看 mission 是否设了**：查 `bank_missions.json`。
4. **开调试日志**：`HINDSIGHT_DEBUG=true`（本环境已开），`recall.py`/`retain.py` 会把每步打到 stderr，Claude Code 会显示。
5. **手测 API**：
   ```bash
   # recall
   curl -X POST http://10.83.11.134:8888/v1/default/banks/company1-project-alpha/memories/recall \
     -H "Authorization: Bearer key-zhang3" -H "Content-Type: application/json" \
     -d '{"query":"insert undo","max_tokens":1024,"budget":"mid","types":["observation"]}'
   ```
6. **注意加载的是缓存副本**：插件实际从 `~/.claude/plugins/cache/hindsight/hindsight-memory/0.7.5/` 加载，**不是**源码目录 `/rri/.../hindsight/hindsight-integrations/claude-code/`。改源码后需 `claude plugin update hindsight-memory` 才生效（见记忆 `hindsight-offline-mcp-install`）。

---

## 7. 附：关键源码文件索引

| 文件 | 作用 |
|------|------|
| `hooks/hooks.json` | 注册 4 个 hook 到 Claude Code |
| `.claude-plugin/plugin.json` | 插件清单（name/version） |
| `.mcp.json` | 注册 MCP server（手动通道） |
| `scripts/recall.py` | **recall 主流程**（UserPromptSubmit） |
| `scripts/retain.py` | **retain 主流程**（Stop） |
| `scripts/session_start.py` / `session_end.py` | 会话起止处理（SessionEnd 会 force retain） |
| `scripts/mcp_server.py` | MCP server，暴露 `agent_knowledge_*` 工具 |
| `scripts/run_mcp.sh` | MCP server 启动器（含 venv/pip bootstrap） |
| `scripts/lib/config.py` | 配置加载（DEFAULTS + env 覆盖） |
| `scripts/lib/client.py` | HindsightClient（recall/retain/set_bank_mission API） |
| `scripts/lib/bank.py` | bank_id 推导 + mission 设置 |
| `scripts/lib/state.py` | 文件状态机（turns/retention_tracking/bank_missions，含 flock） |
| `scripts/lib/content.py` | transcript 格式化、strip_memory_tags、记忆格式化 |
| `scripts/lib/daemon.py` | API URL 解析（external/local/daemon 三模式） |

---

> **一句话收束**：hindsight 通过 Claude Code 的 `UserPromptSubmit`/`Stop` 两个 hook，在"读"侧把历史记忆以 `additionalContext` 注入每次 LLM 调用、在"写"侧把会话 transcript 异步增量沉淀到向量库，构成了一个 recall↔retain 的闭环长期记忆系统——这正是"基于 hindsight 实现 ContextDB 功能"的机制内核。
