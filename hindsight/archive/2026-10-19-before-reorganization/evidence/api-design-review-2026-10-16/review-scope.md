# API 审查范围

日期：2026-10-16。用户要求启动 REST/Web、UI、Agent 专家检视当前 API，目标为首期简单、高效、安全，并将优化点写入现有优化文档。

- 场景：external-docs / design-review。
- 代码编辑权限：DENIED。仅允许主控更新优化文档和本目录审查证据。
- 实际代码工作树：`/Users/zhuqingping/Work/Database/Context/.local/worktrees/contextdb-v2-simple-20261016`，HEAD `d5e851b60315b79696e995874e7edc1e9a7bae23` 加现有未提交实现。
- 资料仓：`/Users/zhuqingping/Work/Database/Context/ContextDB-Research`，HEAD `aa7bd92c766a5863cbd790b335c6297383f18ae3` 加现有脏文件。
- 授权修改：`hindsight/contextdb-optimization-backlog.md`、`hindsight/evidence/api-design-review-2026-10-16/`。
- 禁止：业务代码/旧设计/OpenAPI/curl手册修改、运行库写入/DDL、测试、模型调用、重启、提交推送、外部发布；不操作现有空间/成员/Key。
- 专家使用同一工作树只读，无补丁，不为只读审查新建隔离分支；分工为 REST/Web 合同、UI 交互、Agent REST/MCP 及任务边界。
- 证据只保存代码基线/哈希、审查摘要及决策，不保存凭据、配置明文、HTTP 敏感载荷或完整会话。
- 验证：静态调用链、官方资料、专家交叉复核、Markdown链接/示例JSON、空白检查及代码状态/哈希不变；运行验收待实现后隔离完成。
- 无适用的 MySQL 内核领域规则，不套用该领域测试门槛。
