# 调研源报告：国际云厂商 Agent 记忆托管服务（AWS/Google/Anthropic/OpenAI）

> 来源：夜间任务调研 agent 4（2026-10-08 执行）
> 方法：WebFetch/curl 直接抓取官方页面（WebSearch 故障兜底），OpenAI 公告经 Wayback Machine 存档验证，全部访问于 2026-10-08
> 用途：`hindsight/competitive-differentiation/` 系列文档的原始输入

---

# 国际云厂商 Agent 记忆托管服务竞品调研（2026-10-08）

**说明**：WebSearch 工具在本次会话不可用（API 400），全部证据通过 WebFetch/curl 直接抓取官方页面获得，访问日期均为 2026-10-08；OpenAI 公告经 Wayback Machine 存档验证。

## 一、AWS Bedrock AgentCore Memory

**定位**【官方文档】：全托管服务，短期记忆（session 内事件流）+ 长期记忆（跨 session 抽取记录）。来源：https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html

**API 形态**【已确认】：已从 2025 年预览版演化为双平面：控制面（bedrock-agentcore-control）`CreateMemory/UpdateMemory/GetMemory/ListMemories/DeleteMemory`；数据面 `CreateEvent/GetEvent/ListEvents/ListSessions/ListActors`、`BatchCreateMemoryRecords/BatchUpdateMemoryRecords/BatchDeleteMemoryRecords`、`GetMemoryRecord/ListMemoryRecords`、`RetrieveMemoryRecords`（语义检索）、`StartMemoryExtractionJob`、`IngestData`。来源：https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_Operations.html。**预览版的 StoreConversationEvent/RetrieveMemories/GenericMemoryRecord 在当前 API 参考中已不存在**——记录模型改为通用 `MemoryRecord`（content≤16KB 文本 + namespace + metadata + memoryStrategyId），无强类型 record。

**策略**【官方文档】：`MemoryStrategyInput` 联合类型：`semanticMemoryStrategy`（事实抽取）、`userPreferenceMemoryStrategy`、`summaryMemoryStrategy`（XML topic 分块）、`episodicMemoryStrategy`（episode+reflection，跨片段洞察）、`customMemoryStrategy`。三档执行模式：**built-in**（全自动、存储贵）、**built-in overrides**（自定义 prompt、模型在客户账户调用）、**self-managed**（完全自管线）。来源：https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-strategies.html 及 devguide/API_CreateMemory.html

**定价**【已确认】（https://aws.amazon.com/bedrock/agentcore/pricing/）：短期记忆摄入 **$1.00/GB**（2026-10-06 起生效，此前为 $0.25/千事件——两天前刚改为按 GB）；检索 $0.20/GB；存储 $0.10/GB-月；单事件计费下限 12KB/上限 64KB。长期记忆：built-in **$0.75/千记录/月**，override/self-managed **$0.25/千记录/月**（模型费自理）；检索 $0.50/千次。

**企业特性**【官方文档】：KMS CMK（encryptionKeyArn）、事件 TTL（eventExpiryDuration）、跨账户访问、namespace 校验（allowedValues/regex）；注意事件 metadata 不被 CMK 加密。**区域列表**：【未能验证】（静态文档无清单，示例默认 us-west-2）。

## 二、Google：Gemini Enterprise Agent Platform Memory Bank

**重大变化**【已确认】：Vertex AI 平台已整体更名 **Gemini Enterprise Agent Platform**（来源：https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes），Memory Bank 归入其 "Scale" 板块（与 Agent Runtime、Sessions、Feedback 并列），是原 Vertex AI Agent Engine 记忆能力的延续。

**API 形态**【官方文档】（https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank 及 api-quickstart）：Agent Platform SDK——`client.memory_banks.create()`、`client.sessions.events.append()`、`client.memory_banks.memories.generate()`（支持 `vertex_session_source` 会话源 / `direct_memories_source` 预抽取 facts / `CreateMemory` 直写不合并）、`RetrieveMemories`（全量+相似度检索）。记忆以 `{"scope": {"user": ...}, "fact": ...}` 对象存储，scope 最多 5 个 KV 做身份隔离；资源挂在 reasoningEngines 路径下。ADK 内置 `VertexAiMemoryBankService` 工具（memory-as-a-tool），另有 LangGraph 集成。**非 generate_content 内嵌**，是独立 API+SDK+ADK 工具三层。

**抽取**【官方文档】：默认模型 **gemini-3.5-flash**；`managed_memory_topic` 枚举（USER_PERSONAL_INFO/USER_PREFERENCES/KEY_CONVERSATION_DETAILS 等）+ few-shot 自定义；异步生成、批量事件摄取自动触发、记忆合并（consolidation）、revision 历史、TTL、多模态。

