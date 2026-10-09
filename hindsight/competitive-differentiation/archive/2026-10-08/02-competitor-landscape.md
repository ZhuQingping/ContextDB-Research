# 友商全景：Agent 记忆/上下文服务竞争格局

日期：2026-10-08
调研方式：6 路并行调研 agent 实际抓取（GitHub API、官方文档、定价页、arXiv），全部访问于 2026-10-08
证据等级：【已确认】= 实际抓取验证；【官方宣传】= 官方自述未实测；【推断】= 由证据推导
原始调研记录：[evidence/](../../evidence/) 目录 6 份源报告
本轮检视：本页保留原调研结构，定价/版本/star 数未全面重抓；具体能力以 [05](05-concrete-selling-points.md) 为准，证据纠错见 [检视记录](../../evidence/review-concrete-capabilities.md)。

## 1. 结论速览

1. **"Agent 记忆托管"已是全球云厂商的标配赛道**：阿里（RDS ContextDB）、火山（OpenViking Context）已 GA 收费，AWS（AgentCore Memory）、Google（Memory Bank）全托管在售，Google 于 2026-09 起独立计费、AWS 于 2026-10-06 刚调整计费口径——两家国际厂 30 天内连续动价，说明赛道进入商业兑现期。
2. **国内最大威胁是阿里**：记忆晋升+知识评审闭环已上线（我方原设想的"团队知识闭环"差异点被占位），但**记忆/知识库均不可导出**（官方使用限制原文），锁定痕迹明显。
3. **商业模式最完整的是火山**：AGPL 开源同内核托管 + 0.01 元/时激进入门价 + AgentPlan 订阅抵扣 + 官方"开源 vs 商业差异表"——这套话术与打法华为云可直接复制且更优（MIT > AGPL）。
4. **API 范式已收敛**：AWS/Google 独立收敛出"控制面（建库/配策略）+ 数据面（事件流+语义检索）+ 策略分档"的共识形态；ContextDB 对齐该范式可降低客户迁移成本。
5. **具体比较方向**：导出可对照阿里限制；中文检索对照当前 Hindsight 部署并实测；权限、审计、恢复、治理按对象与链路比较。未检索到声明不等于行业空白，上游成绩不等于华为效果。

## 2. 六方全景总表【已确认，除注明外】

| 维度 | 阿里云 RDS ContextDB | 火山引擎 OpenViking Context | 腾讯云 | AWS AgentCore Memory | Google Memory Bank | Hindsight（开源内核） |
|---|---|---|---|---|---|---|
| 状态 | 中国站正式商用；国际站 invitational preview | GA 约 5 个月（2026-05-26 计费上线），仅 cn-beijing | **无托管记忆服务**；双开源引流 | 全托管在售 | 全托管在售（平台更名 Gemini Enterprise Agent Platform） | MIT 开源 46,695★，Cloud 按量在售 |
| 归属 | RDS（AI 能力中心） | VikingDB 文档树（数据库线） | WeKnora=微信事业群；Agent Memory=数据库团队 | Bedrock | Gemini Enterprise Agent Platform（Scale 板块） | Vectorize（$3.6M seed 独立公司） |
| 记忆模型 | 事实/实体 Entity Card/记忆规则/自动遗忘 + 记忆晋升为知识 | viking:// 统一文件、L0/L1/L2 分层 | 开源侧：L0 对话→L1 原子→L2 场景→L3 人格 | 事件流 + MemoryRecord + 5 类策略（semantic/preference/summary/episodic/custom） | fact 对象 + scope 隔离 + topic 枚举 + consolidation + revision | 四网络（事实/经历/实体/信念）+ retain/recall/reflect + 后台 consolidation |
| 知识侧 | 知识库+知识图谱+ContextDB Sync（钉钉/飞书）+知识评审 | Resource/Skill 与 Memory 同为 viking:// 文件 | WeKnora（32,413★，知识管理+记忆+Wiki） | 无（纯记忆） | 无（纯记忆，RAG 在别处） | Knowledge Page 原生 |
| 开源策略 | 闭源（开源侧为 AgentScope/ReMe 引流） | AGPLv3 开源同内核+商业差异表 | 双 MIT 开源（WeKnora 32,413★、Agent Memory 27,762★） | 闭源 | 闭源 | MIT 全功能开源 |
| 计费 | Credit（1 元/Credit）+ 存储 GB/时；新客送 834 元 | 0.01 元/时起 + 按文件量；AgentPlan 订阅 AFP 抵扣；前 50 文件免费 | 免费（引流） | 摄入 $1.00/GB + 存储 $0.10/GB-月 + 检索 + 记录 $0.75/千/月 | 存储 $0.30/GiB-月 + 读写折算 vCPU-h + 抽取 token 单列 | Cloud 按量（token/调用+存储），无席位费 |
| 导出 | 原调研及本轮官方搜索索引列限制，正文快照待复核 | 全量包未核验 | 自托管可访问数据，正式导出覆盖另验 | 有列表读取 API，全量包未核验 | 有读取/revision，全量包未核验 | 有部分文档导出，Workspace 全量待验证 |
| 中文优化 | 专项效果未核验 | 专项效果未核验，原评测用 Doubao | 面向中文，专项效果待核验 | 专项效果未核验 | 专项效果未核验 | 当前本地 PG 路径 english；中文向量已配置，全文适配待做 |
| 公开评测 | 本轮未核验 | 原材料有开源内核评测，托管服务待核验 | 原材料有 Agent Memory 自报评测 | 本轮未核验 | 本轮未核验 | 原材料有作者榜单；独立复现未验证，不作华为成绩 |

