# ContextDB 总体架构

更新：2026-10-16。沿用原详细设计中“入口 → 独享计算服务 → 同一 PG”的结构，展示当前首发版本的三个入口。

![Console、Agent、Hindsight UI 三个入口](diagrams/contextdb-first-release-architecture.svg)

[可编辑 drawio 源文件](diagrams/contextdb-first-release-architecture.drawio) · [PNG 预览](diagrams/contextdb-first-release-architecture.png) · [当前设计](member-apikey-bank-service-design-first-release.md)

| 入口 | 链路 | 职责 |
| --- | --- | --- |
| Console | Console → 华为云管控 → 节点管理 Agent | 实例资源开通、配置、启停和升级；部署阶段离线初始化元数据 |
| Agent / 应用 | 原生 REST / MCP → Hindsight API | 使用业务 API Key 和 bank_id，调用 Retain、Recall、Reflect 等记忆接口 |
| Hindsight UI | UI 服务端 → Hindsight API | 管理员用 UI 密码登录；服务端持 Admin Key，管理工作空间、用户、Key 和空间内容 |

实线表示请求或数据访问，虚线表示部署运维。节点管理 Agent 不转发业务 Agent 或 UI 的请求。实例运维与业务 Agent 是不同角色。

Hindsight API 与 Worker 并列，共用同一 PG。API 负责认证、授权、路由与请求处理，Worker 领取原生异步任务。ctxdb_meta 保存管理元数据；每个工作空间在独立 schema 中对应唯一 Bank，保存记忆、文档、索引和原生任务。没有独立的 MetaPG。

工作空间管理已在 Hindsight UI，Console 负责实例运维。已有节点 Agent 的具体调度实现由云管控集成，图中的运维连线不代表新增了一套 Agent 接口。

原 V2 架构说明已保留在[历史版本](archive/2026-10-16-before-architecture-redraw/contextdb-v2-architecture.md)；原 SVG、原 my_arch.drawio 和 v1 详细设计均未覆盖。
