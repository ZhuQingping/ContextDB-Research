# 原生 v1.0.0 接口权限对照与 Bank 管理统一评估

> **版本说明（2026-10-22）：** 本文保留问题复现、评审和过程记录；旧的“独立worktree／未提交”描述不代表当前状态。当前代码为本地提交`9fb57bc04`（父提交003bbe032，未推送），已修复项和剩余边界以[当前设计](contextdb-release-design.md)及[最新验证](../testing/contextdb-validation-summary.md)为准。Audit继续关闭，O02及外部环境等未验项不记为通过。


更新：2026-10-21。状态：源码检视完成，方案建议待确认；不修改代码，不将建议当成已实施。

## 1. 基线、范围和阅读方式

- 原生：官方Release v1.0.0，提交 `39c65ffe2f140d0c84cee58566cad8900c5b9908`。
- 当前策略：`contextdb/quality-20261021-004226`工作树，c56c7ac17基线加本轮未提交质量修复（含提示词预览限制）；不是只读原仓旧提交。
- 枚举原生http.py全部100项显式REST路由、BankReadOperation全部32项、BankWriteOperation全部40项、PrecheckOperation全部7项、原生_ALL_TOOLS全部39个MCP工具。补充生命周期与外围拦截。此范围不包含其他独立MCP程序、扩展自行注册接口、框架自动生成的文档路由或其他可选后端。
- R=已授权空间的只读业务Key；W=读写业务Key；A=实例Admin Key。允许表示自研策略允许，仍受原生参数、配置开关、资源状态和目标授权约束，不等于每个入口已经真实运行验收。A不绕过当前原生生命周期限制。
- 表中的权限是组合策略结果：Transport、Tenant、Validator、MCP工具过滤、部署限制都可能进一步收紧。未知操作默认拒绝与已知能力遗漏需分别判断。
- 本次RUN：AST枚举、源码链路走读、默认拒绝集合差集核对。NOT RUN：100个REST入口和所有MCP工具的逐项在线验证、Bank API新方案原型、性能测试。

## 2. 关键发现及建议

| 级别 | 发现 | 判断及建议 |
| --- | --- | --- |
| Important | 六个原生写操作落入默认拒绝：UPDATE_BANK、CREATE/DELETE_BANK_ALIAS、CREATE/UPDATE/DELETE_WEBHOOK | Webhook已定恢复；UPDATE_BANK需按字段拆分身份与展示属性，不能笼统视为改bank_id；别名需入口解析适配 |
| Important | 原生Bank.name是仍兼容但已标deprecated的展示名，bank_id是稳定标识 | 更新展示名不等于重命名Bank或schema；当前拒绝Admin展示名更新有过度限制，应允许Admin更新展示属性，不能靠放行任意业务Key处理 |
| Important | MCP隐藏Admin的update_bank，而REST对既有Bank的纯config更新路径可能允许 | 工具隐藏、字段授权和REST行为不一致；恢复时逐字段验证，不把整个PUT/PATCH简单标成一律拒绝 |
| Important | 默认拒绝只覆盖一个层面；别名、模板导入、归档导入/克隆被外围先挡住 | 只把操作加入Validator允许集无法恢复这些接口；必须检查Transport及schema初始化 |
| Important | 单Key多schema的Bank创建/删除不可能只靠前置Validator维护完整生命周期 | 创建前需Admin身份认证及schema准备；成功后需元数据状态、授权及schema清理。复用Bank URL可以简化接口，不消除这些职责 |
| Important | 恢复Trace/Audit/Webhook已定案，代码仍拒绝 | 不能把文档目标写成已开放；按O05实施与组合验收 |
| Minor | 文档导入、模板导入、整库恢复不是同一能力 | POST /document-transfer导入现有空间的文档是内容写路径；不应把所有“import”都认作生命周期操作 |

**总建议：REVISE。** 保留动态权限默认拒绝和独立schema的安全边界，纠正已知能力的不必要禁用。对全部已知操作显式分类，增加“枚举全覆盖”测试；以后原生新增操作使测试失败并要求分类，不能用Admin无条件允许所有未知操作掩盖遗漏。

## 3. 原生REST接口完整对照