**定价**【已确认】（https://cloud.google.com/products/gemini-enterprise-agent-platform/pricing）：2026-09-01 起按此结构计费——存储（含 revisions）**$0.30/GiB-月**（Agent Storage SKU，首 1GiB 免费档）；读操作 1 Agent Compute vCPU-h（$0.085）/300 万次；写操作 1 vCPU-h/100 万次；**抽取与嵌入 token 按模型 SKU 另计**。Scale 产品统一按 Compute/Memory/Storage 三资源计费。

**治理**【官方文档】：IAM 角色 aiplatform.memoryUser/memoryViewer/memoryEditor + IAM Conditions 限制 scope 读写；区域实例（us/eu/global），CMEK 不支持 global 端点；明确提示记忆投毒（memory poisoning）风险，建议 Model Armor 检查。

## 三、Anthropic：不做托管服务，给 client-side 工具

**Memory tool**【官方文档】（https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool）：`{"type": "memory_20250818", "name": "memory"}`，六命令 view/create/str_replace/insert/delete/rename，`/memories` 前缀由**客户端映射到自己的存储**（文件/DB/对象存储均可）；Claude 4+ 全模型可用；启用后 API 自动注入 "MEMORY PROTOCOL" 系统提示；官方文档明确路径穿越、敏感信息、容量上限、过期清理**全部是客户端责任**。与 context editing/compaction 组成长程 agent 方案。

**Claude Code auto memory**【官方文档】（https://code.claude.com/docs/en/memory）：`~/.claude/projects/<project>/memory/` 下 MEMORY.md 索引+主题文件，四类记忆（user/feedback/project/reference），每会话自动加载前 200 行/25KB，机器本地不跨设备。

**Claude 产品端 memory**【已确认】（https://claude.com/blog/memory，2025-09-11）：Claude app 内置记忆，Team/Enterprise 起步，project 级独立记忆，memory summary 可查看/编辑，Incognito chat，支持跨 AI 工具导入/导出。

## 四、OpenAI：记忆是产品功能，不是 API

**ChatGPT Memory**【已确认，Wayback 存档】（https://openai.com/index/memory-and-new-controls-for-chatgpt/，2025-02-13 发布）："saved memories" + "chat history 引用"双层机制，2025-09-05 扩展至 Free/Plus/Team/Enterprise，Temporary Chat 可关闭。**API 侧无托管记忆服务**【已确认】：developers.openai.com 文档索引（https://developers.openai.com/api/docs/llms.txt）中无任何 memory 条目；仅提供 Conversations API、`previous_response_id` 链式状态、Agents API 的 session state 与 Files（https://developers.openai.com/api/docs/guides/conversation-state）。

## 五、对比与对 ContextDB 的 5 条启示

**范式对比**：AWS=事件流+策略抽取+通用记录（记录式，Extract→Consolidate→(Reflect)）；Google=会话事件+LLM 生成合并 fact 对象（生成式，topics 约束）；Anthropic=工具式（文件命令协议，存储归客户端）；OpenAI=仅状态保持。**定价对比**：AWS 按 GB 摄入/存储/检索+按记录数+按检索次数，抽取成本内化（built-in 存储贵 3 倍）；Google 按存储 GiB+读写次数折算 vCPU-h+模型 token 单列。**企业门槛**：双方均强调 CMK/CMEK、租户隔离、数据驻留、记忆投毒防护。

对华为云 ContextDB 的启示：

1. **对齐"双平面+事件模型"API 范式**：控制面（建库/配策略）+数据面（写事件/语义检索），actorId/sessionId/namespace 组织记忆——这是 AWS/Google 收敛出的共识形态，对齐可降低客户迁移成本。
2. **策略分档+抽取成本显性化**：托管抽取（贵）/自带模型 override（中）/纯存储自管线（便宜）三档定价；抽取 token 费用务必单列（Google 做法），避免重资产免费抽取拖垮毛利。
3. **把隔离与治理做成卖点**：scope/namespace 级 IAM、区域驻留、记忆投毒检测（对标 Model Armor）是企业采购硬门槛，也是差异化机会。
4. **记忆+会话+知识库成套卖**：两家均将 Memory 与 Sessions/RAG/Vector Search 同平台捆绑；ContextDB"记忆+知识库一体化"定位正确，还应补齐 session 管理与向量检索的套件感。
5. **兼容"协议优先"生态**：Anthropic/OpenAI 证明 memory tool 协议正在成为事实标准——ContextDB 应可直接充当 Claude memory tool 的 `/memories` 后端及对接 ADK 等框架，以"托管后端+标准协议"双形态进入存量生态。

---

**主要来源**（均访问于 2026-10-08）：docs.aws.amazon.com（bedrock-agentcore devguide memory、memory-strategies、API_Operations、CreateMemory、pricing）；docs.cloud.google.com（gemini-enterprise-agent-platform：vertex-ai-name-changes、scale/memory-bank、api-quickstart）与 cloud.google.com（pricing）；platform.claude.com（memory tool）、code.claude.com（memory）、claude.com/blog/memory；openai.com（memory-and-new-controls-for-chatgpt，Wayback 验证）、developers.openai.com（llms.txt、conversation-state）。
