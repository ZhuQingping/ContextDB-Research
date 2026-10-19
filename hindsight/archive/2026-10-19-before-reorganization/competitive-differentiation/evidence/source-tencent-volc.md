# 调研源报告：腾讯云与火山引擎 Agent 记忆/上下文管理产品布局

> 来源：夜间任务调研 agent 3（2026-10-08 执行）
> 方法：curl + jina 渲染代理 + 搜狗搜索实际抓取（WebSearch 故障兜底），全部访问于 2026-10-08
> 用途：`hindsight/competitive-differentiation/` 系列文档的原始输入

---

# 腾讯云 vs 火山引擎：Agent 记忆/上下文管理产品布局调研（2026 下半年）

**方法注记**：本环境 WebSearch/WebFetch 工具持续报 API 错误，全部证据改经 curl + jina 渲染代理 + 搜狗搜索**实际抓取**获得，未凭记忆编写；所有页面访问日期均为 2026-10-08。

## 一、火山引擎：OpenViking Context 已正式商用

**产品与状态**【已确认】
- 托管版产品名 **OpenViking Context**，产品页 https://www.volcengine.com/product/openviking-service（页面标题"火山引擎 - OpenViking Context"），定位"基于开源 OpenViking 内核构建的全托管云服务、面向 AI Agents 的上下文数据库"，Memory/Resource/Skill 统一为 viking:// 文件、L0/L1/L2 分层、目录递归检索。产品介绍文档 https://docs.volcengine.com/docs/84313/2374478（更新于 2026.09.16），**挂在 VikingDB 向量数据库文档树下**。
- **GA/时间线**【已确认】：VikingDB 产品更新公告（https://docs.volcengine.com/docs/vector_database_vikingdb/Releasenotes-14）显示 2026.5.26 库管理与计费上线、6.1 飞书知识导入、6.8 接入 OpenClaw/Claude Code/Codex/Cursor/TRAE 等框架卡片，至 9 月持续迭代——**已后付费正式收费（GA）约 5 个月**，另有服务等级协议文档。
- **区域**【已确认】：仅 cn-beijing（控制台与服务端点均为 openviking+cn-beijing）；海外 **BytePlus 计划中**（开源 README 自述）【官方宣传】。
- **定价**【已确认】（计费说明 https://www.volcengine.com/docs/84313/billing-instructions）：个人版 0.01 元/小时起（<4 万文件），超出按 1 万文件 0.003 元/时；企业版 0.05 元/时起（<20 万文件），超出按 10 万文件 0.03 元/时、独占实例；**个人版前 50 文件免费**；可用 **AgentPlan 订阅 AFP 额度抵扣**（5/25 AFP 每时起），在 Agent Plan 的"Agent 记忆"卡片一键开通。1 万文件≈2-3 万轮对话记忆或 3-5 千篇文档。
- **开源侧**【已确认】：GitHub volcengine/OpenViking，39,360 stars（2026-01-05 创建），主协议 AGPLv3 + CLI/examples Apache-2.0。开源/商业**同内核**，商业版差异=VikingDB 万亿级向量、SLA/Oncall、企业安全、火山生态集成（官方差异表）。记忆评测用 Doubao 2.0 Pro。
- HiAgent：产品页抓取未见独立记忆产品【未能验证 HiAgent 有独立记忆服务】，火山记忆叙事集中于 OpenViking。

## 二、腾讯云：双开源 + 平台内嵌，尚无托管记忆服务

- **TencentDB Agent Memory**【已确认】：GitHub TencentCloud/TencentDB-Agent-Memory，**27,762 stars**（2026-04-07 创建，5 个月冲到 2.8 万星），MIT（README 标注）。定位"团队级记忆中枢"：Chat Memory/Skill/LLM-Wiki/Code-Graph 四类记忆资产；符号化短期记忆（Mermaid 画布卸载）+ 长期记忆金字塔 L0 Conversation→L1 Atom→L2 Scenario→L3 Persona；OpenClaw 实测 **Token -61.38%、成功率 +51.52%**、PersonaMem 48%→76%（官方 README 数据）。后端为本地 SQLite 或腾讯云向量数据库 TCVDB，默认 LLM 端点指向腾讯云 LKE；Roadmap 为记忆迁移/Skill 生成/观测面板，**无云托管版计划**。
- **LKE 与 WeKnora 关系**【已确认】：cloud.tencent.com/product/lke 页面标题与内容已是"腾讯智能体开发平台"——**LKE 入口已并入 ADP**，知识能力成为平台原子能力。WeKnora 则是**微信团队**开源（Docker 镜像 wechatopenai/*、官网托管于 weknora.weixin.qq.com）：GitHub Tencent/WeKnora 32,413 stars，MIT，v0.8.2（2026-09-24），RAG 问答+Agent 推理（含跨会话记忆）+自动 Wiki；**云上部署仅为腾讯云 Lighthouse 应用模板（自托管），无全托管 SaaS**【已确认】。
- **TCADP**【已确认】：四种开发模式（Claw/标准/工作流/Multi-Agent）+ Agent Harness 托管运行；**文档树（/document/product/1759）无独立"记忆"功能项**；套餐订阅四档（免费版/Skill Plan（原 ClawPro，2026.4.27 更名）/专业版/企业版）+ PU 预付费资源包（100 元≈5000 万 token）。
- **微信生态**【已确认】：ADP"智能体一键接入微信服务号、订阅号、企业微信"；WeKnora 有 WeChat IM 集成与微信小程序连接器——微信通路是腾讯独有打法，但属**分发渠道优势**，非记忆技术本身。

## 三、华为云防御点与总结

**威胁点**：① 火山已跑通"AGPL 开源引流→0.01 元/时托管→AgentPlan 订阅捆绑"闭环，Coding Agent/个人开发者心智被占；② 官方"开源 vs 商业差异表"直接瓦解自建借口；③ 腾讯双 MIT 开源抢插件生态（OpenClaw/Hermes/npm），虽无托管版但随时可上云；④ 微信/企微分发独占 To C 与小 B。

**产品结构**：火山=单线纵深（OpenViking 开源+OpenViking Context 托管，挂 VikingDB）；腾讯=三线并行（WeKnora 知识/微信团队、Agent Memory 记忆/数据库团队、ADP 平台商业化），记忆暂为引流而非收入项。
**定价模式**：火山按小时+文件量后付费+订阅额度抵扣+免费额度；腾讯靠 ADP 套餐+PU 包，记忆零收费。

**最值得学习 3 点**：1）**激进入门定价与捆绑**：0.01 元/时、前 50 文件免费、按"加工后文件数"计费口径，并入开发者订阅套餐一键抵扣；2）**开源-云同内核+透明差异表**（规模/SLA/安全/生态四维对比），华为云 ContextDB 基于 Hindsight 可直接复制此话术；3）**Agent 框架插件矩阵与白盒运营**：主流 Coding Agent 接入卡片、用量/成本可视化、L0/L1/L2 可观测——华为云需在 GA 前补齐 Claude Code/OpenClaw/Cursor 等接入面与用量看板。

---

**主要来源**（均访问于 2026-10-08）：volcengine.com/product/openviking-service；docs.volcengine.com/docs/84313/2374478、/84313/billing-instructions、Releasenotes-14；github.com/volcengine/OpenViking（39,360★）；github.com/TencentCloud/TencentDB-Agent-Memory（27,762★）及其 README_CN；github.com/Tencent/WeKnora（32,413★）、weknora.weixin.qq.com；cloud.tencent.com/product/tcadp、/product/lke、/document/product/1759/129200。