前缀 `B` = `/v1/default/banks/{bank_id}`。下面逐项列出全部100项。必要性/恢复方式同时列出；“扩展”不代表无需完整生命周期适配。

| # | 原生方法与路径 | 原生用途 | 当前策略 | 限制必要性、恢复方式 |
| --- | --- | --- | --- | --- |
| 1 | `GET /health` | Health check endpoint | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 2 | `GET /health/ready` | Readiness probe | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 3 | `GET /health/live` | Liveness probe | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 4 | `GET /version` | Get API version and feature flags | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 5 | `GET /v1/version` | version_endpoint | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 6 | `GET /metrics` | Prometheus metrics endpoint | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 7 | `GET B/graph` | Get memory graph data | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 8 | `GET B/memories/list` | List memory units | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 9 | `POST B/memories/dry-run-extract` | Dry-run fact extraction (preview, no persistence) | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 10 | `POST B/prompts/preview` | Preview an operation's prompts (no LLM call) | 仅A | 运维信息/完整导出边界，保留；文档导出可另评W需要的最小权限，不因此全部开放 |
| 11 | `GET B/memories/{memory_id}` | Get memory unit | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 12 | `PATCH B/memories/{memory_id}` | Curate memory unit | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 13 | `GET B/memories/{memory_id}/history` | Get observation history | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 14 | `POST B/memories/recall` | Recall memory | R/W/A | 保留，Reflect会调用模型但不据此要求W；是否有副作用遵循原生 |
| 15 | `POST B/reflect` | Reflect and generate answer | R/W/A | 保留，Reflect会调用模型但不据此要求W；是否有副作用遵循原生 |
| 16 | `GET /v1/default/banks` | List memory banks | 动态Key；扩展合并可见空间目录 | 保留可见性隔离；跨schema列表由外围聚合，不能直接读一个schema替代 |
| 17 | `GET B/stats` | Get statistics for memory bank | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 18 | `POST B/health/llm` | Test the bank's LLM connectivity | R/W/A，目标空间认证 | 原生通过GET_BANK_STATS读授权，允许状态探测并可能消耗模型调用；是否进一步限Admin属于产品策略，当前没有这样限制 |
| 19 | `GET B/stats/memories-timeseries` | Memory ingestion time-series | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 20 | `GET B/entities` | List entities | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 21 | `GET B/entities/graph` | Get entity co-occurrence graph | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 22 | `GET B/entities/{entity_id}` | Get entity details | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 23 | `POST B/entities/{entity_id}/regenerate` | Regenerate entity observations (deprecated) | 原生已废弃，合法空间请求通常410 | 不是自研功能遗漏，不恢复已退役端点；非法空间可能被外围先拒绝 |
| 24 | `GET B/mental-models` | List mental models | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 25 | `GET B/mental-models/{mental_model_id}` | Get mental model | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 26 | `GET B/mental-models/{mental_model_id}/history` | Get mental model history | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 27 | `POST B/mental-models` | Create mental model | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 28 | `POST B/mental-models/{mental_model_id}/refresh` | Refresh mental model | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 29 | `POST B/mental-models/{mental_model_id}/dry-run-refresh` | Dry-run mental model refresh (preview, no persistence) | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 30 | `POST B/mental-models/{mental_model_id}/clear` | Clear mental model content | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 31 | `PATCH B/mental-models/{mental_model_id}` | Update mental model | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 32 | `DELETE B/mental-models/{mental_model_id}` | Delete mental model | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 33 | `GET B/knowledge-base/tree` | Get the knowledge-base tree | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 34 | `POST B/knowledge-base/folders` | Create a knowledge-base folder | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 35 | `POST B/knowledge-base/pages` | Create a knowledge-base page | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 36 | `GET B/knowledge-base/export` | Export the knowledge base as a markdown bundle | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 37 | `GET B/knowledge-base/search` | Hybrid search over knowledge pages (BM25 + vector) | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 38 | `GET B/knowledge-base/pages/{page_id}` | Get a knowledge-base page | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 39 | `PATCH B/knowledge-base/nodes/{node_id}` | Rename/move a knowledge-base node or update a page's options | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 40 | `DELETE B/knowledge-base/nodes/{node_id}` | Delete a knowledge-base node | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 41 | `GET B/directives` | List directives | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 42 | `GET B/directives/{directive_id}` | Get directive | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 43 | `POST B/directives` | Create directive | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 44 | `PATCH B/directives/{directive_id}` | Update directive | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 45 | `DELETE B/directives/{directive_id}` | Delete directive | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 46 | `GET B/documents` | List documents | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 47 | `GET B/documents/{document_id:path}/chunks` | List document chunks | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 48 | `POST B/documents/{document_id:path}/reprocess` | Reprocess document | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 49 | `GET B/documents/{document_id:path}` | Get document details | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 50 | `GET B/tags` | List tags | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 51 | `GET /v1/default/chunks/{chunk_id:path}` | Get chunk details | R/W/A；解析canonical chunk目标 | 保留授权；拒绝歧义旧编码，不遍历schema |
| 52 | `PATCH B/documents/{document_id:path}` | Update document | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 53 | `DELETE B/documents/{document_id:path}` | Delete a document | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 54 | `GET B/operations` | List async operations | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 55 | `GET B/operations/{operation_id}` | Get operation status | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 56 | `DELETE B/operations/{operation_id}` | Cancel a pending or in-flight async operation | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 57 | `POST B/operations/{operation_id}/retry` | Retry a failed async operation | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 58 | `DELETE B/operations/{operation_id}/delete` | Delete a terminal async operation | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 59 | `GET B/profile` | Get memory bank profile (removed — use GET .../config) | 原生已废弃，合法空间请求通常410 | 不是自研功能遗漏，不恢复已退役端点；非法空间可能被外围先拒绝 |
| 60 | `PUT B/profile` | Update memory bank disposition (removed — use PATCH .../config) | 原生已废弃，合法空间请求通常410 | 不是自研功能遗漏，不恢复已退役端点；非法空间可能被外围先拒绝 |
| 61 | `POST B/background` | Add/merge memory bank background (removed — use PATCH .../config) | 原生已废弃，合法空间请求通常410 | 不是自研功能遗漏，不恢复已退役端点；非法空间可能被外围先拒绝 |
| 62 | `GET B/aliases` | List the bank's aliases | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 63 | `POST B/aliases` | Add an alias to the bank | A/R/W均被Transport拒绝；写钩子也拒绝 | 别名不是迁移schema；可通过扩展解析alias→canonical并防跨空间冲突后恢复A管理，不直接放行 |
| 64 | `PATCH B/aliases/{alias}` | Show this alias in place of the bank id | A/R/W均被Transport拒绝；写钩子也拒绝 | 别名不是迁移schema；可通过扩展解析alias→canonical并防跨空间冲突后恢复A管理，不直接放行 |
| 65 | `DELETE B/aliases/{alias}` | Remove an alias from the bank | A/R/W均被Transport拒绝；写钩子也拒绝 | 别名不是迁移schema；可通过扩展解析alias→canonical并防跨空间冲突后恢复A管理，不直接放行 |
| 66 | `PUT B` | Create or update memory bank | 新Bank拒绝；既有Bank含name更新拒绝；纯config更新A可通过原生对应路径 | 展示名限制过强；扩展适配创建/更新，保留Admin和schema绑定；空/不同字段组合须补黑盒 |
| 67 | `PATCH B` | Partial update memory bank | 新Bank拒绝；既有Bank含name更新拒绝；纯config更新A可通过原生对应路径 | 展示名限制过强；扩展适配创建/更新，保留Admin和schema绑定；空/不同字段组合须补黑盒 |
| 68 | `DELETE B` | Delete memory bank | A/R/W均不能直接删Bank | 当前统一走workspace管理；建议由原生Bank入口调用同一外围生命周期 |
| 69 | `POST B/import` | Import bank template | A/R/W均被Transport拒绝 | 一刀切过强；模板dry_run/更新现有对象、documents模式、创建新目标需分开适配；仅放Validator不够 |
| 70 | `GET B/export` | Export bank template | 仅A | 运维信息/完整导出边界，保留；文档导出可另评W需要的最小权限，不因此全部开放 |
| 71 | `GET B/document-transfer` | Export documents (removed — use POST .../document-transfer/export) | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 72 | `POST B/document-transfer/export` | Export documents (async) | 仅A | 运维信息/完整导出边界，保留；文档导出可另评W需要的最小权限，不因此全部开放 |
| 73 | `POST B/document-transfer` | Import documents (async) | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 74 | `POST B/transfer/export` | Export a bank (async) | 仅A | 运维信息/完整导出边界，保留；文档导出可另评W需要的最小权限，不因此全部开放 |
| 75 | `POST B/transfer/import` | Import a bank (async) | A/R/W均被Transport拒绝 | 一刀切过强；模板dry_run/更新现有对象、documents模式、创建新目标需分开适配；仅放Validator不够 |
| 76 | `POST B/clone` | Clone a bank (async) | A/R/W均被Transport拒绝 | 一刀切过强；模板dry_run/更新现有对象、documents模式、创建新目标需分开适配；仅放Validator不够 |
| 77 | `GET B/attachments/{attachment_id}` | Fetch an attachment retained inline with a document | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 78 | `GET /v1/default/files/download/{key:path}` | Download a stored file (async export archive) | 仅A | 运维信息/完整导出边界，保留；文档导出可另评W需要的最小权限，不因此全部开放 |
| 79 | `GET /v1/bank-template-schema` | Get bank template JSON Schema | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 80 | `DELETE B/observations` | Clear all observations | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 81 | `GET B/observations/scopes` | List observation scopes | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 82 | `POST B/consolidation-strategies/preview` | Preview consolidation strategies | R/W/A，目标空间认证 | 经list_observation_scopes读授权，只做策略匹配预览，不持久写入 |
| 83 | `POST B/consolidation/recover` | Recover failed consolidation | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 84 | `DELETE B/memories/{memory_id}/observations` | Clear observations for a memory | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 85 | `GET B/config` | Get bank configuration | A可读允许字段；R/W字段投影为空 | 当前产品策略，保留凭据过滤；是否允许业务读非敏感配置可独立讨论 |
| 86 | `PATCH B/config` | Update bank configuration | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 87 | `DELETE B/config` | Reset bank configuration | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 88 | `POST B/consolidate` | Trigger consolidation | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 89 | `POST B/webhooks` | Register webhook | GET仅A；POST/PATCH/DELETE连A也拒绝；当前启用记录阻止启动 | 写拒绝是已确认缺口；已定恢复全局/Bank能力，扩展补A写权限并撤销启动阻断 |
| 90 | `GET B/webhooks` | List webhooks | GET仅A；POST/PATCH/DELETE连A也拒绝；当前启用记录阻止启动 | 写拒绝是已确认缺口；已定恢复全局/Bank能力，扩展补A写权限并撤销启动阻断 |
| 91 | `DELETE B/webhooks/{webhook_id}` | Delete webhook | GET仅A；POST/PATCH/DELETE连A也拒绝；当前启用记录阻止启动 | 写拒绝是已确认缺口；已定恢复全局/Bank能力，扩展补A写权限并撤销启动阻断 |
| 92 | `PATCH B/webhooks/{webhook_id}` | Update webhook | GET仅A；POST/PATCH/DELETE连A也拒绝；当前启用记录阻止启动 | 写拒绝是已确认缺口；已定恢复全局/Bank能力，扩展补A写权限并撤销启动阻断 |
| 93 | `GET B/webhooks/{webhook_id}/deliveries` | List webhook deliveries | GET仅A；POST/PATCH/DELETE连A也拒绝；当前启用记录阻止启动 | 写拒绝是已确认缺口；已定恢复全局/Bank能力，扩展补A写权限并撤销启动阻断 |
| 94 | `POST B/memories` | Retain memories | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 95 | `POST B/files/retain` | Convert files to memories | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 96 | `DELETE B/memories` | Clear memory bank memories | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 97 | `GET B/audit-logs` | List audit logs | 仅A可读历史；新增正文强制关闭 | 读权限保留；正文开启按O05恢复，不提供不可丢失保证 |
| 98 | `GET B/audit-logs/stats` | Audit log statistics | 仅A可读历史；新增正文强制关闭 | 读权限保留；正文开启按O05恢复，不提供不可丢失保证 |
| 99 | `GET B/llm-requests` | List LLM request traces | R/W/A按空间可读历史；新增Trace强制关闭 | 开启按O05恢复；现有空间读取权限不等于只给A，正文披露边界须组合测试 |
| 100 | `GET B/llm-requests/stats` | LLM request statistics | R/W/A按空间可读历史；新增Trace强制关闭 | 开启按O05恢复；现有空间读取权限不等于只给A，正文披露边界须组合测试 |

