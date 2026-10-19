# ContextDB V2 本地自测与验收记录

日期：2026-10-15。V2 本地自测通过，可用于多工作空间、多用户的功能体验；云管控和生产部署尚未完成验收。本记录汇总已有执行证据，本次文档归档没有重新运行业务测试。

## 版本与验证范围

| 项目 | 版本 / 范围 |
| --- | --- |
| 正式代码 | [contextdb/service-management-v2](https://github.com/ZhuQingping/hindsight/tree/contextdb/service-management-v2)，已推送 |
| 固定提交 | [d5e851b60315b79696e995874e7edc1e9a7bae23](https://github.com/ZhuQingping/hindsight/commit/d5e851b60315b79696e995874e7edc1e9a7bae23) |
| 上游基线 | `a77c1f3412a7b82f36588dffce1a8d7480e99cc7`；V1、V2 各自是此基线上的独立功能提交 |
| 测试环境 | 本地标准 PostgreSQL、真实 API/Worker、模型 stub；UI 使用 Next production build |
| 本机体验 | 两个工作空间 MySQL、PG；运行时代码与正式 V2 提交一致 |

正式提交整理后重新执行扩展和 UI 套件；系统黑盒、原生回归及真实 UI/后端联调沿用运行时代码一致的开发阶段证据。下面各批次不累计计数，也不代表远程 CI 或生产验收。

## 已执行结果

| 检查 | 结果 | 覆盖与限制 |
| --- | --- | --- |
| 正式分支扩展测试 | **242 passed**，无 skip/xfail | 元数据、用户/Key 授权、生命周期、PG 角色边界、随版 OpenAPI 合同 |
| 正式分支 UI 测试 | **46 个文件、343 passed**，UTC | 管理员准入、管理代理、用户/Key 操作与工作空间文案；未覆盖浏览器视觉布局 |
| ContextDB 系统黑盒 | **49 passed** | REST/MCP、多空间授权、撤权、嵌入式/独立 Worker、取消与删除排空；模型为 stub |
| 原生定向回归 | **41 passed** | 扩展、MCP、Worker 相关回归；不是全部上游测试 |
| production UI + 真实 API + 临时 PG | **2 passed** | 两种 Worker 模式；登录、用户/Key 创建、版本冲突、停用、未来空间可见与撤销后旧会话拒绝 |
| 构建与质量检查 | **通过** | Next production build、根 lint、扩展 Ruff、格式及 ty |
| 本地外部 Host/HTTPS 代理模拟 | **通过** | 仅本地模拟，实际云代理和网络策略未验收 |
| 本机 UI 只读检查 | **通过** | 登录、英文/中文页面、用户管理和 API 均返回 200；MySQL/PG 可见，两种语言的工作空间文案存在，各检查 13 个资源 |

业务权限的主要验收点包括：一把 Key 对 A 读写、B 只读、C 拒绝；同用户不同 Key 独立授权；用户范围与 Key grants 求交；移除授权或停用后旧 MCP 的下一请求被拒绝；管理员 all Key 能看到未来空间；普通 Key 不自动扩权。

生命周期测试覆盖 Console 专属工作空间创建/删除、原生 Bank 创建/删除/clone/import 等入口的限制、异步操作查询和在途请求/任务排空。删除后保留 schema、表结构及墓碑，不能按 schema 是否消失判断成功。客户受限 PG 角色与真正超级用户的反例均已测试；SUPERUSER/OS root 仍可绕过同库保护。

## 待完成的验收

| 项目 | 状态 | 下一步 |
| --- | --- | --- |
| 当前 V2 实例真实 MaaS Retain → Recall → Reflect 全流程 | **NOT_RUN** | 依验证手册完成中英文用例，核验模型结果、向量维度、检索与重排；此前模型接口单独调用成功不能替代本流程 |
| 云 Console / 管控 → 节点 Agent → API | **NOT_RUN** | 确认实际 Agent 协议、转发能力、凭据交付及任务 ID；按联调文档验证实例和空间流程 |
| 生产 PG 配置 | **待验证** | 本机体验库为 SQL_ASCII、`shared_preload_libraries` 为空；生产需 UTF8 新库，配置需要预加载的扩展并核验索引与查询 |
| 华为 RDS 客户高权限账号 | **NOT_RUN** | 在真实 RDS 验证角色边界，明确客户是否取得真正超级用户权限 |
| 实际云反向代理、HTTPS、私网与来源限制 | **NOT_RUN** | 按真实拓扑检查管理入口和 UI 准入 |
| 多副本迁移、故障隔离、备份恢复、容量与性能 | **NOT_RUN** | 单独完成生产专项验收；未知旧执行者未隔离前不强行清理屏障 |
| 浏览器视觉验收 | **NOT_RUN** | 人工检查工作空间切换、用户/Key 管理及中英文布局 |

本机体验库已安装 `vector 0.8.6`、`pg_trgm 1.6`、`btree_gin 1.3`、`pg_stat_statements 1.12` 和 `pgroonga 4.1.0`。扩展出现在 `pg_extension` 中，不等于预加载配置、索引及生产查询都已验收。

## 复验与证据入口

- [V2 验证与演示手册](contextdb-v2-local-validation-guide.md)：管理面、数据面、REST/MCP、UI 和 PG 的具体操作及预期结果。
- [部署与使用手册](contextdb-v2-deployment-usage-guide.md)、[环境变量清单](contextdb-v2-deployment-environment.md)：在其他机器准备新实例。
- [管控联调文档](../contextdb-v2-control-plane-integration.md)：实例开通、空间生命周期、重试与待确认的 Agent 调用合同。
- [夜间开发审阅记录](contextdb-tenant-admin-review-2026-10-15.md)：历史缺陷、修复及独立审阅。

本地证据文件：`v2-commit-result.json`、`v2-commit-extension-tests.log`、`v2-commit-ui-tests.log`、`v2-commit-root-lint.log`、`integration-report.md`、`integration-system-tests.log`、`integration-ui-real-backend.log`、`backend-native.log`；体验检查见 `ui-workspace-live.json`。归档目录为本机 `.local/night-runs/contextdb-tenant-admin-20261015`，体验证据位于 `test/hindsight_test/contextdb-v2-experience/20261015-104834-735ecc/evidence`，均相对本机 Context 工作目录。本公开仓库保存结果摘要，运行凭据和原始环境文件留在本机。
