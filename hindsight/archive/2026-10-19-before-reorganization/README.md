# Hindsight 服务化文档

这里统一维护设计、部署、运维和图表；代码仓docs只链接这里，不再双份同步。实现基于原生Hindsight v1.0.0，当前功能基线为[00770662e](https://github.com/ZhuQingping/hindsight/commit/00770662e52a5368432d65563eb07517a7329060)，分支 `contextdb/v1.0.0`。

## 代码检视：先读两份

1. [完整特性设计](design/contextdb-release-design.md)：总体架构、资源关系、核心实现、接口、PG表、安全依据、边界和TODO。图表直接随正文阅读，无须先浏览图表目录。
2. [代码对比与检视顺序](design/version-comparison.md#专家检视顺序)：按原生接入、外围扩展、UI、部署和测试分组检查。

设计正文及实现细节完整保留；不要求检视人先通读部署命令、调研过程和历史验收。

## 部署和使用：按任务选择

| 任务 | 文档 |
| --- | --- |
| 部署官方原生Hindsight v1.0.0 | [部署合同](native-v1.0.0/contextdb-deployment-contract.md) · [联调操作指南](native-v1.0.0/contextdb-service-integration-guide.md) |
| 部署自研ContextDB版本 | [部署合同](design/contextdb-deployment-contract.md) · [联调操作指南](design/contextdb-service-integration-guide.md) |
| 手工验证功能和权限 | [curl用例](design/contextdb-optimized-curl-guide.md) |
| 运行问题定位 | [运维手册](design/contextdb-operations-runbook.md) |

原生与自研版本的认证、初始化不同，不混用两套合同。当前首版为单容器API/内置Worker/UI；RDS使用native英文全文与基础扩展，中文分词全文待适配，PG SSL可选。

<details>
<summary>需要时查阅的配套资料</summary>

- [CPU、内存与磁盘说明](design/contextdb-resource-sizing.md)：示例与实测分开，生产规格待压测。
- [PG插件说明](design/postgresql-extensions.md)。
- [优化实施与历史验证](design/contextdb-optimization-status.md) · [专题调研](design/contextdb-service-research-validation.md)：用于追溯，不代替当前设计和TODO。
- 两张图：[总体架构](design/diagrams/contextdb-first-release-architecture.svg) · [工作空间、用户与Key关系](design/diagrams/contextdb-first-release-workspace-model.svg)。SVG用于阅读，drawio原稿和PNG导出留存，不是额外架构方案。
- [管理接口定义参考](https://github.com/ZhuQingping/hindsight/blob/00770662e52a5368432d65563eb07517a7329060/hindsight-extensions/contextdb-service/docs/contextdb-control-plane.openapi.yaml)：机器合同以代码仓的schemas目录和生成器校验结果为准。

</details>

## 维护约定

资料仓是人工文档的唯一维护位置；代码仓保留实现、部署材料、测试和机器可读接口定义。这里的文档不再标记为“代码仓同步副本”，也不要求两处复制。新增设计决策和TODO统一写入特性设计，不再另建重复清单。

提交代码时同步更新相关设计，并在提交或PR中记录代码和资料的对应版本；当前专题调研和历史测试按文内原有基线理解。首次迁入来源可追溯到[资料提交ee44cb2](https://github.com/ZhuQingping/ContextDB-Research/commit/ee44cb2433017ef8026d7b5483cdcb8e0c97b522)，无需保留逐文件同步清单。

部署脚本及模板仍使用固定代码版本；操作指南中的链接已绑定功能基线。在其他机器检出对应代码后再设置HELPERS/REPO等实际路径。其他早期草稿保留作对照，当前评审和部署从本页进入。