**共同限制：** 所有目标空间先校验已登记的canonical bank_id及格式；不支持借原生Retain隐式建立未登记空间。业务Key的GET任务列表/详情裁剪Webhook敏感诊断，include_payload=true仅A；表格普通任务GET的R/W允许不包含完整负载。模板/归档导出为A，知识库export单独属于knowledge.read，不能一概禁止。配置health、LLM健康等仍可受原生开关与资源状态限制。

## 4. Validator操作完整对照

下表说明外部客户调用；原生internal Worker另按已登记bank/schema、tenant UUID和空间状态校验，不重新用客户Key认证已受理任务。创建/删除的受信管理上下文不等于客户可传internal=true。

### 4.1 BankReadOperation：32项

| 操作 | 当前Validator | 外围附加限制及必要性 | 扩展恢复判断 |
| --- | --- | --- | --- |
| `EXPORT_KNOWLEDGE_BASE` | R/W/A，knowledge.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_BANK_CONFIG` | R/W/A，memory.read | 业务GET config字段被投影为空；不回显凭据 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_BANK_PROFILE` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_BANK_STATS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_CHUNK` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_DIRECTIVE` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_DOCUMENT` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_ENTITY` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_ENTITY_GRAPH` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_ENTITY_STATE` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_GRAPH_DATA` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_KNOWLEDGE_BASE_TREE` | R/W/A，knowledge.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_KNOWLEDGE_PAGE` | R/W/A，knowledge.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_MEMORIES_TIMESERIES` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_MEMORY_UNIT` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_MENTAL_MODEL_HISTORY` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_OBSERVATION_HISTORY` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_OPERATION_STATUS` | R/W/A，memory.read | include_payload额外限A；业务Webhook任务诊断裁剪 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_BANK_ALIASES` | R/W/A，memory.read | 只允许canonical目标；别名写入/解析恢复另算 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_DIRECTIVES` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_DOCUMENT_CHUNKS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_DOCUMENTS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_ENTITIES` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_MEMORY_UNITS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_MENTAL_MODEL_TAGS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_MENTAL_MODELS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_OBSERVATION_SCOPES` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_OPERATIONS` | R/W/A，memory.read | include_payload额外限A；业务Webhook任务诊断裁剪 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_TAGS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_WEBHOOK_DELIVERIES` | A，且检查memory.read | 保留Admin诊断权限；Webhook写/启动禁用另算 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_WEBHOOKS` | A，且检查memory.read | 保留Admin诊断权限；Webhook写/启动禁用另算 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `SEARCH_KNOWLEDGE_BASE` | R/W/A，knowledge.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |

### 4.2 BankWriteOperation：40项

“必要性”不以代码默认拒绝作为依据；六项默认拒绝均明确列出。

| 操作 | 当前Validator | 限制必要性、恢复方式 |
| --- | --- | --- |
| `CANCEL_OPERATION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `CLEAR_MENTAL_MODEL` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `CLEAR_OBSERVATIONS` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `CLEAR_OBSERVATIONS_FOR_MEMORY` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `CREATE_BANK_ALIAS` | 默认拒绝，且Transport先拦截 | 别名可恢复但需canonical解析和跨空间无歧义规则；不需要搬迁schema |
| `CREATE_DIRECTIVE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `CREATE_KNOWLEDGE_FOLDER` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `CREATE_KNOWLEDGE_PAGE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `CREATE_MENTAL_MODEL` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `CREATE_WEBHOOK` | 默认拒绝，A也拒绝 | 非必要永久限制；已确认通过扩展恢复A操作 |
| `DELETE_BANK` | 仅受信workspace删除；内容清空经专用标识允许A | 可由统一Bank生命周期适配入口复用；不可只改为Admin就跳过元数据清理 |
| `DELETE_BANK_ALIAS` | 默认拒绝，且Transport先拦截 | 别名可恢复但需canonical解析和跨空间无歧义规则；不需要搬迁schema |
| `DELETE_DIRECTIVE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `DELETE_DOCUMENT` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `DELETE_KNOWLEDGE_NODE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `DELETE_MENTAL_MODEL` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `DELETE_OPERATION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `DELETE_WEBHOOK` | 默认拒绝，A也拒绝 | 非必要永久限制；已确认通过扩展恢复A操作 |
| `IMPORT_DOCUMENTS` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `MERGE_BANK_MISSION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `MOVE_KNOWLEDGE_NODE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `RENAME_KNOWLEDGE_NODE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `REPROCESS_DOCUMENT` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `RESET_BANK_CONFIG` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `RETRY_FAILED_CONSOLIDATION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `RETRY_OPERATION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `RUN_CONSOLIDATION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `SET_BANK_MISSION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `SUBMIT_ASYNC_CONSOLIDATION` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `SUBMIT_ASYNC_GRAPH_MAINTENANCE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `SUBMIT_ASYNC_VECTOR_INDEX_MAINTENANCE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_BANK` | 默认拒绝，A也拒绝 | 展示名/mission更新不等于bank_id变更；应补A字段授权。不同入口config路径另算 |
| `UPDATE_BANK_CONFIG` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `UPDATE_BANK_DISPOSITION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `UPDATE_DIRECTIVE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_DOCUMENT` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_KNOWLEDGE_PAGE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_MEMORY_UNIT` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_MENTAL_MODEL` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_WEBHOOK` | 默认拒绝，A也拒绝 | 非必要永久限制；已确认通过扩展恢复A操作 |

### 4.3 其他钩子和前置操作

| 钩子 | 当前策略 | 结论 |
| --- | --- | --- |
| validate_create_bank | 只允许受信生命周期调用；Admin直接原生创建也拒绝 | 新Bank无schema/元数据，需外围创建流程；不能仅放行钩子 |
| validate_retain / validate_consolidate / validate_mental_model_refresh | memory.write | W/A；原生自动整合和内容派生任务继续保留 |
| validate_recall / validate_mental_model_get | memory.read | R/W/A |
| validate_reflect | reflect | R/W/A，当前权限投影均包含reflect |
| bank_list_scope | 返回当前目标的可读Bank；内部维护按schema取Bank | 根列表由扩展聚合；单schema原生列表不能代表全部空间 |
| filter_mcp_tools | 业务按读写范围；A允许原生工具集减create/update/delete_bank | 目录隐藏不是执行授权，不能用目录出现证明可调用 |
| validate_memory_update | 未覆盖该可选钩子，沿用原生默认 | 不能据此判越权；对应修改仍经UPDATE_MEMORY_UNIT及Tenant，需黑盒组合确认 |
| 其余通知/计量回调 | 沿用原生基类默认，不等于新增权限检查 | 不宣称自研提供原生Cloud完整IAM、审计或配额 |

- `precheck.DRY_RUN_EXTRACT`：W/A，memory.write；前置检查通过不替代完整操作授权。
- `precheck.FILES_RETAIN`：W/A，memory.write；前置检查通过不替代完整操作授权。
- `precheck.MENTAL_MODEL_CREATE`：W/A，memory.write；前置检查通过不替代完整操作授权。
- `precheck.MENTAL_MODEL_REFRESH`：W/A，memory.write；前置检查通过不替代完整操作授权。
- `precheck.RECALL`：R/W/A，memory.read；前置检查通过不替代完整操作授权。
- `precheck.REFLECT`：R/W/A，reflect；前置检查通过不替代完整操作授权。
- `precheck.RETAIN`：W/A，memory.write；前置检查通过不替代完整操作授权。

## 5. 原生MCP工具完整对照

以下为原生工具全集；单Bank模式本来就不提供全部管理工具，这是原生模式差异，不是自研遗漏。原生全局/Bank工具allowlist仍可进一步收窄。表内不把“隐藏”与“执行拒绝”混为同一机制。

| 原生工具 | 业务R | 业务W | Admin | 必要性与恢复 |
| --- | --- | --- | --- | --- |
| `cancel_operation` | 隐藏/拒绝 | 隐藏/拒绝 | 可见，实际执行仍经钩子 | A运维边界，保留；业务如需再单独讨论 |
| `clear_memories` | 隐藏/拒绝 | 隐藏/拒绝 | 可见，实际执行仍经钩子 | A运维边界，保留；业务如需再单独讨论 |
| `clear_mental_model` | 隐藏/拒绝 | 隐藏/拒绝 | 可见，实际执行仍经钩子 | A运维边界，保留；业务如需再单独讨论 |
| `create_bank` | 隐藏/拒绝 | 隐藏/拒绝 | 隐藏/拒绝 | 统一Bank API方案需让MCP也调用同一生命周期，不能只恢复目录 |
| `create_directive` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `create_knowledge_folder` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `create_knowledge_page` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `create_mental_model` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `delete_bank` | 隐藏/拒绝 | 隐藏/拒绝 | 隐藏/拒绝 | 统一Bank API方案需让MCP也调用同一生命周期，不能只恢复目录 |
| `delete_directive` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `delete_document` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `delete_knowledge_node` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `delete_mental_model` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_bank` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_bank_stats` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_document` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_knowledge_base_tree` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_knowledge_page` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_memory` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_mental_model` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_operation` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `invalidate_memory` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_banks` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_directives` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_documents` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_memories` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_mental_models` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_operations` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_tags` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `recall` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `reflect` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `refresh_mental_model` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `retain` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `search_knowledge_base` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `sync_retain` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `update_bank` | 隐藏/拒绝 | 隐藏/拒绝 | 隐藏/拒绝 | 应补Admin更新展示属性，现有整工具隐藏过强 |
| `update_knowledge_node` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `update_memory` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `update_mental_model` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |

