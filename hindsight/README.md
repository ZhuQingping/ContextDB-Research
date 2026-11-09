# Hindsight / ContextDB 文档

## 产品讲解与持续推进（2026-11-07起）

面向领导和开发同事的讲解统一从 **[ContextBase 产品讲解与演示](product-guide/README.md)** 开始：核心价值、可用部署架构、真实案例、问题解答和验证待办。

下面保留既有技术文档索引；其中版本与状态属于各自记录时间，不代表2026-11-07运行环境已重新完整验收。

当前实现基于 **Hindsight v1.0.0**，代码分支 `contextdb/v1.0.0`。本目录只将一套当前文档放在主目录中；旧方案、重复手册和过程记录放入 [archive](archive/README.md)。完整设计与实现细节保留，未按篇幅删减。本轮同步管理简化已在本地实现，本地回归与 Hindsight/PG 独立检视已完成（见验证摘要）；代码特性提交为已推送的 `a05b808`；随后发现的问题及待优化状态以[统一清单](design/contextdb-simplification-plan.md#current-optimization-backlog)为准，不能用此前回归结果替代后续修复验收。

## 从这里开始

| 你要做什么 | 先看哪份 |
| --- | --- |
| 理解方案、评审架构 | [完整设计](design/contextdb-release-design.md) |
| 理解召回次数/时间、读取权限、配置和旧实例升级 | [召回统计设计与使用说明（已实现，PR #54送审）](design/contextdb-recall-usage-design.md) |
| 查看简化实施状态、核对依赖与验收 | [简化与实施清单](design/contextdb-simplification-plan.md) |
| 查看后续待修复、待优化的统一安排 | [统一清单](design/contextdb-simplification-plan.md#current-optimization-backlog)；[Issue #19证据与测试缺口](design/contextdb-pr15-issue19-review-analysis.md) |
| 检视相对原生 Hindsight 的代码改动 | [代码检视指南](design/code-review-guide.md) |
| 查看管理 API、参数、返回值并执行测试 | [API 与 curl 手册](api/contextdb-management-api-curl-guide.md) |
| 用curl真实验证Retain/Recall、中英文及空间隔离 | [Retain / Recall用例](api/contextdb-retain-recall-curl-guide.md) |
| 了解PG权限、普通客户隔离及root边界 | [PG隔离统一方案](deployment/contextbase-postgresql-isolation.md)；[云端验收](testing/contextbase-cloud-pg-e2e-20261024.md) |
| 部署自研 ContextDB | [联调操作指南](deployment/contextdb-service-integration-guide.md)；配置字段查 [部署合同](deployment/contextdb-deployment-contract.md) |
| 先对接官方原生 Hindsight | [原生联调操作指南](deployment/native-v1.0.0/contextdb-service-integration-guide.md) · [原生部署合同](deployment/native-v1.0.0/contextdb-deployment-contract.md) · [部署工具](deployment/native-v1.0.0/tools/) |
| 运行问题定位、恢复 | [运维手册](operations/contextdb-operations-runbook.md) |
| 火山 embedding 每批超过 10 条导致写入失败 | [批量参数与任务恢复（2026-11-08）](operations/contextbase-embedding-batch-20261108.md) |
| 排查深度回忆超时、定位四层配置及评估默认值 | [Reflect 超时处理与默认值评估待办（2026-11-07）](operations/contextbase-reflect-timeout-20261107.md) |
| 排查 Claude Code 与 Codex 的 ContextBase 安装、项目 Bank 隔离和自动保存 | [客户端安装问题记录（2026-11-07）](operations/contextbase-coding-agents-installation-issues-20261107.md) |
| 了解验证结果及尚未覆盖的环境 | [验证摘要](testing/contextdb-validation-summary.md) |
| 查看夜间质量任务、已测/未测、已修复/未修复 | [质量任务与验收记录](testing/contextdb-quality-improvement-plan.md) |

评审先看设计与代码检视两份即可。部署合同解释“管控传什么”，联调指南解释“节点逐步怎么执行”，两者分工不同。

## 目录与配套资料

| 目录 | 内容 |
| --- | --- |
| `design/` | 当前完整设计、代码检视、简化实施清单；规格与决策更新设计正文，实施范围和状态维护清单 |
| `api/` | 13 个管理操作、原生业务接口与权限验证用例 |
| `deployment/` | 自研部署；`native-v1.0.0/` 单独放官方原生部署，不能混用初始化及认证 |
| `operations/` | 日志、健康检查、PG 与后台任务诊断、恢复边界 |
| `testing/` | 验证范围、结果及生产环境待验项 |
| `diagrams/` | 正文使用的两张 SVG；`source/` 是可编辑 drawio 原稿 |
| `archive/` | 历史版本与本次整理前备份，不作为部署依据 |

PG 插件见 [插件说明](deployment/postgresql-extensions.md)，CPU/内存/磁盘见 [资源说明](deployment/contextdb-resource-sizing.md)。首版为单容器 API/内置 Worker/UI；RDS 基础扩展为 vector、pg_trgm、btree_gin，采用 native 英文全文，中文分词全文仍为 TODO，PG SSL 可选。

## 维护规则

资料仓是人工文档的维护位置；[代码仓文档入口](https://github.com/ZhuQingping/hindsight/tree/contextdb/v1.0.0/hindsight-extensions/contextdb-service/docs)只提供链接。脚本、模板、测试和机器可读 OpenAPI 留在代码仓，版本对应及固定链接见[代码检视指南](design/code-review-guide.md)。

接口、配置或安全边界变化时，更新对应的当前文档与设计 TODO；不要在目录外新建另一份“最新版”。验证记录要注明代码与环境，不能用历史试验结果替代当前验收。查早期 V1/V2 讨论时从归档入口进入。

仓库持续维护正文、必要的SVG与可编辑图源、固定版本引用和人可读的验证摘要。原始抓取、批量JSON/CSV证据、整理前历史原稿、构建预览及生成资料包放在本机`.local-archive/`，由`.gitignore`排除；不推送该目录。本次整理不清除此前已发布的历史归档。