## 3. 国内三强详析

### 3.1 阿里云：需重点对照的国内产品

【已确认，详见 evidence/source-aliyun-contextdb.md】

- **产品力**：四链路升级为记忆沉淀（Entity Card 常驻画像+关系图谱+自动遗忘）/记忆晋升（多 Agent 协作写成知识文档，含审批+质量分阈值）/知识库（图谱+钉钉飞书同步）/知识评审（质量评分+自矛盾检测+智能重写）；"夜间服务"承担上下文演进。
- **接入摩擦极低**：自然语言安装 / curl install.sh 一键 CLI（--agent claude/codex/qoder/openclaw/hermes 等）/ MCP 三通道，官方支持八大平台。
- **计费打包模型成本**：写入/检索按 Credit 计价内含推理与向量化，Pro/Lite 按 Rerank 分档（价差 50 倍），客户决策成本低。
- **双线夹击**：百炼记忆库超低价（检索 Lite 0.00002 元/次）+ AgentScope/ReMe 开源占心智 + ContextDB 收企业级溢价；RDS Agent 与数据库线互相导流。
- **软肋**：①记忆/知识库**不可导出**；②托管实现未公开，本轮未获得可复现的服务效果报告；③独立域名 context-database.aliyuncs.com 引擎解耦但文档挂在 RDS MySQL 树下，数据库纵深叙事弱。

**战略含义**：原假设的"团队知识闭环（个人记忆→人审→团队 KB）"已被阿里以"记忆晋升+知识评审"占位。我方不能做功能跟随之争，必须**下沉到记忆层治理**（推断确认制/来源血缘/抑制记录——WeKnora 已验证该层空白，见 01 文档）并**对位其锁定软肋**（可导出+开放核心）。

### 3.2 火山引擎：商业模式最完整的对手，打法可复制

【已确认，详见 evidence/source-tencent-volc.md 与 evidence/source-opensource-landscape.md】

- **闭环完整**：OpenViking（开源 39,360★，AGPLv3）→ OpenViking Context（托管，挂 VikingDB 文档树）→ 0.01 元/时起、前 50 文件免费、AgentPlan 订阅 AFP 额度抵扣、Agent 记忆卡片一键开通。
- **透明差异表**：官方"开源 vs 商业"差异表（规模/SLA/Oncall/企业安全/生态四维）直接瓦解自建借口。
- **运营打法**：Coding Agent 接入卡片矩阵（OpenClaw/Claude Code/Codex/Cursor/TRAE 等）、用量/成本可视化、L0/L1/L2 可观测。
- **软肋**：仅 cn-beijing 单区域；AGPLv3 的许可义务需要按修改与提供服务的方式评估，不能概括为所有商业使用均须开源——这一点 MIT 的 Hindsight 天然占优。

**战略含义**：火山的"开源-云同内核+透明差异表+激进入门价+订阅捆绑"四件套已被市场验证 5 个月，ContextDB 可整体复制并将许可换为 MIT、将单区域升级为多 Cell/多区域、将"文件量计费"升级为"数据库级计费透明"。

### 3.3 腾讯：生态玩家，暂无托管记忆收入