## 6. 复用Bank API作为工作空间管理：明确结论

**长期候选方向，暂不实施：工作空间是产品展示名，评估API统一采用原生Bank资源、减少独立workspace CRUD。现有工作空间管理接口继续保留，不删除、不切换调用方。** 保留ctxdb_meta中的空间身份/授权/schema登记，它是Bank的服务化元数据，不是第二套可独立存在的业务资源。此为候选方案，不是当前实施清单；须先完成隔离原型、充分测试和兼容性评估，再确认是否实施，尚未变更现有接口合同。

| 接口职责 | 建议外部入口 | 外围仍需做什么 |
| --- | --- | --- |
| 创建或更新 | PUT /v1/default/banks/{bank_id} | Admin；新对象登记UUID、创建schema并迁移、调用原生Bank实现、成功激活/失败状态；已有对象按原生字段更新，不重复迁移 |
| 更新已有对象 | PATCH /v1/default/banks/{bank_id} | 按原生create_if_missing=false，不因PATCH隐式创建；Admin更新展示属性/配置，稳定bank_id不变 |
| 列表 | GET /v1/default/banks | 复用现有跨schema目录聚合及Key可见性，不另建workspace列表资源 |
| 删除 | DELETE /v1/default/banks/{bank_id} | Admin；调用同一生命周期，清理Key授权、元数据及专属schema；保留停流量约束 |
| 详情 | 原生列表/已有Bank详情工具，按客户端需要选取 | 原生http.py没有GET /banks/{bank_id}，/profile也已410；不能声称直接复用这个不存在的GET。若确需单对象REST详情，明确只新增一个Bank详情适配或用列表定向查询，另评契约 |

