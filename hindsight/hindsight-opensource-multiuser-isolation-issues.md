# Hindsight 开源版多人记忆隔离与知识共享讨论

更新日期：2026-10-10。本文整理 Hindsight GitHub issue、维护者回复、社区讨论及官方 cookbook 中，与多人共享、成员隔离和授权相关的关键信息，供 ContextDB 成员与 API Key 方案评审使用。

> 2026-10-12 范围更新：当前源码提供 `resolve_tag_scope` 与 `resolve_write_tag_scope`，默认不会自动按用户隔离。ContextDB 首期采用一工作空间一 schema、schema 内唯一 Bank，只实现空间/用户/Key 管理及认证，不实现强制用户 tag scope。本文的隔离建议是[后续研究](member-memory-isolation-future-notes.md)，不是首期能力；当前管理合同见[首期设计](member-apikey-bank-service-design.md)。

## 结论

Hindsight 开源版的主要隔离与共享边界是 **Tenant 和 Bank**，而不是 Bank 内的用户成员。开源版适合“每个用户一个 Bank”实现个人记忆隔离，也适合多个 Agent/客户端共同使用一个 Bank 实现共享；但不能仅凭不同 API Key、不同调用方或给记忆加了用户 tag，就认为同一 Bank 内的 memory 已经按用户隔离。