【已确认，详见 evidence/source-tencent-volc.md】

- 三线并行：WeKnora（微信事业群，知识管理+跨会话记忆）、TencentDB Agent Memory（数据库团队，L0-L3 记忆金字塔，27,762★）、ADP 平台（套餐+PU 资源包）。
- 记忆暂为**引流而非收入项**：无托管版计划、记忆零收费、Roadmap 无上云项。
- 独占资产：微信/企微分发通路（To C 与小 B），与华为云政企 B 端市场几乎不重叠。

**战略含义**：腾讯当前不构成托管记忆正面竞争，但其"开源抢插件生态"（OpenClaw/Hermes/npm）提醒我方：**客户端生态卡位窗口期有限**。Hindsight 已覆盖 Qwen Code/Kimi/Trae/CodeBuddy 等 20+ harness【已确认】，ContextDB 应顺势继承而非另起炉灶。

## 4. 国际云三范式

【已确认，详见 evidence/source-aws-google.md】

| 范式 | 代表 | 机制 | 对 ContextDB 的含义 |
|---|---|---|---|
| 记录式 | AWS AgentCore Memory | 事件流→MemoryStrategy 抽取→MemoryRecord；三档执行（built-in 贵/override 中/self-managed 便宜） | 策略分档定价是毛利保护机制：托管抽取成本内化（built-in 记录费 3 倍）；ContextDB 定价应把抽取/巩固 token 单列或分档 |
| 生成式 | Google Memory Bank | 会话事件→LLM 生成合并 fact 对象；scope≤5KV 隔离；topic 枚举+few-shot 自定义；revision 历史+TTL | 治理细节最全：scope 级 IAM、区域驻留、记忆投毒（memory poisoning）官方警示+Model Armor 建议——"记忆投毒防御"已进入国际厂官方文档，可作为 ContextDB 安全叙事的对齐点 |
| 协议式 | Anthropic memory tool / OpenAI 产品内嵌 | Anthropic 不做托管，六命令文件协议、存储归客户端；OpenAI 记忆仅是 ChatGPT 产品功能，API 无记忆服务 | **memory tool 协议正在成为事实标准**：ContextDB 应可直接充当 Claude memory tool 的 `/memories` 托管后端——"协议优先+托管后端"双形态进入存量生态 |

**API 范式收敛点**（AWS/Google 独立趋同）：控制面（建库/配策略/删除）+ 数据面（写事件/批量摄取/语义检索/列出）+ actorId/sessionId/namespace（或 scope）三层身份隔离 + TTL/过期。ContextDB 的 Workspace/Bank/actor 设计与此同构，对外文档应主动标注对齐关系以降低迁移成本。

## 5. 国际开源光谱与行业分界线

【已确认，详见 evidence/source-opensource-landscape.md】

| 模式 | 代表 | 变现 |
|---|---|---|
| 引擎开源+云独占功能 | Mem0（66,768★）、Cognee | 订阅/用量；图谱、整合、治理云独占 |
| 引擎开源+闭源数据面 | Zep（31,525★，Graphiti+闭源 Konig） | 云订阅+BYOC |
| MIT 全开源+纯托管 | **Hindsight（46,695★，仅次于 Mem0）** | 按量托管+企业版（BYOC/SLA 99.95%/SSO） |
| 开源+产品化转型 | Letta（25,068★，主仓 5 月后无 release） | 转型 agent 产品——**记忆 infra 单独变现困难的信号** |
| 论文代码 | A-mem（1,192★，停更） | 无——**无维护即死** |

**所列国际开源项目的产品分层**：引擎采用宽松许可（该样本不含 AGPL 的 OpenViking），云独占=SSO/MFA/审计/SLA/BYOC 等治理 + 高级认知功能（记忆整合/图谱/防投毒）。ContextDB"核心开源"路线符合行业主流，但必须回答：**MIT 意味着任何人（包括阿里）可以拿同样的内核建同样的服务**——壁垒只能来自托管运维质量、企业治理深度与数据库级优化（04 文档展开）。

**云厂商自研铁律**：AWS/Google/Azure 全部自研、**未发现任何头部云厂商托管 Mem0/Zep/Letta**。记忆层被云厂视为必争控制点——华为自建路线符合行业主流，但也意味着没有"引入第三方"的捷径可走。

## 6. 定价模式对比表

【已确认，均抓取自官方定价页，详见各 evidence 文件】

