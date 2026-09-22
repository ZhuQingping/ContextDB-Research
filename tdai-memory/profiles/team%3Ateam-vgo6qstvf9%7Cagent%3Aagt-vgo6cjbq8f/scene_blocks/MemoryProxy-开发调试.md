-----META-START-----
created: 2026-09-22T06:43:34.016Z
updated: 2026-09-22T09:55:32.014Z
summary: zhuqingping 开发 MemoryProxy（TypeScript 代理：请求/用量日志、session key isolation、memory injection、writeL0 会话录制）与 MemoryPanel；2026-09-22 06:35-07:25 持续巡检：审阅 types.ts 三类日志接口、metadata.db 资产记录、chat-memory 路由，追踪 session 8f75421c 的 session-init bypassed（L2a hit/pending_asset_confirm/choice=false），跨 MemoryCore/MemoryProxy 两库追踪 preset-identity bypass（x-team-id/x-agent-id/x-task-id 预选择、onMismatch、直接注册），实测 /v3/meta/agent/create 发现 glm-5.3-flash 10 token 即 max_tokens 截断；09:11 记忆侧确认 MemoryCore 以 provider=proxy 经 ${baseUrl}/proxy/<iid>/v1 + TDAI_MEMORY_SYSTEM_USER_KEY 调用本代理（LLM provider 级集成落地）；09:55 补记：MemoryCore 侧 llmRunner 路径自带 model 且忽略 memory.extraction.model，该参数仅对 fallback 路径生效——provider=proxy 意味着 model 由 runner/代理路径决定，配置声明的模型参数与实际生效路径脱节。
heat: 9
-----META-END-----

## 用户基础信息
- 用户名：zhuqingping
- 职业：开发者，同时负责两个记忆相关项目：腾讯云 TencentDB ContextDB（memory-tdai，见另一场景文件）与 MemoryProxy
- MemoryProxy：TypeScript 代理，含请求/用量日志、会话键隔离（session key isolation）、记忆注入（memory injection）模块、session-init/注入流水线，以及 writeL0 会话录制路径（client.addConversation 将对话 POST 到 /v3/conversation/add，分块批量写入）；已被 MemoryCore 以 provider=proxy 方式作为 LLM 出口：baseUrl 运行时改写为 ${baseUrl}/proxy/<iid>/v1，鉴权用 TDAI_MEMORY_SYSTEM_USER_KEY 系统密钥。llmRunner 路径自带 model、忽略 memory.extraction.model（该参数仅对 fallback 生效）——MemoryCore LLM 调用存在双路径 model 解析
- 配套 MemoryPanel（chat-memory 路由：team-assets / agent-fixed / patch-scope 等）；对两者源代码及元数据数据库 metadata.db 均有直接访问与操作权限

## 用户核心特征
用户横跨记忆系统生产端（ContextDB memory-tdai）与消费端（MemoryProxy 注入代理），工程风格是接口契约、运行时观测与落库核验的闭环：以 types.ts 日志接口为审阅锚点，靠 injection-debug 日志观察注入行为，下探 metadata.db 验证存储层，追运行时日志定位真实案例；同一机制（如 session-init preset-identity bypass）会横跨 MemoryCore 与 MemoryProxy 两个代码库连续追踪，并以 API 实测取证，不停留在静态审阅。

## 用户偏好
- 代码审阅以模块为单位连续展开：一次会话内浏览 types.ts、anthropicHandler.ts、handler.ts 多个源文件
- 重视日志数据结构（RequestLogEntry/UsageLogEntry/AnalyzerUsageLogEntry），以结构化日志支撑请求/用量分析
- 关注 sessionKey/conversationId 的语义与流向
- 验证不止于代码：直接检查 metadata.db 表结构与资产记录，并经 API 实测（create-agent）捕获响应元数据（stop_reason、output tokens）取证
- 排查注入问题以具体 session 为线索，顺日志追踪到分支决策点

