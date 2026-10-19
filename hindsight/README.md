# Hindsight 服务化文档

当前代码基于原生 Hindsight v1.0.0，全部特性集中在一个提交中。首版一个容器运行 API/内置 Worker 和 UI；RDS 全文使用 native + english，不要求 PGroonga/Groonga；数据库 SSL 可选，默认示例不指定 sslmode。

| 阅读目的 | 文档 | 适用范围 |
| --- | --- | --- |
| 确认管控输入、PG、模型、端口与凭据 | [原生部署合同](native-v1.0.0/contextdb-deployment-contract.md) | 官方 Hindsight v1.0.0，不含自研权限和元数据 |
| 按命令完成部署与联调 | [原生联调操作指南](native-v1.0.0/contextdb-service-integration-guide.md) | 首版单容器；脚本及模板链接固定到代码提交 |
| 评审总体架构、接口、PG 表和安全边界 | [特性设计](design/contextdb-release-design.md) | ContextDB 自研扩展版 |
| 查看剩余优化项 | [设计文档 TODO](design/contextdb-release-design.md#本轮实现收敛与-todo) | 后续设计讨论统一在此维护 |
| 核对已实施改动与测试依据 | [优化实施状态](design/contextdb-optimization-status.md) | 历史证据按文内快照区分 |
| 按范围检视代码 | [版本与代码对比](design/version-comparison.md#专家检视顺序) | 原生接入、外围扩展、UI、部署、测试分开查看 |
| 部署自研扩展版 | [部署合同](design/contextdb-deployment-contract.md) / [联调指南](design/contextdb-service-integration-guide.md) | 不能与原生认证和初始化混用 |
| 了解资源开销和采样 | [CPU、内存与磁盘说明](design/contextdb-resource-sizing.md) | 示例限制与实测分开，生产规格待压测 |
| 定位故障与验证接口 | [运维手册](design/contextdb-operations-runbook.md) / [curl 用例](design/contextdb-optimized-curl-guide.md) | 原生排障跳过自研专属元数据命令 |

## 版本来源与代码评审

- 代码仓：[ZhuQingping/hindsight](https://github.com/ZhuQingping/hindsight)
- 分支：`contextdb/v1.0.0`
- 同步提交：[`00770662e`](https://github.com/ZhuQingping/hindsight/commit/00770662e52a5368432d65563eb07517a7329060)，已推送；一个完整特性提交。
- 原生基线：`v1.0.0` / `39c65ffe2f140d0c84cee58566cad8900c5b9908`，也是特性提交的直接父提交。
- [完整代码差异](https://github.com/ZhuQingping/hindsight/compare/39c65ffe2f140d0c84cee58566cad8900c5b9908...00770662e52a5368432d65563eb07517a7329060)；[代码仓特性入口](https://github.com/ZhuQingping/hindsight/tree/00770662e52a5368432d65563eb07517a7329060/hindsight-extensions/contextdb-service)。
- 同步时间：`2026-10-19T11:13:38+08:00`；[同步清单](design/sync-manifest.json)记录每个源文件与副本的 SHA-256。

## 维护规则

代码仓为准，资料仓保存同步阅读副本。设计和 TODO 先在代码仓特性设计文档更新，再同步这里；副本不独立维护另一套方案。优化实施状态解释已经完成的工作及验证依据，不另建重复待办。

同步 `docs/native-v1.0.0/` 到本目录 `native-v1.0.0/`，其余当前 `docs/` 材料到 `design/`，保留图示、drawio原稿及引用证据。副本仅增加来源标注和调整链接，不删改设计正文；每次记录源提交、日期及摘要。

部署脚本与配置模板保留在代码仓。副本中的源文档、脚本、模板链接均固定到上述提交，不依赖作者本机路径。在其他环境检出同一代码提交，再按指南设置 HELPERS/REPO 等实际路径；不要用过期材料或直接使用未经核对的 latest。

本目录其他草稿保留作历史对照，当前部署和评审从本页进入。原生模式使用原生共享 Key/Bank，不含自研多用户及逐空间授权。自研设计仍处于内部评审，未开放能力及目标ECS/RDS验收以设计边界和 TODO 为准。
