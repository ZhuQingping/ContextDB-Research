# 调研源报告：开源 Agent 记忆产品全景（Mem0/Zep/Letta/Cognee/MemOS/A-MEM/Hindsight）

> 来源：夜间任务调研 agent 5（2026-10-08 执行）
> 方法：GitHub API 与各官网 curl 实抓（WebSearch/WebFetch 故障兜底），全部访问于 2026-10-08
> 用途：`hindsight/competitive-differentiation/` 系列文档的原始输入

---

# 开源 Agent 记忆产品格局调研（截至 2026-10-08，所有数据当日实抓）

## 一、数据刷新【已确认】（GitHub API，2026-10-08）

| 项目 | Stars | 许可证 | 最近 push | 最新 release |
|---|---|---|---|---|
| Mem0 | 66,768 | Apache-2.0 | 10-07 | v2.2.1（09-25） |
| **Hindsight** | **46,695** | MIT | 10-07 | v0.10.2（09-29） |
| Cognee | 31,545 | Apache-2.0 | 10-07 | v1.6.3（10-07） |
| Zep/Graphiti | 31,525 | Apache-2.0 | 10-07 | v0.30.2（09-08） |
| Letta | 25,068 | Apache-2.0 | 09-10 | v0.16.8（2026-05-14） |
| MemOS | 11,745 | Apache-2.0 | 09-29 | v2.0.34（09-23） |
| A-mem | 1,192 | MIT | 2025-12-12 | 无（停更） |

要点：Hindsight 上线约一年即 46.7k★，超过 Graphiti/Letta/Cognee，仅次于 Mem0。官方自述：333 天破 40k★，后 20k 仅用 45 天，263 名贡献者、70 个 release（平均 4.8 天一个）、fork/star 比 13%（hindsight.vectorize.io/blog/2026/09/28/hindsight-40k-stars）。Letta 主仓 5 月后无 release，开发重心已转移至 letta-code 仓（3,539★，10-07 仍在更新）；A-mem 为论文代码已停更。来源：api.github.com/repos/...（mem0ai/mem0、vectorize-io/hindsight、letta-ai/letta 等）。

## 二、2026 下半年关键动作【已确认=官方博客/仓库；官方宣传单独标注】

- **Mem0**：Dream 后台记忆整合（09-03）、DolphinBench 基准（09-22）、入驻 Vercel Marketplace（09-16）、时序推理（07-31）、OpenMemory MCP 服务 coding agents。融资 $24M（YC/Peak XV/Basis Set，2025-10-28，techcrunch.com/2025/10/28/mem0-raises-24m-from-yc-peak-xv-and-basis-set-to-build-the-memory-layer-for-ai-apps）。
- **Zep/Graphiti**：自研闭源图数据库 Konig 作为数据面（08-27）、Memory MCP Server（06-30、08-19）、ABAC 密钥权限（07-09）、记忆溯源（07-14）、Batch API（06-09）、记忆投毒防御（09-02）。S&P Global（2026-04）称其有望成为该层事实伙伴【官方宣传】。（getzep.com/blog）
- **Letta**：战略转型——4 月发布 Letta Code app 并发文"Why Memory Isn't a Plugin"，8 月 Agents SDK、9 月动态工作流；从"记忆基础设施"转向"会学习的 agent 产品"。历史融资 $10M seed（Felicis，投后 $70M，2024-09，TechCrunch）。
- **MemOS**：2.0 "Stardust" 发布（MemCube 架构、Cloud/Lite 双版本、DeepSeek Harness 插件）；官网列 Alibaba Cloud、中国电信、上交大、海尔、携程为合作伙伴【官方宣传，深度未核实】（memos.openmem.net）。
- **Cognee**：v1.6.3 时序检索与召回精度增强（10-07）。

## 三、商业模型对比【已确认】（定价页实抓）

- **Mem0**（mem0.ai/pricing）：云 Free/$19/$249/企业版；**云独占**：Graph memory、Dream、高级分析、on-prem、SSO/审计。
- **Zep**（getzep.com/pricing）：开源仅 Graphiti 引擎；云 Free（1 万 credits/月）/Flex $125/Flex Plus $375/企业版，按 Episode 大小计 credit，检索存储不限量；**云独占**：Observations、自定义抽取、webhooks、分析、ABAC、BYOK/BYOC。
- **Letta**（letta.com 文档 Pricing）：Pro $20/月；API $20/月+$0.10/活跃 agent+按 token；Teams $20/席。增值=托管沙箱与 Letta Auto 模型路由。
- **Cognee**（cognee.ai/pricing）：$1/百万 token+$5/workspace；企业版为 BYOC 交付（含闭源 runtime）。
- **Hindsight**（vectorize.io/pricing）：MIT 自托管免费无限制；Cloud 纯按量（百万 token/调用+存储，无月费席位费）；企业版 BYOC/本地、SLA 最高 99.95%、SSO/RBAC。母公司 Vectorize：2024-01 成立，$3.6M seed（True Ventures），CEO Chris Latimer【官方宣传】（vectorize.io/about）。
- 全行业**无一家 AGPL/BSL**，均宽松许可+云增值。