## 隐性信号
- 06:35-07:25 一次会话内完成"接口层→数据库层→路由层→运行时"纵向巡检，随后又把同一 bypass 问题扩展到 MemoryCore 代码库——他在对"身份预选→注入"机制做跨库统一审视，两项目集成正从接口对接走向机制层对齐。
- 追踪 'session-init bypassed → skipping all injection'（session 8f75421c，L2a hit、pending_asset_confirm、choice=false）后继续深挖 preset-identity bypass（x-team-id/x-agent-id/x-task-id 头驱动预选择、onMismatch bypass、直接注册）：他怀疑身份预选/确认门控是注入被跳过的根源，排查正沿此收窄。
- MemoryCore 侧确认 provider=proxy 解析（${baseUrl}/proxy/<iid>/v1、TDAI_MEMORY_SYSTEM_USER_KEY）：代理已进入 MemoryCore 生产调用链，按 iid 分流 + 独立系统密钥——跨项目集成从机制审视进入运行时耦合，<iid> 与 header 驱动的身份预选（x-team-id/x-agent-id/x-task-id）如何衔接值得追踪。
- create-agent 实测中 glm-5.3-flash 的 assistant 响应仅 10 output tokens 即 stop_reason=max_tokens：或是有意的小预算探针，也可能暴露 create-agent 流程 max_tokens 配置过低/未传；按其顺异常追根的习惯，大概率会跟进。
- writeL0 录制侧（recorder.ts extractLatestUserMessage/recordTdaiTurn）只提取真实用户查询、避免 harness 噪音污染 L0：L0 数据洁净责任前置到录制入口，与其"L0 质量决定 L1/L2 提取质量"的链路质量观一致。
- client.addConversation 采用分块批量 POST：关注大量对话场景的吞吐与可靠性，批量写入的失败重试/幂等或是后续关注点。
- 注入流水线存在 SIDEQUERY/FORK/MAIN 三分支：注入策略按会话语境分流，多获取路径的作用域取舍仍是设计焦点。

## 核心叙事
2026-09-22 06:35-07:25 UTC，刚完成 ContextDB memory-tdai 全链路调试收尾（**触发**），用户对 MemoryProxy 生态做连续巡检：06:35-06:38 系统性浏览 sessionKey/conversationId 相关代码（types.ts 三类日志接口、anthropicHandler.ts/handler.ts 注入调试日志），06:38-06:40 下探 metadata.db 核对表结构与 agents/teams/chat_memory 资产记录，并审阅 MemoryPanel 的 team-assets/agent-fixed/patch-scope 等路由；06:41-06:47 转入运行时排查，追踪 session 8f75421c-91f4-4007-9d20-b2ecae331d6a 的 'session-init bypassed → skipping all injection' 日志（L2a hit、pending_asset_confirm、choice=false），并审阅 writeL0 录制代码（client.ts 分块批量 POST /v3/conversation/add、recorder.ts 只提取真实用户查询防 harness 噪音污染 L0）与 SIDEQUERY/FORK/MAIN 注入分支（**行动**）。07:23-07:25 继续同一调查：跨 MemoryCore 与 MemoryProxy 两库追踪 session-init preset-identity bypass 代码——header 驱动预选择（x-team-id/x-agent-id/x-task-id）、onMismatch bypass 处理与直接注册，随后经 /v3/meta/agent/create 实测建 agent，捕获 glm-5.3-flash 的响应在仅 10 output tokens 时即 stop_reason=max_tokens（**行动→结果**）。至此他拿到注入被跳过的真实案例、跨库 bypass 机制图谱与一个实测异常，为注入修复与两项目身份机制对齐奠定基础。09:11 补记：MemoryCore 侧确认 provider=proxy 时 baseUrl 改写为 ${baseUrl}/proxy/<iid>/v1 并使用 TDAI_MEMORY_SYSTEM_USER_KEY——MemoryProxy 已成为 MemoryCore 的 LLM 出口，集成由"机制对齐"进入"运行时耦合"。

## 待确认/矛盾点
- 'session-init bypassed' 根因：pending_asset_confirm + choice=false 是预期的资产确认门控，还是确认链路未走通？onMismatch bypass 与 preset-identity 预选择在其中的角色待澄清。
- create-agent 测试中 10 token 即 max_tokens：是请求侧 max_tokens 配置过低/未传，还是有意的小预算探针？
- 注入日志的 'L2a' 与 ContextDB L2 场景块是否同一数据源；与 metadata.db 的 chat_memory 资产是一套还是两套存储，待澄清。
- SIDEQUERY/FORK/MAIN 三分支的触发条件与各自注入策略差异待梳理。
- 本次排查的后续动作（是否修复 bypassed、是否调整 pending_asset_confirm/max_tokens 配置）待观察。
