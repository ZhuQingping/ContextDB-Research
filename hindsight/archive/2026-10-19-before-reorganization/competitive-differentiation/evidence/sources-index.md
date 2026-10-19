# 来源索引

全部来源访问于 2026-10-08。主文档中的证据分级：【已确认】= 实际抓取验证；【官方宣传】= 官方自述未实测；【推断】= 由证据推导；【未能验证】= 尝试但未获证据。

## 原始源报告（本目录）

本轮新增 [review-concrete-capabilities.md](review-concrete-capabilities.md)：华为 RDS 加密/zhparser 核验、原文冲突、纠错与待验证项。源报告保留为历史输入；与修订主文档冲突时按检视记录阅读，旧“已确认”标签不是当前事实保证。

| 文件 | 覆盖范围 | 调研方式 |
|---|---|---|
| [source-weknora-deep-dive.md](source-weknora-deep-dive.md) | WeKnora 架构/记忆/治理/MCP/商业化 | GitHub API + 官方文档站 11 页实抓 |
| [source-aliyun-contextdb.md](source-aliyun-contextdb.md) | 阿里 RDS ContextDB/百炼记忆/开源布局 | 官方帮助文档/活动页/GitHub API，69 次调用 |
| [source-tencent-volc.md](source-tencent-volc.md) | 腾讯 WeKnora+Agent Memory+ADP；火山 OpenViking Context | curl+jina 渲染+搜狗搜索兜底 |
| [source-aws-google.md](source-aws-google.md) | AWS AgentCore Memory/Google Memory Bank/Anthropic memory tool/OpenAI | 官方文档+定价页；OpenAI 经 Wayback 验证 |
| [source-opensource-landscape.md](source-opensource-landscape.md) | Mem0/Hindsight/Cognee/Zep/Letta/MemOS/A-mem 数据刷新与商业模式 | GitHub API+定价页实抓 |
| [source-papers-survey.md](source-papers-survey.md) | 14 篇论文 + 评测基准 + 上下文工程共识 | arxiv.org/abs 页面逐篇核验（13 来源） |

## 按主题的关键来源

**阿里云**：help.aliyun.com RDS ContextDB 快速开始/使用限制（不可导出原文）；aliyun.com/activity/database/contextdb（新客活动与定价）；docs.bailian.console.aliyun.com 记忆库计费；github.com/agentscope-ai/{agentscope,ReMe}。

**火山引擎**：volcengine.com/product/openviking-service；docs.volcengine.com/docs/84313/{2374478,billing-instructions}；Releasenotes-14（GA 时间线）；github.com/volcengine/OpenViking（39,360★，AGPLv3）。

**腾讯**：github.com/Tencent/WeKnora（32,413★）+ weknora.weixin.qq.com/docs；github.com/TencentCloud/TencentDB-Agent-Memory（27,762★）；cloud.tencent.com/product/{tcadp,lke}。

**AWS**：docs.aws.amazon.com/bedrock-agentcore/{devguide/memory,memory-strategies,APIReference}；aws.amazon.com/bedrock/agentcore/pricing（2026-10-06 新政）。

**Google**：docs.cloud.google.com/gemini-enterprise-agent-platform/{vertex-ai-name-changes,scale/memory-bank,api-quickstart}；cloud.google.com/products/gemini-enterprise-agent-platform/pricing。

**Anthropic/OpenAI**：platform.claude.com memory tool；code.claude.com memory；claude.com/blog/memory；openai.com/index/memory-and-new-controls-for-chatgpt（Wayback）；developers.openai.com/api/docs。

**开源全景**：api.github.com/repos/{mem0ai/mem0,vectorize-io/hindsight,topoteretes/cognee,getzep/graphiti,letta-ai/letta,MemTensor/MemOS,agiresearch/A-mem}；mem0.ai/pricing；getzep.com/pricing 与 blog；letta.com；cognee.ai/pricing；vectorize.io/{pricing,about,blog/hindsight-40k-stars}；hindsight.vectorize.io/developer/oracle。

**论文**（arxiv.org/abs/）：2310.08560 MemGPT；2504.19413 Mem0；2502.12110 A-MEM；2507.03724 MemOS；2501.13956 Zep；2405.14831 HippoRAG；2502.14802 HippoRAG 2；2401.18059 RAPTOR；2402.17753 LoCoMo；2410.10813 LongMemEval；2304.03442 Generative Agents；2504.13171 Sleep-time Compute；2512.12818 Hindsight；2507.13334 Context Engineering 综述。另：benchmarks.hindsight.vectorize.io（实时榜单）。

**本地基线文档**（只读引用）：hindsight/Hindsight Architecture.md、cloud-service-priorities.md、cloud-service-architecture.md、contextdb-high-level-design.md、contextdb-design-expert-review.md、backend-storage.md、scheme3-prototype-design.md、hindsight-cloud-open-source-comparison.md。
