# 调研源报告：阿里云 Agent 记忆/上下文管理产品布局

> 来源：夜间任务调研 agent 2（2026-10-08 执行）
> 方法：官方帮助文档、活动页、GitHub API 实际抓取（69 次工具调用），全部访问于 2026-10-08
> 用途：`hindsight/competitive-differentiation/` 系列文档的原始输入

---

# 阿里云 Agent 记忆/上下文管理产品布局调研（2026-10-08，均于当日访问实测抓取）

## 一、RDS ContextDB 现状【已确认，官方文档】

- **定位与归属**：官方定义为"面向 Agent 的企业级上下文数据库服务"，帮助文档挂在"云数据库 RDS > RDS MySQL数据库 > AI能力中心 > RDS ContextDB"下，属 RDS 控制台"AI 应用市场"家族（与 RDS Agent 兼容 OpenClaw/Hermes、RDS Agent Manager、全托管 Supabase 并列），独立域名 context-database.aliyuncs.com，按量付费，与具体数据库引擎解耦；文档未提及 RDS PostgreSQL【"基于 PG"这一说法未能验证，推断已改为引擎无关的独立服务】。
- **状态**：中国站已正式商用（原文"如您之前为公测用户，可单击正式开通"）；国际站标注 invitational preview（需提工单，2026-09-21 更新）。客户端 OSS 在 cn-hangzhou，未公布多区域列表【区域信息未能验证】。
- **定价**（快速入门文档原文）：调用按 Credit——记忆写入/检索（contextdb_mem_add_requests 等）、知识写入/检索、上下文演进（context_growth），1 元/Credit；存储按 GB/小时——源存储 0.00017 元/GB/时、上下文存储（记忆+索引）0.0021 元/GB/时。Credits 包有效期 1 个月、不可退、不抵扣存储。新客活动 2026-09-20~11-30 送 834 元（799 元 Credits + 35 元存储券≈20GB/月）。
- **能力演进**：四链路已升级为——①记忆沉淀（事实/实体 Entity Card 常驻画像+关系图谱/记忆规则/自动遗忘）；②记忆晋升（多 Agent 角色协作把记忆写成知识文档，含审批、质量分阈值自动入库）；③知识库（含知识图谱开关、ContextDB Sync 同步钉钉/飞书）；④知识评审（质量评分、自矛盾检测、智能重写）；"夜间服务"承担上下文演进（即原 Dream 异步整理）。记忆和知识库**均暂不支持导出**（官方使用限制原文）。
- **接入**：API Key + 三通道——自然语言安装、curl install.sh 一键 CLI（--agent claude/codex/qoder/qwenwork/openclaw/hermes 等）、MCP（/v1/mcp）。官方支持 Qoder、QoderWork、Claude Code、Codex、OpenClaw、OpenCode、Hermes、千问办公八平台。
- 来源：https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/rds-contextdb-quick-start ；https://www.aliyun.com/activity/database/contextdb ；https://www.alibabacloud.com/help/en/rds/apsaradb-rds-for-mysql/rds-contextdb-quick-start

## 二、百炼记忆能力【已确认，官方文档】

- **记忆库/长期记忆 API**：自动提取"事实记忆+用户画像"，走 DashScope 网关（/api/v2/apps/memory/，AddMemory/SearchMemory/画像模板等接口，3000 QPM）。2026-08-20 商业化：写入事实记忆 Pro 0.03 元/次、Lite 0.018、多模态 0.1、技能记忆 0.3；检索 Pro 0.001、Lite 0.00002（差别在 Rerank）；存储 0.002 元/万条/时。免费额度 1500 次写入+5000 次检索+1 万条存储。来源：https://docs.bailian.console.aliyun.com/zh/model-studio/memory/billing.md 及 memory-library.md。
- **Managed Agents**（2026-08-17 商业化）：会话运行时 0.5 元/时+模型费+工具费；"记忆库"此处指跨会话持久化文件树，挂载于 /mnt/memory。Agent 1.0 应用内长期记忆存储免费；Agent 2.0 长期记忆标注"未来迭代支持"。**百炼记忆库与 ContextDB 无官方互操作说明**【推断：两条产品线分层——模型平台做轻量对话记忆，数据库线做企业级上下文资产】。

## 三、开源布局【已确认，GitHub 实测】

- **AgentScope**（32,849 stars，Apache-2.0）：记忆为中间件——Agentic Memory（Markdown 自治）、ReMe、Mem0 三后端可切换；Context 中间件做自动压缩与工具结果卸载。
- **ReMe**（3,555 stars，Apache-2.0，2026-10 仍活跃）：local-first Markdown 记忆库，BM25+向量+wikilink 检索，跨 Agent 共享工作区（SKILL.md/CLI/HTTP/MCP）；README 示例 LLM/Embedding 端点指向 DashScope——开源引流、按模型调用变现的闭环【推断】。
- **Spring AI Alibaba**（10,969 stars，Apache-2.0）：Graph 有状态运行时+Admin 可视化平台+Nacos A2A，记忆沿用 Spring AI Chat Memory 体系。
- 来源：github.com/agentscope-ai/agentscope、/ReMe、alibaba/spring-ai-alibaba（2026-10-08 查询 API）。

## 四、商业化打法

按量双轨（调用 Credit 计费已含推理/向量化成本+存储计费）；ContextDB 主打企业级 Coding Agent 与多 Agent 协作（八大平台一键接入），百炼记忆库主打对话应用（千次检索 1 元的低价）；RDS Agent（2026-04-17 起试用，包年包月 6 折）基于 RDS 向量数据库内置长期记忆并绑定百炼全系列模型——数据库线与模型线互相导流。来源：https://www.aliyun.com/activity/database/rdsclaw。

## 五、对华为云 ContextDB 的威胁点

1. **接入摩擦极低**：一条 curl 命令+MCP 覆盖 Claude Code/Codex 等主流 Coding Agent，抢占开发者入口；
2. **记忆→知识治理闭环**：记忆晋升+知识评审（质量分/自矛盾检测/自动入库阈值）超出"存储+检索"，切入企业知识治理预算；
3. **双线夹击**：百炼记忆库超低价+开源 AgentScope/ReMe 占心智，ContextDB 收企业级溢价；
4. **锁定**：记忆/知识库不可导出。

## 最值得学习的 3 点

1. **计费打包模型成本**：Credit/次数单价内含推理与向量化，Pro/Lite 按是否 Rerank 分档（价差 50 倍），客户决策成本极低；
2. **三通道最小化接入**（自然语言/CLI/MCP）并逐一适配主流 Coding Agent 清单，作为产品页第一卖点；
3. **把记忆做成"组织资产"**：Workspace-Group-Member 三层权限+晋升审批+审计日志，用治理语言而非 AI 语言对企业采购叙事。

（功能效果均引自官方文档，属官方宣传、未实测。）
