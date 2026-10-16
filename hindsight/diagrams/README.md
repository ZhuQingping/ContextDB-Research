# ContextDB 服务化架构图

## 当前首发对象关系

[contextdb-first-release-workspace-model.drawio](contextdb-first-release-workspace-model.drawio) 是可编辑源文件，配套 SVG 与 PNG 用于文档和预览。图中用户与工作空间同属实例，Key 归属用户，并独立配置可访问的空间与权限。旧版 `contextdb-workspace-model` 保留为历史参考。

## V2 总体架构

[总体架构说明](../contextdb-v2-architecture.md)按业务访问、云管控、UI 管理三个场景展示同一套服务。

| 文件 | 内容 |
| --- | --- |
| [contextdb-v2-service-architecture.svg](contextdb-v2-service-architecture.svg) | 三个场景的组件调用关系；API/Worker 与 PG 元数据、用户数据的关系 |

V2 图使用普通 SVG 文本、矩形和箭头，SVG 本身就是可编辑源文件，不需要 Mermaid 构建。图中重复的 API 和 PG 不是额外部署的实例。

## V1 历史架构

2026-10-13。四张图对应[首期设计](../member-apikey-bank-service-design.md)。新增管理接口仅提供内部 REST，供可信管控调用，不向用户面直连开放；原生 REST/MCP 接口保持不变，接口裁剪另行评估。管理认证采用管控后端专用 Key；用户登录由已有管控承担，不在 Hindsight 节点直接校验 IAM Token。前序本地验证不代替生产联调。

| 文件前缀 | 内容 |
|---|---|
| contextdb-workspace-model | 云租户 → 工作空间 → 用户（管理员/成员）→ 多 API Key；每空间独立 schema 内唯一 Bank |
| contextdb-service-architecture | Console → 管理面 → Hindsight 计算节点；Agent → Hindsight 计算节点；API/Worker 并列，同一个 PG DB，各空间表/索引分开 |
| contextdb-member-request | 管理链路概览：Console → 管理面 → Hindsight 计算节点 → PG；突出用户授权、管理 Key 校验及权限复核，协议细节留在正文 |
| contextdb-data-request | 原生业务认证接入：Agent/应用（REST/MCP）→ Hindsight 计算节点 → PG；突出用户 Key 校验、空间范围与 retain/recall 权限，不新增业务处理模块 |

`.mmd` 是可编辑 Mermaid 源文件，`.svg` 是已生成的查看文件。本次使用 Mermaid CLI `12.0.0`；SVG 使用系统中文字体，推荐 PingFang SC 或 Microsoft YaHei。

在仓库根目录可重新生成，例如：

```bash
npx --yes --package @mermaid-js/mermaid-cli@12.0.0 mmdc \
  -i hindsight/diagrams/contextdb-service-architecture.mmd \
  -o hindsight/diagrams/contextdb-service-architecture.svg \
  -c hindsight/diagrams/mermaid.config.json \
  -b white --size 1600 --no-font-embed
```

命令需要可用的 Puppeteer/Chrome；使用已有 Chrome 时通过 `-p` 指定其配置文件，不修改 Agent 或浏览器全局配置。替换文件前缀可生成其他三张图。
