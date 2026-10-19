# ContextDB 同 Bank 用户记忆隔离后续研究

更新日期：2026-10-12。本文记录问题、证据和候选思路，不属于[首期管理服务设计](member-apikey-bank-service-design.md)的实现/验收范围。首期不提供同 Bank 的用户私有记忆承诺。

## 结论与论据

Hindsight 不是完全无法表达隔离，而是默认没有“Key 绑定用户 → 自动按用户隔离记忆”的产品能力。工作空间独立 schema 解决空间之间的数据对象隔离，不解决同空间 Bank 内的成员隔离。

| 论据 | 能确认什么 | 不能确认什么 |
|---|---|---|
| [SMIC 商用实测](evidence/hindsight-cloud-cross-key-smic-2026-10-10.md)：key1 一次 Retain，key1/key2 各一次 Recall，均 200，返回相同 world 与 observation ID | 在两 Key 和该 Bank 的配置中，key1 写入对 key2 可见；不同 Key 本身不构成隔离 | 未证明两 Key 对应不同 Cloud 成员；未测反向写入，不能外推所有组织/成员配置 |
| 开源 TenantContext 主要返回 schema_name，Bank 查询按 bank_id 限定；用户归属来自我们自己的元信息映射 | Tenant/schema 和 Bank 是原生范围；Key 用户映射不是自动的 memory 行授权 | 不能通过 metadata.user_id、来源人名或前端成员筛选声明权限已生效 |
| [OperationValidatorExtension](https://github.com/vectorize-io/hindsight/blob/a77c1f3412a7b82f36588dffce1a8d7480e99cc7/hindsight-api-slim/hindsight_api/extensions/operation_validator.py) 的 resolve_tag_scope / resolve_write_tag_scope 默认返回 None | 上游提供可实现同 Bank 范围控制的 hook，但默认不按用户缩小读写范围 | 插件存在不等于我们的策略已开发、所有入口/派生任务已验证 |

SMIC 实测返回相同的 observation `d197cda9-a82b-449d-ac70-c938bd221cfc` 和 world `6141abf2-d9de-4be0-9241-fdbd71e421ea`；对应 tags 为空。原始请求/响应留在证据文件中，本次没有再次调用商业服务。

首期有 memory.read 的用户可读取本 Bank 的记忆，不区分写入用户；有写能力时也不能假设只能修改“自己”的内容。使用场景应限定为允许工作空间内共享的数据，不应写入依赖用户隔离保护的隐私内容。

## 候选方案与上游扩展

一种低侵入方向是“稳定用户 ID + 服务端强制 tag scope”，不是让客户端自觉传 tags：

1. Key 认证解析稳定 member_id，同一用户多 Key 不产生多个记忆主体。
2. 私人内容由服务端注入 `ctxdb:owner:<member_id>`，正式共享内容用 `ctxdb:shared:<workspace_id>`；客户端不能冒充他人或自行写共享权限标签。
3. resolve_tag_scope 强制读取“本人范围 + 获准共享范围”，使用 strict 过滤，与客户端查询取交集；resolve_write_tag_scope 只允许本人及受控标签，共享内容只由受控发布流程写入。
4. validate_retain/accept_with(contents=...) 可注入标签，但还须检查 document_tags、文档替换/追加、策略生成标签和 observation_scopes，不能只覆盖 item.content。
5. 私人 Observation 采用显式 owner scope，共享 Observation 采用 shared-tag scope。原生 observation_scopes="shared" 表示无标签 Observation，不等于经过确认的共享知识，不能直接用于私人数据整理。
6. Mental Model、Knowledge Page 及后台刷新必须持久化并遵守来源范围，不能从所有私人记忆自动合成共享知识。共享发布需确认/脱敏、来源读取授权与版本规则。

None 表示不限制；空列表在相关引擎路径可能视为无 scope，不能用 [] 表达“没有读取权”，这种情况应显式拒绝。标签本身不是加密、PG RLS 或完整持久 ACL，权限强度取决于服务端覆盖与测试。

## 实施前必须解决的边界

- 原文、chunks、附件、详情/分页、图/实体、Recall、Reflect 工具、导入导出、REST/MCP 均须一致授权，不能只过滤最终回答。
- Bank 级审计/LLM 请求/统计、operation 状态可能包含其他人的信息，成员级隔离时应禁用或适配；原生 get_bank_profile 校验不能替代成员范围。
- Worker 的 internal=True 会绕过部分认证/范围 hook，已受理任务需要携带可追溯用户归属并保持标签快照；不得把无用户身份当成无限权限。
- 同一 document_id 的跨用户覆盖、共享标签伪造、未打标签的历史数据、None/空 scope、知识页来源混合和撤权中的任务需要负向测试。
- 管理员若能代签其他用户 Key 并获得 secret，可模拟该用户；不能同时承诺防不可信管理员读取私有记忆。需要这种承诺时应改为本人签发/领取等更严格方案。
- tags/metadata 在严格策略下可能够用；持久 ACL、分享/撤回、权限变更和数据库级边界是否需要新增记录，应在独立设计中确定。

## 后续验收与当前状态

候选验收包括同 Bank 两用户交叉读取/改写拒绝、同用户多 Key 一致、共享知识只读、观察/页面派生不混入私人来源、Worker 与 REST/MCP 一致、撤权和历史数据迁移。上述功能为 NOT_IMPLEMENTED/NOT_RUN，不进入本期管理服务的 P0。

本期只实现工作空间、用户与 Key 管理及其认证/空间权限。不得把候选标签规则注入本期配置后就宣布用户隔离完成；需先单独评审、实现和端到端验证。
