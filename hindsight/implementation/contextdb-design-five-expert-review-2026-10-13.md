# ContextDB 首期设计五专家局部复核

日期：2026-10-13。对象：[主设计](../member-apikey-bank-service-design.md)、管理 OpenAPI、关联研究及前序实现记录。

结论：保留现有首期方案，仅校准文档。五类专家代理完成首轮审核及修订后复核，均接受本轮限定范围的修订；没有提出必须立即改变架构的事项。Hindsight 开发者是技术审核角色，不代表官方维护者背书。

源码已实现并有前序代理自测，但用户尚未检视代码/验收，生产联调也未完成。本报告不是代码发布批准、完整安全审计或上线验收。

## 本轮边界

- 保持云租户独享计算引擎与 PG、同库 ctxdb_meta、每空间单 schema/单 Bank、admin/member 和成员多 Key。
- 保持新增管理接口仅内部 REST、仅供管控后端；原生 REST/MCP 协议不变，原生接口裁剪另行评估。
- 不增加组织、项目、MetaPG、节点 IAM、用户记忆 ACL、配置热加载或自动故障恢复。
- 五位专家只读；主代理集成文字校准。没有改源码、DDL、运行配置、权限模型、原始测试结果，没有提交/推送。
- 主文档保持原目录/章节及 9 表、16 操作；相对此轮送审稿仅 28 行插入、6 行删除，没有全文重写。

## 审核结果

| 专家代理 | 主要检查与已关闭发现 | 修订后结论 |
|---|---|---|
| 资料专家 materials_design_review | 9 表/7 索引/16 操作及测试证据；纠正共享 MCP Token 约束、用户未验收状态及关联研究中的历史首期门槛 | scoped ACCEPT |
| 文档专家 human_document_review | 首屏状态、模块阅读关系、计算引擎/API/Worker 职责、Key 到期与轮换措辞 | scoped ACCEPT |
| agent memory 专家 agent_memory_design_review | 同 Bank 共享修改/删除、业务 scope 实际范围、MCP 重试提示、47 项测试的场景/辅助区分 | scoped ACCEPT |
| PG 专家 pg_database_design_review | 首响应等待、无 TTL 人工恢复、连接预算、schema 权限边界、数据库约束与服务规则 | scoped ACCEPT |
| Hindsight 开发者 hindsight_developer_design_review | 原生补丁部署、默认 hook、配置加载、原生协议兼容和删除受理语义 | scoped ACCEPT WITH RISKS |

五类结论都只针对本轮文档校准。首轮发现是当前实现事实的表达或交付说明问题，已通过短句修订闭合；并不表示每位专家重新运行了全部测试或用户已经验收。

## 局部优化及依据

| 优化 | 实现/问题依据 |
|---|---|
| 明确“代理自测完成，用户验收未完成” | 既有 JUnit 和日志只证明前序代理执行；云联调/容量/恢复仍未完成 |
| 说明管理角色不保护个人内容，共享包含编辑/删除 | validator 的 scope/Bank 校验不比较内容成员所有权；memory.write 可编辑共享文档和派生内容 |
| 明确 memory.read 范围与独立 knowledge.read | 原生 profile gate 同时覆盖审计/LLM trace/原始导出；不等于新增管理 REST 或 ctxdb_meta 管理审计授权 |
| 明确管理任务在 API 进程内，Worker 消费原生数据任务 | http.py 启动 Lifecycle；无需新增生命周期服务 |
| 区分动态资源管理与启动配置 | Settings 在构造时加载；管理 Key/来源网络/pepper 无热加载，通常通过滚动重启重新加载 |
| 明确共享 MCP Token 已被拒绝，不是待验证的可选兼容项 | config.py 检测 HINDSIGHT_API_MCP_AUTH_TOKEN 即拒绝启动，动态 Key 不可被旧共享 Token 绕过 |
| 明确 DELETE 202 前可能先等待请求退出 | Repository 先取得空间 FOR UPDATE；系统 103 用例明确断言同步业务执行期间 DELETE 尚未返回 |
| 明确 owner_id 非 PID、恢复负责人及维护窗口影响 | 请求异常/断锁留下持久记录；未知旧执行者不可按年龄或单个 PID 消失推定结束 |
| 补充连接预算、schema/PG 账号边界及版本检查限制 | API 两个额外池各 max_size=10；无每空间独立 PG role；版本表检查不核验实际列/索引 |
| 明确需带原生边界补丁部署 | ASGI/入队 hook、MCP 上下文、知识读取来源等已实现；不是只复制扩展目录即可部署 |
| 校准历史测试说明和竞品研究状态 | 系统包 47 项含 41 个真实进程场景及 6 个辅助回归；私有记忆/完整审计为后续候选 |

