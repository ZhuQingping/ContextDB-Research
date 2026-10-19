# Agent 专家审查摘要

日期：2026-10-16。主控根据独立专家报告整理，仅静态读取，没有发送写请求或读取真实业务凭据。

## 判断

当前实现：**REVISE**。保留 14 个管理操作与原生业务 REST/MCP，首发先修敏感读取，再落实逐空间权限；不重建节点 Agent 协议。

## 主要发现

| 级别 | 发现与建议 | 依据 |
| --- | --- | --- |
| Critical / P1 | REST include_payload 可读取含 Webhook secret/http_config 的原始任务载荷，普通读权限不足以保护运维信息 | validator.py:151–166；原生 api/http.py:8234–8254；memory_engine.py:21159–21180；webhooks/manager.py:129–139、211–221 |
| P1 | 当前整把 Key.permission 生成 scopes；逐空间必须贯穿 select_workspace、REST/MCP 执行和列表，不能只改 UI | repository.py:262–276；models.py:54–81 |
| P1 | MCP 工具列表是各空间能力并集，调用仍需按目标空间重验；单空间 endpoint 宜按本空间过滤 | validator.py:254–260；mcp.py:72–92 |
| P1 | selected 按 ID 授权，旧空间删除、同名重建不继承旧权限；任务句柄必须继续绑定 schema/Bank | repository.py:150、274–276、798–803；memory_engine.py:21159–21180 |
| P1 | 吊销阻断后续检查，不承诺强行取消已受理任务；内部 Worker 不用撤销 Key 重新登录 | repository.py:233–243；mcp.py:69–71；validator.py:87–113 |
| P1 | Key 创建不自动重试，不提供明文恢复；原生异步 Retain 复用自己的 operation_id 合同 | repository.create_key；原生 api/http.py:1269–1287；memory_engine.py:22261–22288 |
| P2 | 原生目录和 MCP 发现遍历空间，先测量查询数和延迟，只考虑请求内复用，不跨请求缓存授权 | routing.py:61–87；validator.py:254–260 |

所有扩展路径位于 hindsight-extensions/contextdb-service/hindsight_ext_contextdb；原生路径位于 hindsight-api-slim/hindsight_api。

## 敏感读取的证据边界

原生 list_operations 默认包含 webhook_delivery，可发现任务 ID；详情打开 include_payload 后返回原始任务。两条 Webhook 入队路径保存签名密钥与 http_config。已建立静态可达链，但没有做隔离动态复现、没有请求真实 payload。

原生 MCP get_operation 目前不传 include_payload，使用默认 false，不能把 REST 风险描述为已确认的 MCP 泄露。trace/audit 等诊断读取也需核查，但本次没有确认其内容泄露凭据。

最小方案为扩展层限制业务原始载荷读取、保留普通状态查询；用合成凭据回归，不建设第二套任务服务。

## 取舍

管理员部署凭据与业务 Key 继续分离；业务 MCP 不增加管理工具，空间生命周期继续经扩展。节点 Agent 管启停/升级，离线命令管实例初始化；自动化发现使用原生 Bank 列表，不新增全局任务句柄或业务目录接口。

单空间 MCP 的 list_banks 目前可能返回该 Key 有权访问的其他空间，未突破 Key 总范围；应在单空间过滤验收中明确产品语义，不作为已确认越权漏洞。

## 验证

RUN：只读核对约束、优化清单和扩展/native 调用链，比较 Bank/schema、任务句柄、MCP/Worker 边界。

NOT RUN：HTTP/MCP 实测、单测、模型请求、SQL/DDL、重启、代码改动、提交推送。

详见 [共识记录](review-summary.md)。