| 厂商 | 计费单位 | 入门门槛 | 特点 |
|---|---|---|---|
| 阿里 ContextDB | Credit（1 元/Credit）+ 存储 0.00017~0.0021 元/GB/时 | 新客送 834 元 | 调用含模型成本，Pro/Lite 价差 50 倍 |
| 火山 OpenViking | 0.01 元/时起+按文件量（1 万文件 0.003 元/时） | 前 50 文件免费；AgentPlan AFP 抵扣 | 全场最低入门价+订阅捆绑 |
| AWS AgentCore | 摄入 $1.00/GB（10-06 新政）+存储 $0.10/GB-月+记录 $0.75/千/月+built-in 3 倍溢价 | 按量 | 策略分档定价的毛利设计范本 |
| Google Memory Bank | 存储 $0.30/GiB-月+读写折算 vCPU-h+抽取 token 单列 | 首 1GiB 免费 | 成本结构最透明（Compute/Memory/Storage 三资源） |
| Hindsight Cloud | 按 token/调用+存储，无席位费 | 按量 | 与 Vectorize 自家 Cloud 互为镜像——华为云托管 Hindsight 的定价可参照其上限（企业版 BYOC+SLA 99.95%） |
| 腾讯 | 记忆零收费（ADP 套餐+PU 包间接变现） | 免费 | 引流逻辑 |

**定价启示**：国内战场入门价已被火山钉在 0.01 元/时；阿里用 Credit 打包模型成本。ContextDB 的合理定位是**介于两者之间**：按量计费+抽取/巩固 token 单列（学 Google 透明）+华为云开发者订阅额度抵扣（学火山捆绑）+免费额度给足（前 50 文件/1GiB 量级的行业惯例）。

## 7. 威胁矩阵与空白矩阵

### 7.1 威胁矩阵（对我方既有差异化假设的冲击）

| 我方原假设 | 现状 | 冲击评级 | 应对方向 |
|---|---|---|---|
| 团队知识闭环（个人记忆→人审→团队 KB） | 阿里"记忆晋升+知识评审"已上线 | **高** | 下沉到记忆层治理（确认制/血缘/抑制记录），知识闭环保留但不再作为主差异点 |
| 数据库级运维与正确性 | 阿里挂 RDS 树、火山挂 VikingDB 树，均已在讲数据库故事 | 中 | 比拼深度：多 Cell/多区域/SLA/国产化替代（华为 GaussDB 基因强于两者） |
| 成本可解释性 | Google 已做"三资源透明计费"；AWS 分档定价 | 中 | 对齐+超越：抽取/巩固/检索成本在控制台可见可归因 |
| 开放核心 | 火山 AGPL 同内核+差异表已跑通；行业分界线已收敛 | 中 | MIT 优于 AGPL+可导出承诺+上游贡献换生态主导权 |

### 7.2 具体能力比较与验证缺口

| 能力 | 比较依据与边界 | 我方验证 |
|---|---|---|
| 导出 | 阿里索引列限制，其他完整资产包未全面核验 | 格式/快照/权限/校验与导入 |
| 中文 | 当前本地 Hindsight PG 用 english，竞品效果待测 | 分词读写适配、历史重建、同条件评测 |
| 治理 | WeKnora 有确认/抑制，Google 有 revision，不能称唯一 | 检索与后台全链路过滤、人工保护 |
| 加密 | AWS/Google 已有客户密钥 | 各落点覆盖、密钥依赖及恢复 |
| 质量报告 | 多方有自报研究分数，服务效果仍须同条件测试 | 固定版本/模型/预算，不继承上游分数 |
| 防投毒/协议 | 原材料已有多个先例，托管支持待核验 | 攻击样本和客户端版本测试 |

## 8. 来源

全部访问于 2026-10-08，逐条 URL 见 [evidence/](../../evidence/)：
[source-aliyun-contextdb.md](../../evidence/source-aliyun-contextdb.md)（阿里 69 次实抓）、[source-tencent-volc.md](../../evidence/source-tencent-volc.md)（腾讯/火山）、[source-aws-google.md](../../evidence/source-aws-google.md)（国际四家）、[source-opensource-landscape.md](../../evidence/source-opensource-landscape.md)（开源全景）、[source-weknora-deep-dive.md](../../evidence/source-weknora-deep-dive.md)（WeKnora）、[source-papers-survey.md](../../evidence/source-papers-survey.md)（论文）。