**为什么不能直接删管理代码、只放行Admin。**

1. 原生Tenant认证在Bank操作前执行，现有认证要求目标已经登记且active；新Bank还不存在metadata/schema，不能正常进入原生create。
2. 原生Bank写入只在选定schema操作，不负责给每个Bank新建schema；原生的validate_create_bank是前置校验，并非完整创建事务扩展槽。
3. 原生delete_bank删Bank数据，不负责删除ctxdb_meta授权/登记或DROP专属schema，Validator也没有可靠的“原生删除提交后”通知。把跨资源写入塞进验证钩子会产生失败残留和重复调用风险。
4. 因此，最小方案仍是扩展HTTP适配层在原生URL处接管生命周期分派，复用现有Lifecycle/原生引擎操作；使用原生路径不等于不需要外围实现。MCPExtension的create_bank/delete_bank也必须接入同一服务，否则REST能管理而MCP仍拒绝。

**简化收益与保留成本。**

- 可删除独立/ext/contextdb/v1/workspaces的列表/详情/创建/删除契约及专用OpenAPI/UI调用分支，减少Bank与workspace双资源概念。
- 可恢复Admin通过原生Bank URL及SDK操作，不再要求客户掌握第二套路由。
- 仍保留一次外围创建/删除协调、schema迁移、动态Key权限、UUID、目录聚合、失败状态和元数据清理；不能承诺核心管理代码全部删除或复杂度骤降。
- PUT原生是创建或更新；现workspace POST是严格创建201/冲突409。不能机械换URL而保持另一套隐蔽语义。原生PUT/PATCH返回BankProfileResponse、DELETE返回DeleteResponse，现接口201/204、ETag要求及UUID查询需重做契约取舍；不强制给原生SDK增加必传If-Match。内部仍可使用UUID/版本，删除同名重建与旧请求边界按已接受的停流量约束处理。
- description不是原生CreateBankRequest的等价现成字段，是否保留metadata描述或映射到独立展示字段需明确；不能把mission当空间描述。展示name（原生已标deprecated，但仍兼容）与稳定bank_id区分，更新name不改schema；命名要求仍受PG schema长度和metadata唯一约束，复用URL不会自动恢复任意原生bank_id。
- 别名仍需全局入口alias→canonical解析，模板导入/恢复/克隆仍需分别适配目标创建、现有内容导入或两空间权限。API统一后这些问题不会自动消失。

