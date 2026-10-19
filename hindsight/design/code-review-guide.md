# ContextDB 代码检视指南

更新：2026-10-19。当前功能基于原生 Hindsight v1.0.0，分支 `contextdb/v1.0.0`；完整功能相对原生集中为一个提交。管理 API 和元数据都从版本 1 开始，历史草稿中的 V1/V2 不代表已发布的升级合同。

## 版本对应

| 内容 | 固定版本 / 位置 |
| --- | --- |
| 原生父提交 | `39c65ffe2f140d0c84cee58566cad8900c5b9908`（v1.0.0） |
| 本次整理前的代码提交 | [c60d409](https://github.com/ZhuQingping/hindsight/commit/c60d409cfb4f879051a4fe258bbcaff8872df09e)；详细文档已移至资料仓，提交内 docs/README.md 为链接入口 |
| 当前代码 | [75ae4b7ed806c6c6e54d6306b9420e5fd9535014](https://github.com/ZhuQingping/hindsight/commit/75ae4b7ed806c6c6e54d6306b9420e5fd9535014)；本轮仅更新资料仓新路径的导航链接，运行代码与 c60d409 相同 |
| 当前人工文档 | [本目录总入口](../README.md)、[完整设计](contextdb-release-design.md)；以包含本次目录整理的资料仓提交为快照 |
| 机器接口合同 | [OpenAPI](https://github.com/ZhuQingping/hindsight/blob/75ae4b7ed806c6c6e54d6306b9420e5fd9535014/hindsight-extensions/contextdb-service/schemas/contextdb-control-plane.openapi.yaml)，由代码生成并校验 |

`c60d409` 的详细设计、部署指南、API 用例和运维手册由资料仓维护；本轮整理前完整目录见[备份](../archive/2026-10-19-before-reorganization/README.md)。代码仓只保留入口，不再双份同步人工文档。

## 专家检视顺序

先读[设计](contextdb-release-design.md)，再按下表查看相对 v1.0.0 的差异，不需要先通读历史过程记录。

| 范围 | 代码路径 | 重点 |
| --- | --- | --- |
| 原生接入 | `hindsight-api-slim/hindsight_api` | HTTP/MCP、引擎、Worker 的可选扩展与执行代次保护；其他租户扩展默认保持原生行为 |
| 外围实现 | `hindsight-extensions/contextdb-service/hindsight_ext_contextdb` | 统一 PG 认证、按 Key 授权、生命周期、元数据、管理 REST；记忆算法复用原生 |
| UI 与代理 | `hindsight-control-plane` | 工作空间/用户/Key、管理员登录、固定目标代理及原生 Bank 入口限制 |
| 部署 | 扩展包的 `deployment/`、`scripts/` | 单容器、离线初始化、配置与秘密持久化、RDS 插件及可选 PG SSL |
| 回归 | 扩展包 `tests/`、原生/API/UI/system tests | 权限、重建、在途保护、Append 冲突、进程退出及原生业务 |

```bash
# 先在本地检出下面固定提交；这些命令只读，不运行部署或测试。
git show --stat 75ae4b7ed806c6c6e54d6306b9420e5fd9535014
git diff 39c65ffe2f140d0c84cee58566cad8900c5b9908 75ae4b7ed806c6c6e54d6306b9420e5fd9535014 -- hindsight-api-slim/hindsight_api
git diff 39c65ffe2f140d0c84cee58566cad8900c5b9908 75ae4b7ed806c6c6e54d6306b9420e5fd9535014 -- hindsight-extensions/contextdb-service
git diff 39c65ffe2f140d0c84cee58566cad8900c5b9908 75ae4b7ed806c6c6e54d6306b9420e5fd9535014 -- hindsight-control-plane
```

## 当前评审边界

单容器 API 内置 Worker，独立 UI 进程；用户属于实例，Key 独立授权，selected 可逐空间读写/只读，all 包含未来空间。工作空间使用可读 bank_id 与 schema，内部 UUID 区分删除后同名重建对象。

原生 Trace/Audit 正文写入、Webhook 在自研首版关闭。中文分词全文、目标 ECS 容量、RDS 恢复、完整镜像安全验收等尚未完成，见[设计 TODO](contextdb-release-design.md#本轮实现收敛与-todo)及[验证摘要](../testing/contextdb-validation-summary.md)。本轮只整理文档及导航，不代表这些 TODO 已完成。

更早的 V1/V2 对照、未推送本机提交与过程检视见[整理前的版本说明](../archive/2026-10-19-before-reorganization/design/version-comparison.md)，不列为当前检视前置材料。