代码依据为本地 `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/` 及原生引擎改动；具体开发问题见[开发记录 D4、D9、D12–D22](contextdb-service-night-task-2026-10-13.md)。未以文本调整代替代码修复。

## 保留现有保护的理由

- 同库独立连接池对应 D4 已复现的连接等待问题；仍是同一个 PG，不增加 MetaPG。
- request_admissions 对应 D20 的“元信息锁已消失、旧数据事务仍可能晚提交”窗口；独立池不能替代持久屏障。
- 租约等待后检查对应 D18；迁移不跨长元信息事务对应 D12，避免并发建索引的快照阻塞。

这些机制已实现，本轮没有删除或重构。人工恢复和 DDL 不具备强执行者隔离保证是已披露限制，必须在用户验收/上线前确认操作流程与演练结果。

## 需用户另行同意的变化

本轮没有执行或认定必须实施的新架构变化。若后续希望改变 DELETE 首响应等待、限制成员编辑他人内容、拆分审计/trace 的 scope、增加自动恢复/配置热加载、调整空间存储拓扑或新增公开 pool accessor，须先讨论并获得用户同意，再独立修改代码及验证。

当前建议先检视并验证已实现版本，保留已有方案；不得通过删除屏障、强行清空记录或减少验收门槛来宣称更快上线。

## 本轮验证与证据边界

| 检查 | 状态 |
|---|---|
| 五位专家全文/定向源码只读审核及修订后复核 | RUN；各自报告未写文件、未运行 DB/服务 |
| 相关源码/测试/依赖文件哈希前后比较 | RUN；131 条相关文件记录不变 |
| 文档/DDL 9 表、7 显式索引；16 操作/OpenAPI；本地链接与目录锚点 | RUN，PASS；主设计哈希与五位复核版本一致 |
| 管理 OpenAPI schema 校验及实际路由/响应字段合同测试 | RUN，schema 有效，合同测试 1 passed；仅既有第三方弃用告警，不代表全面功能或生产验证 |
| 前序 175/175/47/41、lint 及原始证据 SHA-256 | 只读核对，未改原始结果；重复 175 不累加，47 非全真实服务场景 |
| 全套功能测试、真实数据库/模型、云管控、多副本容量/恢复演练 | NOT_RUN；本轮未修改运行时代码，用户验收尚待开展 |

送审主设计 SHA-256：`e205f1c0bb626bcec9e9f14660932c8aed827f52a07973155079462b4005946e`。

五位最终复核的主设计 SHA-256：`533f8ae698406dbf04df3a6b5f5842930b9499242b2d43655ea3956c2db5f51a`。

本轮定向命令：源码仓 `PYTHONPATH=hindsight-extensions/contextdb-service .venv/bin/python -m pytest hindsight-extensions/contextdb-service/tests/test_openapi_research_contract.py -q`，退出码 0；研究仓 `npx --yes @apidevtools/swagger-cli validate hindsight/api/contextdb-control-plane.openapi.yaml`、`git diff --check` 均退出码 0。另用只读解析核对 method/path、DDL、Markdown 锚点及原始证据哈希。未运行全仓自动修复 lint 或依赖同步。

源码仓 HEAD：`a77c1f3412a7b82f36588dffce1a8d7480e99cc7`；研究仓 HEAD：`74ab76872c3e9c226df7902a17955252156b46d7`。审核对象包含此前未提交/未跟踪的实现与文档，不能用 HEAD 链接冒充本地新增代码。
