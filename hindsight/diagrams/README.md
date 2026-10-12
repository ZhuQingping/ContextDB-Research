# ContextDB 首期服务化架构图

2026-10-13。三张图对应[首期设计](../member-apikey-bank-service-design.md)，产品模型已确认，系统实现尚待验证。管理认证已改为管控后端专用 Key；用户登录由已有管控承担，不在 Hindsight 节点直接校验 IAM Token。

| 文件前缀 | 内容 |
|---|---|
| contextdb-workspace-model | 云租户 → 工作空间 → 用户（管理员/成员）→ 多 API Key；每空间独立 schema 内唯一 Bank |
| contextdb-service-architecture | 已有管控经内部管理入口调用 API；业务入口独立；API/Worker 并列，同一个 PG DB，各空间表/索引分开 |
| contextdb-member-request | 管控先做用户认证/授权，节点验证管理 Key 和可信 actor；业务用用户 Key；不展示未实现的用户 tag 隔离 |

`.mmd` 是可编辑 Mermaid 源文件，`.svg` 是已生成的查看文件。本次使用 Mermaid CLI `12.0.0`；SVG 使用系统中文字体，推荐 PingFang SC 或 Microsoft YaHei。

在仓库根目录可重新生成，例如：

```bash
npx --yes --package @mermaid-js/mermaid-cli@12.0.0 mmdc \
  -i hindsight/diagrams/contextdb-service-architecture.mmd \
  -o hindsight/diagrams/contextdb-service-architecture.svg \
  -c hindsight/diagrams/mermaid.config.json \
  -b white --size 1600 --no-font-embed
```

命令需要可用的 Puppeteer/Chrome；使用已有 Chrome 时通过 `-p` 指定其配置文件，不修改 Agent 或浏览器全局配置。替换文件前缀可生成其他两张图。