## 四、Hindsight 其他动态【已确认】

0.10.0 图像/文件一等记忆、0.10.2 bank 别名/按 scope 整合；Cloud 6–8 月上线 SSO/MFA/审计/Memory Defense（防注入、密钥检测）；Hermes 插件化（10-01）。**关键先例：官方文档支持 Oracle Database 23ai 作存储后端（VECTOR+Oracle Text），retain/recall/reflect 全功能可用**（hindsight.vectorize.io/developer/oracle）。客户端已覆盖 Qwen Code、Kimi、Trae（字节）、CodeBuddy（腾讯）、DeepSeek Harness 等 20+ harness。

## 五、云厂商自研 vs 采用开源【已确认】

- AWS：Bedrock AgentCore Memory，全托管短/长期记忆（docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html）
- Google：Vertex AI Memory Bank（Agent Engine 内）（cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/memory-bank/overview）
- 微软：Foundry Agent Service Memory（preview）+ Memory Store API（learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-memory）
- **未发现任何头部云厂商托管 Mem0/Zep/Letta**；Zep 以"中立多云"对抗云厂锁定（getzep.com/aws-agentcore-memory-alternative）。第三方进云厂的路径只有 Marketplace（Mem0×Vercel）与伙伴名单（MemOS×阿里云 logo）。

## (a) 商业模式光谱表

| 模式 | 代表 | 开源 | 变现 |
|---|---|---|---|
| 论文代码 | A-mem | 全部 | 无，已停更 |
| 引擎开源+云独占功能 | Mem0、Cognee | Apache-2.0 | 订阅/用量；整合、图谱、治理云独占 |
| 引擎开源+闭源数据面 | Zep（Graphiti+闭源 Konig） | Apache-2.0 | 云订阅+BYOC |
| MIT 全开源+纯托管 | Hindsight | MIT 全功能 | 按量托管+企业版 |
| 开源+产品化转型 | Letta | server+code | 订阅+算力 |
| 中国生态开源+私有化 | MemOS | Apache-2.0 | Cloud+企业版+行业方案 |
| 云厂自研闭源 | AWS/Google/Azure | 无 | 绑定自家 agent 栈 |

## (b) 对华为云"核心开源+商业增值"的 4 条启示【推断，基于上述证据】

1. **自建路径符合行业主流，但护城河不在许可**。三大云厂全部自研、无一托管第三方开源记忆——记忆层是云厂必争控制点。MIT 让华为自建无合规障碍、可白嫖 46.7k★ 生态，但也意味着 Vectorize 或任何人都能做同样的事：壁垒只能来自托管运维质量、企业治理与数据库级深度优化。
2. **开源/商业分界线已被行业收敛**：引擎全开源，云独占=SSO/MFA/审计/SLA/BYOC 等治理+高级认知功能（记忆整合、图谱、防投毒）。ContextDB 应完全开源引擎，把 GaussDB 托管、Memory-Defense 类安全、审计合规、SLA 打包成增值。
3. **Oracle 23ai 后端是华为的现成模板**：以数据库为记忆底座（pgvector 兼容、Oracle 用 VECTOR+Oracle Text 复刻全功能），Hindsight 还已支持 Citus 集群后端。"数据库厂商+开源记忆"既可讲国产化替代故事，也应向上游深度贡献（fork 比 13% 证明用户真实在改代码）换取生态主导权。
4. **生态卡位在客户端而非引擎，且警惕独立商业化陷阱**。Hindsight 靠 20+ coding harness（含 Qwen Code/CodeBuddy/Trae 等中国系）起量，Mem0 靠 OpenMemory MCP+Vercel Marketplace 分发——ContextDB 上市即需 MCP server 与国产 harness 适配。反面教材：A-mem 无维护即死、Letta 因记忆 infra 单独变现困难而转型 agent 产品。记忆应作为云/数据库产品线能力出售，而非独立赛道。

---

**主要来源**（均访问于 2026-10-08）：api.github.com/repos/{mem0ai/mem0, vectorize-io/hindsight, topoteretes/cognee, getzep/graphiti, letta-ai/letta, MemTensor/MemOS, agiresearch/A-mem}；mem0.ai/pricing、getzep.com/pricing、letta.com（Pricing 文档）、cognee.ai/pricing、vectorize.io/pricing 与 /about；hindsight.vectorize.io（blog/40k-stars、/developer/oracle、release notes）；getzep.com/blog；memos.openmem.net；docs.aws.amazon.com（bedrock-agentcore memory）；cloud.google.com（vertex-ai memory-bank）；learn.microsoft.com（foundry agents memory）；techcrunch.com（Mem0 融资、Letta 融资）。
