# 调研源报告：WeKnora 深度调研

> 来源：夜间任务调研 agent 1（2026-10-08 执行）
> 方法：GitHub API + 官方文档站 weknora.weixin.qq.com/docs/ 实际抓取
> 用途：`hindsight/competitive-differentiation/` 系列文档的原始输入，结论以主文档引用为准

---

# WeKnora 竞争调研报告（所有来源均于 2026-10-08 实际抓取验证）

## 1. 项目基本面【已确认】
- **32,413 stars / 4,315 forks / 582 open issues**，建仓 2025-07-22，最后推送 2026-10-07（前一天）；近 90 天提交 ≥1000；贡献者 >100 人，首位 `lyingbug` 独占 2111 commits——企业全职团队驱动的项目，甚至有 `claude` 账号参与 28 次提交。（来源：api.github.com/repos/Tencent/WeKnora 及 /commits、/contributors）
- 主语言 Go（23.5MB），Vue3+TS 前端，Python 解析服务；**MIT 许可**（LICENSE 含第三方条款）。发版 v0.1.2（2025-09）→ v0.8.2（2026-09-24）共 40 个 release，节奏约 2–6 周一版。15 个月 32k stars，增速超过同期绝大多数 RAG 项目。

## 2. 架构与核心能力【已确认】
- **形态**：Go 单体（gin+gorm+dig+asynq）+ Vue3 + Python docreader（gRPC 微服务，流式返回防大 PDF 撑爆内存）；默认 PostgreSQL/ParadeDB 同库提供 pgvector+BM25，Redis 做队列与 SSE 流；另有 Lite 单二进制（SQLite+sqlite-vec）和桌面版。RAG 链路是**事件驱动插件管线**（意图识别→改写→实体抽取→记忆召回→并行混合检索→图谱检索→重排[含 WikiBoost、**MemoryAffinity**]→合并→生成），SSE 断线续传、支持多副本。
- **解析**：25+ 格式；引擎可按文件类型切换：builtin / MarkItDown / OpenDataLoader（版面分析）/ **MinerU**（PDF）/ **PaddleOCR-VL**（OCR）/ anydoc（进程内 Office）；VLM 图片描述、ASR。混合检索为**上层统一 RRF 融合**，后端只需各自提供单模检索；10 种向量后端，可按知识库绑定存储实例（带懒重建/singleflight）。
- **知识图谱**：Neo4j+APOC 的 GraphRAG，按库开关，LLM few-shot 配置向导（自动生成示例与标签），逐 chunk 异步抽取（独立队列，文档自称"管线中最昂贵的扇出"），OCR 文本也入图。
- **多租户**：工作空间四级 RBAC、按库所有权、Organization 跨空间只读共享、带能力范围的 API Key、OIDC、审计日志、AES-256-GCM 凭证加密、配额。
- **Agent/MCP**：quick-answer（RAG）与 smart-reasoning（ReAct）双模式+类型预设；内置 **MCP Server**（每空间 `/mcp/<id>` 端点，独立令牌/库范围/限流/工具组，默认只读）同时又是 MCP 客户端（OAuth2、逐工具审批）；技能沙箱（Docker/E2B/Cube，git 检查点）、本机浏览器操控、CLI（agent-first，`mcp serve`）、Chrome 插件采集、10 个 IM 渠道。
（来源：weknora.weixin.qq.com/docs/ 下 01-overview、04-rag-pipeline、03-document-parsing、05-retrieval-engines、09-knowledge-graph、07-agent、08-mcp 各页，及 GitHub README）

