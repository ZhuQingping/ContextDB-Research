# 第二轮研究与验证交付

入口：[Huawei ContextDB Service Develop.md](<../../../hindsight/archive/2026-10-19-before-reorganization/Huawei ContextDB Service Develop.md>)。原演示服务仍使用8888/9999/55432；本轮使用新Bank、独立schema和测试PG，未修改Hindsight原源码。

## 结果按范围阅读

- [参数/模型](reports/parameters-models.md)：493配置字段、51 Bank字段、22项真实HTTP校验、权限扩展异常及DML-only建Bank失败复现、特权预建验证、本地模型与HTTP包装对照；MaaS未实测。
- [完整阶段入口](reports/tests-ci-runbook.md)：上游CI位置、可复制命令与实际依赖；未执行不标通过。
- [测试流水线](reports/tests.md)：每条命令、JUnit、失败与skip。不能把部分suite通过汇总成全部功能完备。
- [真实客户端](reports/clients.md)：Codex/Claude/OpenClaw CLI与Hermes实际Agent核心；模型、版本、自动hooks、失败反例和复验命令。
- [设计审阅](reports/design-review.md)：参数/权限缺陷、参考DDL和21项PG约束检查。
- [具体架构/任务板](../../../hindsight/archive/2026-10-19-before-reorganization/cloud-service-architecture.md)：HLD/LLD、12任务包、依赖、负责人、工期估算和上线门禁。

`evidence/`保留JSON/JUnit和成功、失败日志；`scripts/`保留可复验探针。`clients-work/`、`tests-work/`、`.runtime/`等是忽略的依赖/隔离运行目录，可能含私有客户端配置，不作为可发布文档。

## 主线探针复验

在ContextDB-Research仓库根执行。会创建新的合成Bank/schema及测试记录，不删除演示数据；不要把连接地址改成生产库。

```bash
# 开启独立Cell B，原脚本使用8890/55433。
python3 deployments/hindsight-local/scripts/cell_b.py start

# 真实HTTP/PG opaque-key与Bank ACL原型
 deployments/hindsight-local/.venv/bin/python deployments/hindsight-local/round2/scripts/auth_probe.py
# 原生Retain幂等与控制PG账本
 deployments/hindsight-local/.venv/bin/python deployments/hindsight-local/round2/scripts/idempotency_probe.py
# 原生MCP身份与租户隔离
 deployments/hindsight-local/.venv/bin/python deployments/hindsight-local/round2/scripts/mcp_auth_probe.py
# 发布状态PG合同（上游索引完成为模拟通知）
 deployments/hindsight-local/.venv/bin/python deployments/hindsight-local/round2/scripts/publication_probe.py
# 独立API/Worker；占用8892/8893，用后自动停止
 deployments/hindsight-local/.venv/bin/python deployments/hindsight-local/round2/scripts/split_worker_probe.py
# 参考控制DDL；只创建独立测试schema
 deployments/hindsight-local/.venv/bin/python deployments/hindsight-local/round2/scripts/control_schema_probe.py

# 如不再复验，停止Cell B API；原PG数据保留。
python3 deployments/hindsight-local/scripts/cell_b.py stop
```

探针是研究参考，不是生产网关/迁移工具。API Key的生产KMS、分布式撤权、完整MCP授权与真实RDS/OBS/MaaS需要按任务板继续实现和验收。

真实客户端复验见客户端报告；先确认Retain operation completed，再进入新会话，不用固定sleep当成功证据。重跑真实客户端会调用已配置的远端模型。

## 明确限制

本机PG18.1的pg0实例使用`fsync=off`，本轮事务和进程重启结果不证明断电耐久性。系统suite的模型stub不代表真实模型质量；6条中文模型样本不是标准benchmark。真实客户端成功不等于公网TLS/IAM或所有消息渠道通过。原始测试失败与环境修正均保留，不删失败日志制造全绿结果。

原生UI共享口令隔离验证：[脚本](scripts/ui_access_probe.py)、[5项结果](evidence/ui-access-probe.json)。它不提供客户IAM/Bank ACL。Bank最小权限复验见参数报告，原生建Bank需要运行期DDL，不能只关闭启动迁移。

文档与服务健康复核：`python3 deployments/hindsight-local/round2/scripts/delivery_verify.py`。输出本轮源码SHA、原工作树是否干净、8888/9999健康、Markdown本地链接、脚本语法和文件摘要；不触发模型调用，不代表产品测试全部通过。

当前运行时已按用户要求切换GPT-5.6-Luna/low、LLM并发1，自动整合关闭；[验证记录](evidence/runtime-cost-control.json)。历史四客户端测试模型保持原记录，不冒称Luna完整回归。
