# ContextDB 首期管理设计文档验证记录

日期：2026-10-12。对象：[首期管理设计](../member-apikey-bank-service-design.md)、[后续记忆隔离备忘](../member-memory-isolation-future-notes.md)、[OpenAPI](../api/contextdb-control-plane.openapi.yaml)和[架构图](../diagrams/README.md)。

本轮按用户要求收窄：本期只实现工作空间、用户、API Key 管理及必需认证/空间授权。用户记忆私有/共享知识的 tag 策略、发布工作流和成员任务私有适配不进入本期。管理 IAM Token 与业务随机 Key 明确分开；HttpExtension 的新增 Router 必须自行加管理认证依赖。

认证理解补充：第一把 ContextDB Key 使用已有 IAM Token 申请，不是匿名调用；创建 Key 路径中的 member_id 是目标用户，不是调用者身份。补充认证/云权限/空间与本人授权的判定表，明确当前采用用户 IAM Token 管理 REST，而非只允许后台服务调用的内部接口。相关文字、时序图与现有 OpenAPI 一致，未新增服务实现或改动管理操作数量。

| 检查 | 结果 | 范围 |
|---|---|---|
| 管理 OpenAPI 3.0.3 | PASS，14 个操作，0.2.0-draft | Swagger CLI 4.0.4 结构/引用检查；不验证真实 IAM 授权 |
| 认证与范围合同 | PASS | 管理安全方案为 X-Auth-Token；用户 role 仅 admin/member；去除 knowledge/publications 和 publish_knowledge |
| Mermaid 生成/视觉检查 | PASS，3 张 SVG | 查看 PNG；关系图不再声称私人记忆，服务图/时序图区分 IAM 与业务 Key |
| Markdown 代码块/本地链接/空白 | PASS | 文档资产存在且语法检查通过 |
| 原生扩展与 schema 接口核对 | PASS | 原生 HttpExtension、TenantExtension、OperationValidator 和迁移/Worker hook 存在；tag hook 默认不提供用户策略 |
| git diff --check | PASS | 无补丁空白错误 |
| Cloud 行为证据 | 复用历史实测 + 当前官方文档核对 | SMIC 相同记忆 ID 跨 Key 可见；控制台路由与 scoped 子 Key 能力分开说明；未重新登录核对完整管理认证协议 |
| 真实管理 IAM、Key、空间权限与 SDK/MCP 端到端 | NOT_RUN | 未编写服务代码、创建 schema、迁移数据或调用商业管理写接口 |
| 个人记忆隔离 | NOT_IMPLEMENTED / NOT_RUN | 仅保留证据与候选 tag 思路；不作为本期功能验收 |
| 混合负载性能与多 schema 升级 | NOT_RUN | 工作空间表独立不等于 PG 资源独享或性能互不影响 |

固定源码基线为 a77c1f3412a7b82f36588dffce1a8d7480e99cc7。原生接口签名检查不证明 ContextDB 的 IAM 适配器、角色策略或动态管理已经实现。Cloud UI 的完整 Cookie/JWT/Token 交换未捕获，不把业务 Bearer 实测外推为所有管理接口的认证方式。

协议对比文档中 2 处历史明文 Hindsight Key 已换为占位符，保留命令结构，不使用/撤销该 Key。脱敏不会移除 Git 历史或其他副本，若仍有效，应由凭据负责人评估轮换。

管理草案从 15 个操作收窄到 14 个：删除共享知识发布路径；原管理 Bearer 草案改为原生 IAM X-Auth-Token 头。OpenAPI 中 apiKey 类型只是表示自定义请求头位置，不代表 IAM Token 与 ContextDB API Key 是同一种凭据。

验证阶段未修改全局 Agent 配置、服务代码或数据库；文档提交与推送记录以 Git 历史为准。本轮交付为设计资产，不是上线结果。