## 3. 产品化思路【已确认】
从 RAG 问答走向知识运营的关键动作：①**Wiki 模式**——Agent 把文档提炼为互链页面+知识图谱，人工可编辑，**版本历史区分 pipeline/agent/user/revert 四种来源**，软上限 50 优先清理机器版本、硬上限 200 保人工记录，回滚本身可回滚；②**分块级编辑+版本历史**，改错字不必重传文档；③FAQ 库类型（标准问/相似问/**反例问**）；④解析时间线、卡住检测、活动流、自动打标签、批量重解析；⑤评估 API（BEIR 式数据集，输出 Precision/Recall/NDCG/MRR/MAP/BLEU/ROUGE）；⑥10 个数据源定时同步（飞书/Confluence/Notion/语雀/钉钉/GitLab/RSS 等）。（来源：docs/ 02-knowledge-base、14-wiki、15-evaluation、17-faq）

## 4. 商业化形态【已确认】
- 托管版 = **微信对话开放平台**（chatbot.weixin.qq.com），v0.1.0 README 原文："WeKnora 作为微信对话开放平台的核心技术框架"；另有 WeKnora Platform 云托管知识助手与 **WeKnora Cloud**（给自建版提供托管 LLM+解析），腾讯云 Lighthouse 提供应用模板。
- 出自**微信事业群**而非腾讯云【推断：官网域名 weknora.weixin.qq.com、npm scope `@wxg-prc-cpg`】；**与腾讯云大模型知识引擎 LKE 产品无血缘**【已确认：文档与 README 均无提及，LKE 仅作为 27 家模型厂商之一接入】。

## 5. 与 Agent 记忆的差异与融合【已确认】
WeKnora 已从组织知识侧反向切入个人记忆：v0.8.0 起内置**跨会话长期记忆**（资料/偏好/事实/事项/兴趣五类；explicit/auto 双模式后台蒸馏；**推断条目需用户确认**才注入；拒绝留抑制记录；pgvector 语义召回；**记忆影响问题理解与文档排序**但不扩权限；按空间+调用者隔离；JSON 导出）。融合已发生的三个接口：Agent 通过 `wiki_write_page` 把会话产出写回组织知识；`doc preference` 把常引文档沉淀为个性化检索偏好；MemoryAffinity 让记忆参与重排。**WeKnora 是"文档→记忆"，Hindsight 是"记忆→文档"，两者正在同一交汇点相遇。**

## 6. 可借鉴点 Top 5

| # | WeKnora 做法 | 对 ContextDB 的启示 | 成本 |
|---|---|---|---|
| 1 | **知识即 MCP 服务**：每空间独立端点+作用域令牌+工具组默认只读+限流；CLI/插件把知识送进任意 AI 工具 | Hindsight 内核的记忆 API 直接包装为租户级 MCP 端点（读写分离、默认只读），这是"被 Agent 生态消费"的分发面，WeKnora 已验证需求 | 低 |
| 2 | **记忆参与检索排序**：MemoryAffinity 插件挂在重排链最内层，retrieval_conditioning 用记忆改写问题理解与文档排序 | 差异化核心：让 Agent 记忆成为混合检索的一等输入（记忆→检索条件化），而非独立 recall API；注意 WeKnora 同样强调"记忆不扩权限" | 中 |
| 3 | **记忆治理闭环**：确认制、抑制记录、显式/自动双模式、上限与整理 | 给 Hindsight 自动 consolidation 加企业级治理：推断须确认、来源可溯、可导出清空——这是企业采购的记忆合规底线 | 中 |
| 4 | **双向沉淀带版本血缘**：wiki/chunk 编辑版本区分 pipeline/agent/user/revert，清理策略优先保护人工编辑 | "会话经验晋升知识条目"必须带同样纪律：晋升条目标注 agent 来源、可回滚、人工优先；对应 Hindsight 的知识晋升链 | 中 |
| 5 | **PG 同库混合检索+引擎抽象**：默认 ParadeDB（pgvector+BM25）与业务同库，RRF 上移，10 后端可按库绑定、懒重建 | 印证 ContextDB 的 Cell/DataPG 多 PG 方向：单 PG 同库混合作为默认档，专用引擎按租户/库选配；WeKnora 的注册表懒重建/singleflight 设计可直接抄 | 低-中 |

**一句话判断**：WeKnora 证明了"知识库平台长出记忆"与"记忆服务长出知识"终将同场竞争；ContextDB 的窗口在于把 Hindsight 的记忆原生性（retain/recall/reflect/consolidation）+ 华为云 PG/托管底座，做成 WeKnora 用插件方式补出来的那层（记忆↔检索融合、治理闭环），并以 MCP 一等公民形态分发。

**主要来源**：GitHub API 及 README/CHANGELOG/LICENSE/v0.1.0 README（github.com/Tencent/WeKnora）；官方文档站 weknora.weixin.qq.com/docs/（memory、rag-pipeline、retrieval-engines、document-parsing、knowledge-graph、agent、mcp、knowledge-base、wiki、evaluation、overview 共 11 页）；官网首页。均访问于 2026-10-08。