## 7. 后续可执行的验证与取舍

1. 枚举40项write、32项read和MCP全集，测试每项都显式归类；增加Admin、R、W的对应负例/正例，避免新枚举静默落默认拒绝。默认拒绝继续保留给未审定的新操作。
2. 优先补UPDATE_BANK的展示名/mission/config字段组合，验证PUT已有/不存在、PATCH已有/不存在；别把展示名修改误当bank_id迁移。
3. 按已定O05恢复Trace/Audit/Webhook，重点检查组合任务正文与诊断凭据边界。
4. Bank API方案先做插件内原型：Admin原生SDK创建、更新、列出、删除，普通Key不能创建；新schema/metadata一致，失败后可查询核对。验证MCP相同能力而非只恢复工具清单。
5. 单独评模板dry_run、更新现有空间、documents/restore模式、克隆新目标、别名；不能用权限放行替代目标schema及metadata协调。
6. 文档接口表的“允许”只是源码结论；逐接口黑盒、取消/超时、并发与失败注入NOT RUN，后续不得据此称原生功能全部验收。

本次只新增检视分析文档，不修改源码、既有设计合同或运行实例，不提交/推送。审核结论为REVISE，待确认Bank API合同及恢复范围后再实施。


## 8. Bank API统一方案暂缓实施决定（2026-10-21）

