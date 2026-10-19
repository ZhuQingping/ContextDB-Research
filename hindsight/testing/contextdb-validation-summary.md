# ContextDB 验证摘要

更新：2026-10-19。适用于基于原生 Hindsight v1.0.0 的 ContextDB 代码；[版本对应](../design/code-review-guide.md)。本页汇总已有验证证据，本次目录整理没有重新执行完整业务测试，也不新增生产验收结论。

## 最近验证

| 范围 | 结果 | 说明 |
| --- | --- | --- |
| ContextDB 扩展全量 | 439 通过，1 可选跳过 | c60d409 提交前最近一次全量，31.96 秒；2 条基线 SWIG 警告 |
| OpenAPI | 生成校验通过 | 机器定义迁至 schemas/ 后内容不变 |
| 提交检查 | lint、提交钩子通过 | 人工文档改为资料仓链接入口 |

## 此前同一运行实现的回归与部署证据

| 范围 | 记录 | 不能据此推出的结论 |
| --- | --- | --- |
| 原生单元、UI、SDK 系统回归 | 原生 233 通过；UI 407 通过并完成生产构建；系统 406 通过、1 可选 ONNX 跳过 | 不代表每个上游可选功能均支持 |
| 自研与原生官方单容器 | 真实 MaaS retain/recall/reflect、UI、异步任务；自研权限、删除重建、进程退出与重启验证 | 不代表云上 HA 或性能达标 |
| 不含 PGroonga 的新库 | 基础扩展、非超级用户、原生英文 GIN/SQL 全文与真实 MaaS/异步路径核验 | 不是实际华为云 RDS 验收；中文向量召回不等于中文关键词全文 |
| PG SSL 输入 | 原生/自研的省略、disable、verify-full 共 6 种渲染检查 | 验证 URL 原样传递，不替代目标 PG 证书与网络测试 |

历史过程和当时的环境条件可从[整理前验证材料](../archive/2026-10-19-before-reorganization/design/contextdb-service-research-validation.md)、[优化与历史验证](../archive/2026-10-19-before-reorganization/design/contextdb-optimization-status.md)追溯。原始测试输出、临时容器配置及含凭据材料留在本机私密制品目录，不进入资料仓。Colima ARM 测试使用过 `OPENSSL_armcap=0` 兼容覆盖，正式镜像未写入；目标 ECS 原样镜像启动仍须验收。

## 上线前待完成

目标 ECS/RDS 上的原样启动、插件版本、权限与网络验证；混合业务容量及延迟压测；备份/PITR、故障恢复与全镜像安全检查；中文关键词全文选型与实现。完整决策与 TODO 统一在[设计](../design/contextdb-release-design.md#本轮实现收敛与-todo)维护。

手工功能和权限验证请使用[当前 API/curl 手册](../api/contextdb-management-api-curl-guide.md)，部署请使用[当前联调指南](../deployment/contextdb-service-integration-guide.md)，不要执行归档中的旧部署命令。
