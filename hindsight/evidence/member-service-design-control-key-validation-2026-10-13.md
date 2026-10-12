# ContextDB 管理 Key 认证设计修订验证记录

日期：2026-10-13。对象：[主设计](../member-apikey-bank-service-design.md)、[OpenAPI](../api/contextdb-control-plane.openapi.yaml)、[架构图](../diagrams/README.md)及相关索引/设计摘要。本轮验证仅涉及设计资产，未实施服务代码或修改数据库、全局客户端配置及部署凭据；文档提交与推送记录以 Git 历史为准。

## 决策与信任边界

- 管理 REST 改为已有管控后端专用；节点不直接校验用户 IAM Token。用户登录、云权限和目标权限检查保留在管控。
- 管控使用 `X-ContextDB-Control-Key`，从已认证会话重建 `X-ContextDB-Actor-Subject`；必须覆盖客户自报内部身份/角色头。节点先认证专用 Key，再接受 actor，并按当前元信息复核空间角色、本人和目标归属。
- 内部 Key 只证明持有服务凭据，不独立证明人的身份；信任管控真实完成认证/授权。首个空间的云创建权限由管控检查，不能把匿名申请原样转发。
- 管理 Key 部署阶段生成，每租户独享实例独立，受保护配置注入；不进入用户业务 Key 表，不下发浏览器，不默认获得业务 REST/MCP 权限。支持轮换、撤销及全副本配置生效检查。
- 公共业务入口不路由管理别名和原始 `/ext/contextdb/v1` 路径；内部入口限制管控来源并使用 HTTPS。共享进程不能成为暴露未保护直连路由的理由。
- 管理接口仍为 14 个，只有 admin/member 两种角色；`iam_subject` 保留为与管控登录身份的绑定，不是新增 IAM 验证适配器。同 Bank 记忆共享语义和个人隔离延期不变。

## 验证

| 检查 | 结果 | 范围 |
|---|---|---|
| OpenAPI 3.0.3 结构/引用 | PASS | Swagger CLI 4.0.4 校验；版本 0.3.0-draft |
| 认证及权限合同一致性 | PASS | 全部 14 操作继承 ControlPlaneKey；7 条路径均要求可信 actor；角色仅 admin/member；活动合同无旧 IAM 认证方案或 security 覆盖 |
| Markdown 链接/锚点/代码块/空白及 Key 脱敏 | PASS | 检查 7 份 Markdown，失败项为空；新命令仅使用占位符 |
| Mermaid 源及 SVG | PASS | 两张修改图用 Mermaid CLI 12.0.0 重新生成并查看 PNG，无文字裁切；检查 3 个 SVG，产品关系图未改变 |
| git diff --check | PASS | 无补丁空白错误；不纳入无关未跟踪研究文件 |
| 真实管控登录/权限/转发、管理 Key 认证与网络限制 | NOT_IMPLEMENTED / NOT_RUN | 本次没有编写扩展、调用服务或配置生产入口；合同通过不等于实现通过 |
| 管理 Key 生成/轮换/撤销/日志及全副本生效 | NOT_RUN | 只有配置与验收约定，没有生成或使用真实凭据 |
| SDK/MCP/PG 端到端与个人记忆隔离 | NOT_RUN | 未改服务/数据；用户私有记忆不属于本期实现 |

复现结构验证：

```bash
npx --yes --package @apidevtools/swagger-cli@4.0.4 swagger-cli validate \
  hindsight/api/contextdb-control-plane.openapi.yaml
git diff --check
```

Mermaid 生成方式见[图说明](../diagrams/README.md)，仅使用临时 Puppeteer 配置指向本机已有 Chrome；不修改浏览器或 Agent 的全局配置。

旧 [2026-10-12 IAM 草案验证](member-service-design-doc-validation-2026-10-12.md)保留为历史证据，已加替代说明；不把当日 IAM 结果改写成新方案的实现证据。