**暂不删除工作空间管理接口，暂不切换UI、SDK或其他调用方。** 该方案涉及管理入口、创建/更新语义、返回值、schema与元数据生命周期、权限以及MCP入口，属于相对较大的接口调整。第6章保留为后续研究方案，不作为当前获准实施项，也不作为O04/O05的前置依赖。

重新决定实施前，至少完成：

1. 隔离原型证明Admin可通过原生Bank API及SDK创建、更新、列出和删除，MCP使用同一生命周期；普通业务Key不能绕过权限。原型不替换现有服务入口。
2. 新schema、元数据、授权一致性及失败清理测试；创建/删除部分失败、超时、断连和并发场景有明确结果核对方式，符合已接受的生命周期约束。
3. 原生PUT创建或更新、PATCH不创建、响应结构、错误码、名称/描述、详情查询及现有条件请求的合同逐项明确；对UI、管控和SDK调用方进行影响评估。
4. 原生相关回归与插件REST/MCP/UI端到端验证充分通过，覆盖两种Worker、权限隔离、删除同名重建；证据和未完成项可供检视。
5. 基于验证结果另行确认切换范围与步骤，再将候选方案转为实施任务。

现有workspace接口继续维护。接口权限遗漏、Trace/Audit/Webhook恢复等已明确事项可独立推进，但不因此自动允许原生Bank生命周期绕过现有元数据管理。本文其他恢复建议仍按各自决定和验收标准处理。本次仅更新文档，不修改代码、接口或运行环境。
