# ContextDB 验证摘要

更新：2026-10-19。本轮验证针对 `contextdb/v1.0.0` 简化后的实现，修改前特性提交为 `1b96e97584fda118efc5dc6c7cb76d5236060563`；官方原生基线为 v1.0.0（`39c65ffe2f140d0c84cee58566cad8900c5b9908`）。本轮通过 amend 整理提交，代码提交正文固定资料仓快照；尚未推送，不代表远程旧提交包含本轮修改。

## 本轮结果

| 范围 | 结果 | 实际覆盖与边界 |
| --- | --- | --- |
| ContextDB 扩展全量 | **317 通过，无跳过** | 真实隔离 PG：认证/授权、同步生命周期、六表约束、schema 归属及依赖、故障清理、同名重建、SQL 次数、部署配置与安全。真实非超级用户新库重复 init 两次，验证秘密不变及原生 public 初始化 |
| UI 全量 | **415 通过，50 个文件** | 两入口名称/描述共享表单、512字符描述、取消重开、同步创建/删除、未知结果、条件删除及原生 UI 回归；固定 TZ=UTC，避免原有相对日期测试受本机时区跨日影响 |
| UI 生产构建 | **通过** | 隔离工作树使用默认 Turbopack，经正式 build-ui 重新构建并生成 manifest，完整校验源码与 bundle 匹配；未替换现有9999产物 |
| ContextDB 黑盒 | **60 通过** | 内置及独立 Worker 两种模式，真实 API/PG、发布的 Python SDK、REST/MCP、生产 UI 登录及代理、工作空间/成员/Key 管理、逐空间权限、记忆/知识库、默认模板及故障后清理。含外部 UI 构建验证边界；模型服务使用确定性替身 |
| 原生相关回归 | **1304 通过，5 原生跳过** | 66个相关文件，覆盖原生 Bank/索引/文件、Worker、MCP、连接池、配置与全部16项取消测试；使用真实 PG 与确定性 embedding/rerank，不是上游全套或模型质量验收 |
| 严格原生 dotenv | **另有5项通过** | 独立导出官方源文件验证；与上行覆盖重叠，不累加为新增覆盖 |
| 静态检查 | **通过** | 仓库 lint 脚本、扩展 Ruff/类型检查、UI 类型检查、OpenAPI 生成一致性、差异空白检查；资料脚本语法/JSON与相对链接检查通过 |
| 独立检视 | **无阻断性问题** | Hindsight 与 PG 专家分别只读检视；已采纳授权表反向索引及过时注释修正，补充指令写权限显式回归。结论以本轮规格为前提，不恢复执行屏障 |

原生回归选取65个测试文件及 conftest 与官方基线一致；另一个是已有特性扩展的 dotenv 文件，官方原版另行导出验证。默认 pytest 输出捕获下有一项原生 CLI `CliRunner` 关闭缓冲区错误，在纯官方 v1.0.0 同样复现；以 `-s` 关闭外层捕获后，原断言通过，未改原生源码或删除该断言。5项跳过是原生自定义 MCP 对照例外及缺少可选本地 ML 依赖的直接构造用例。没有声称默认捕获模式或全部可选后端已验收。

本轮把7个原生运行文件全部恢复为官方内容，原生运行目录相对官方 v1.0.0 无差异。同步管理的实现与回归集中在扩展及 UI；管理异步调度、持久准入、额外连接池、执行代次和故障回调相关测试随已删除的增强承诺移除，普通权限、身份条件及原生取消回归保留。

## 验证环境与证据

测试使用任务自有 pg0 实例、临时目录和随机端口；未停止或替换现有 API8888、UI9999、PG5432，未调用真实 MaaS 或使用客户凭据。生产 UI 的实际 HTTP 登录、同源校验和管理代理故事已通过；本轮未完成浏览器截图验收，操作期间浏览器被用户切换，未继续争用现有窗口。

本机证据目录：`/tmp/contextdb-simplification-night-20261019.L6810v`。关键文件为 `extension-final-second.log`、`system-contextdb-second.log`、`ui-form-review-tests.log`、`ui-build-stamped.log`、`native-final-tests.log`、`native-report.md`、`repository-lint-final.log`、`hindsight-final-review.md`、`pg-final-review.md`。日志和临时配置不提交资料仓；目录不是长期制品存储，转测时应按团队流程留存非秘密报告。

## 历史证据与上线前待完成

此前真实 MaaS、单容器部署、PG SSL 渲染和 PGroonga 试验对应旧实现，保留于[历史验证材料](../archive/2026-10-19-before-reorganization/design/contextdb-service-research-validation.md)。不能以这些结果宣称本轮原样容器、真实模型或目标云环境已经通过。Colima ARM 曾使用 `OPENSSL_armcap=0` 兼容覆盖，正式镜像未写入该覆盖。

目标 ECS/RDS 原样启动、插件版本/权限/网络、混合负载及延迟、备份/PITR和故障恢复、依赖与镜像安全仍须验收。首版 native+english 覆盖英文全文，中文向量可用性不能替代中文关键词全文验收。R05可信固定镜像免启动扫描仍为 TODO，当前完整校验保留。后续事项统一在[设计 TODO](../design/contextdb-release-design.md#本轮实现收敛与-todo)维护。

工作空间删除前须由管理员停止新业务，并等待已受理请求与原生后台工作结束；本版不提供并发删除重建时的完整执行隔离。手工验证使用[API/curl 手册](../api/contextdb-management-api-curl-guide.md)，部署使用[联调指南](../deployment/contextdb-service-integration-guide.md)。
