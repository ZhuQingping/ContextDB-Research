# Hindsight / ContextDB 文档

当前实现基于 **Hindsight v1.0.0**，代码分支 `contextdb/v1.0.0`。本目录只将一套当前文档放在主目录中；旧方案、重复手册和过程记录放入 [archive](archive/README.md)。完整设计与实现细节保留，未按篇幅删减。本轮同步管理简化已在本地实现，本地回归与 Hindsight/PG 独立检视已完成（见验证摘要）；本轮以 amend 整理为一个代码提交及配套资料提交，尚未推送，远程旧评审提交不包含本轮简化。

## 从这里开始

| 你要做什么 | 先看哪份 |
| --- | --- |
| 理解方案、评审架构 | [完整设计](design/contextdb-release-design.md) |
| 查看简化实施状态、核对依赖与验收 | [简化与实施清单](design/contextdb-simplification-plan.md) |
| 检视相对原生 Hindsight 的代码改动 | [代码检视指南](design/code-review-guide.md) |
| 查看管理 API、参数、返回值并执行测试 | [API 与 curl 手册](api/contextdb-management-api-curl-guide.md) |
| 部署自研 ContextDB | [联调操作指南](deployment/contextdb-service-integration-guide.md)；配置字段查 [部署合同](deployment/contextdb-deployment-contract.md) |
| 先对接官方原生 Hindsight | [原生联调操作指南](deployment/native-v1.0.0/contextdb-service-integration-guide.md) · [原生部署合同](deployment/native-v1.0.0/contextdb-deployment-contract.md) · [部署工具](deployment/native-v1.0.0/tools/) |
| 运行问题定位、恢复 | [运维手册](operations/contextdb-operations-runbook.md) |
| 了解验证结果及尚未覆盖的环境 | [验证摘要](testing/contextdb-validation-summary.md) |

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