维护者在 [#2235](https://github.com/vectorize-io/hindsight/issues/2235) 表示，Hindsight 有意保持授权层简单：Bank 可用于团队隔离，团队内部可用 tags 区分用户数据，并由部署方 enforce。该回复表达了建议方向，并不等于 OSS 已提供完整、默认启用的成员 ACL。对 ContextDB 而言，若产品要求“同一工作空间内，个人记忆私有、知识共享”，需要在 Hindsight 外层或扩展层实现并强制执行身份绑定、查询过滤和资源授权。

## 关键概念与边界

| 概念 | Hindsight 中的作用 | 对成员隔离的含义 |
|---|---|---|
| Tenant | 通过 TenantExtension 解析请求所属的数据租户/schema | 默认开源 Tenant 扩展不是完整的企业成员与角色系统 |
| Bank | 租户中的记忆库，是主要的应用级数据分组/隔离边界 | 同一 Bank 的记忆、文档和知识资产处于同一数据范围；不能天然按成员区分 |
| API Key | 认证/路由凭据，具体权限取决于所使用的 Tenant/Auth 扩展 | 不应假定“不同 Key = 不同用户记忆空间”；必须明确 Key 到 tenant、bank、subject 和操作 scope 的映射 |
| tags / metadata | 可用于标记来源、分类和检索筛选 | 只有当服务端可信地写入并强制应用过滤时，才可参与授权；客户端可自行传入的 tag 不能单独构成安全边界 |

### 共享与隔离的实际模式

- **个人记忆隔离：**官方 cookbook 推荐每个用户一个 Bank。这是清晰的隔离模式，但 Bank 数量随用户增长，跨用户共享需额外设计。
- **Agent/客户端共享：**社区讨论建议多个 Agent 或工具共同读写同一 Bank，作为共享上下文。这适用于团队知识或协作记忆，不代表终端用户的个人记忆自动隔离。
- **个人 + 团队共享并存：**可在产品层采用个人 Bank 与共享 Bank 分区，再由 ContextDB 的认证授权层按成员和操作控制访问。若必须在同一 Bank 混存私有与共享记录，则需要可靠的行/记录级访问过滤与写入身份校验。

## 相关 issue 与社区结论

| Issue / 讨论 | 状态（2026-10-10） | 关键信息 | 对方案的意义 |
|---|---|---|---|
| [#2235 Team, agent, and memory-level access control](https://github.com/vectorize-io/hindsight/issues/2235) | Open | 讨论租户内组织/成员角色、私有与共享 memory、API Key scope、memory ACL 等。维护者认为各企业授权模型不同，Hindsight 刻意保持简单；建议 Bank 隔离团队、团队内使用 tags，并由部署方强制执行。 | 最直接的上游立场：复杂成员授权不是 OSS 默认产品能力，应由 wrapper、插件或扩展承接。tags 的强制执行责任在部署方。 |
| [#5449 Built-in multi-key tenant extension with per-key bank allow-list](https://github.com/vectorize-io/hindsight/issues/5449) | Open | 提议内置多 Key TenantExtension，并按 Key 限定 Bank。作者称现有单共享 Key 无法识别不同调用者；其自定义 TenantExtension + OperationValidatorExtension 可按 Bank 前缀授权。 | 说明多成员/多 Key、Bank ACL 是真实需求；该提案解决 Key → Bank 的授权，不提供同一 Bank 内的用户级 memory ACL。 |
| [#5448 `allowed_bank_ids` is declared but never enforced](https://github.com/vectorize-io/hindsight/issues/5448) | Open | 报告称 RequestContext 中的 `allowed_bank_ids` 字段没有被引擎读取，且指出特定接口遗漏 Bank 校验。 | 不能把上下文中存在权限字段当成权限已经生效。自定义扩展需逐个验证 REST、MCP、列表、读写及异步/特殊接口。 |
| [#3522 Per-document/chunk ACLs](https://github.com/vectorize-io/hindsight/issues/3522) | Closed（被标记为 #2235 重复） | 请求比 Bank 更细粒度的文档/Chunk ACL。 | 记录级授权仍归入更广泛的权限模型讨论，不能视作已具备的标准能力。 |
| [#2442 LangGraph 工具固定 bank_id 导致多用户共用 Bank](https://github.com/vectorize-io/hindsight/issues/2442) | Closed | 报告集成工具在创建时闭包固定 bank_id，未按每次请求中的 user 配置动态选择 Bank，可能把不同用户的数据写入同一个 Bank。 | 引擎层 Bank 隔离不能弥补客户端集成错误。验证所有 SDK/MCP/hook 的 Bank 路由是否按请求身份计算。 |
| [Discussion #1576 多 Agent 共享记忆](https://github.com/vectorize-io/hindsight/discussions/1576) | Discussion | 社区回复将多个工具/Agent 指向同一共享 Bank 视为常见协作模式。 | 支持“共享上下文”判断，但讨论的是 Agent/工具协作，不是多终端用户私有数据隔离。 |

维护者在 #2235 中还认可授权可以由 middleware 层接入组织认证（例如 Google Workspace、Okta），并指出可通过扩展机制定制。这说明扩展点适合承载策略，但产品方仍需自行设计策略数据、Key 生命周期、授权撤销和覆盖面测试。

## 对 ContextDB 的设计建议

### 推荐的语义分层

```text
云租户
  └─ 工作空间
      ├─ 成员个人记忆空间（成员不可互读）
      └─ 工作空间共享知识空间（按角色授权读写）
```

ContextDB 首期明确将一个工作空间映射为唯一 Bank，成员私有记忆和正式共享知识在其中按可信标签分域，插件强制检查身份、目标 Bank 和读写范围。此选择保留上游“一个用户一个 Bank”作为其他部署的模式参考，不要求客户端进行跨 Bank 遍历。

### 关键安全要求

1. **Key 必须绑定主体和资源范围：**至少能解析 tenant、workspace、成员/服务账号、允许访问的 Bank 与操作权限。API Key 只是凭据，不是授权规则本身。
2. **服务端派生用户身份：**retain 的 user 标识/标签应由认证上下文注入或校验，不能信任客户端自由提交的 `user_id`、tag 或 metadata。
3. **recall 与 reflect 必须强制过滤：**只在 retain 时加用户 tag 不够；所有检索、列表、详情、导出、知识页面、MCP、异步任务都要执行访问规则。
4. **共享知识与个人记忆分别授权：**团队可共享知识，不意味着团队成员应互相看到私人对话记忆。明确知识晋升、审核和撤回机制。
5. **覆盖所有访问路径：**扩展/gateway 的验证清单要覆盖 REST、MCP、SDK、控制面、文档导入/导出、后台任务及重试；对权限拒绝做 403 与无数据泄漏断言。
6. **撤销与审计：**成员禁用、角色变化、Key 撤销后，应按明确的生效时限失效；关键读写操作记录调用主体与授权决策。

若希望最小化对 Hindsight 源码的修改，优先在 ContextDB Gateway/授权层完成身份解析和 Bank 路由，并以 Hindsight 扩展补齐请求上下文与操作校验；但上线前必须通过越权测试证明每条调用路径都经过该层。不要把“使用 tags”或“不同 API Key”当作隔离已经完成的证据。

## 证据边界与复核范围

截至 2026-10-10，GitHub Search API 对 `repo:vectorize-io/hindsight is:issue` 返回 1,439 条 issue；单次搜索结果存在数量上限。本次按成员/用户隔离、共享 Bank、Tenant/API Key、ACL、权限过滤等主题筛选 open 与 closed 记录，并核读了上述直接相关 issue 的正文和维护者回复。结论依据社区公开讨论，不等于 Hindsight Cloud 内部实现披露，也不代替对 ContextDB 目标版本源码和运行时授权链路的安全审计。

## 参考资料

- [#2235 Team, agent, and memory-level access control](https://github.com/vectorize-io/hindsight/issues/2235)
- [#5449 Built-in multi-key tenant extension with per-key bank allow-list](https://github.com/vectorize-io/hindsight/issues/5449)
- [#5448 RequestContext.allowed_bank_ids enforcement report](https://github.com/vectorize-io/hindsight/issues/5448)
- [#3522 Per-document/chunk ACLs](https://github.com/vectorize-io/hindsight/issues/3522)
- [#2442 LangGraph multi-user bank routing issue](https://github.com/vectorize-io/hindsight/issues/2442)
- [Discussion #1576 Multi-agent shared memory](https://github.com/vectorize-io/hindsight/discussions/1576)
- [Hindsight Cookbook: Per-User Memory](https://github.com/vectorize-io/hindsight/blob/main/hindsight-docs/src/pages/cookbook/recipes/per-user-memory.md)
- [Hindsight Cookbook: Support Agent with Shared Knowledge](https://github.com/vectorize-io/hindsight-cookbook/blob/main/notebooks/03-support-agent-shared-knowledge.ipynb)
- [ContextDB 成员与 API Key 管理设计](member-and-apikey-management-design.md)
- [多 Bank 隔离与云化 Gateway 设计](bank-isolation-gateway.md)
