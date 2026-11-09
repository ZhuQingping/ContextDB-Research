# 运维故障如何分层及复用排查经验

文档ID：team_demo_operations_20261027。来源：ContextDB-Research/hindsight/operations/contextdb-operations-runbook.md及hindsight_team_dev1于2026年10月27日的历史排障记录。Codex整理，未经人工审批。以下为诊断知识，不是生产操作授权，也不声称本次重新复现全部历史故障。

历史问题分三类。Issue #31是MCP辅助配置读取缺少空间schema，误查public.banks的服务端适配问题。Issue #32是取消public全量业务迁移后，离线初始化遗漏原生后台共享维护函数；会影响consolidation补偿发现和按cron发现知识页刷新任务，但不能说整个Worker失效，普通Retain任务仍可能运行。Issue #33包含外部MaaS限流，历史bge-reranker-v2-m3配额为每分钟20000 tokens，造成一次知识页刷新最终失败；这个历史配额不是所有环境的固定产品限制。源码修复、部署更新和运行验收是三种不同状态。

先区分API存活、PG就绪、业务授权、异步任务和模型服务。/health/live用于存活，/health/ready检查数据库就绪。健康200不证明模型调用、中文检索、业务授权和所有后台维护均正常。UI能打开也不证明后台Admin Key正确，应检查实际空间读取。

排查记录应包含：时间、代码或镜像版本、配置版本、可读bank_id、内部workspace_id、PG数据库和schema、模型provider与模型名称、HTTP状态、请求ID或operation_id、重试及最终任务状态。日志重复行数不等于独立故障任务数。

遇到429先看实际配额、候选数量、并发、重试与任务积压；不能简单增加超时，也不应为演示全局关闭重排或改模型配置。401/403检查Key、用户状态、空间权限，不把Admin Key交给业务绕过检查。管理和业务问题分别定位。不要用重建实例、清空任务表或重启整个PG作为通用修复。凭据与业务原文留在受控范围，团队知识只保留必要脱敏事实。
