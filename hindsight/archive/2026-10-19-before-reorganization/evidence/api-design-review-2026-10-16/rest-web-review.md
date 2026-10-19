# REST/Web 专家审查摘要

日期：2026-10-16。主控根据独立专家报告及敏感载荷补充复核整理，非逐字会话记录。代码只读，不含实际密钥。

## 判断

当前实现：**REVISE**。14 个管理操作都有实际调用场景，无需合并资源或新增实例 API。首期简化应集中在字段来源、明确失败语义和安全边界。

## 主要发现

| 级别 | 发现与建议 | 依据 |
| --- | --- | --- |
| 发布前阻断 | 普通任务状态的 include_payload 可返回 Webhook 任务中运维凭据；业务 Key 应拒绝原始载荷，保留状态查询 | 原生 api/http.py:8234；engine/memory_engine.py:21159；webhooks/manager.py:129、211；扩展 validator.py:151 |
| P1 | name 与 authorization 独立编辑；授权作为完整对象替换，不同时保留三字段旧合同和逐空间列表 | 扩展 models.py:54–81；repository.py:429–460 |
| P1 | 创建默认读写，PATCH 权限明确必填；只改名不能应用授权默认值 | 最新优化清单 UM-05；现有创建/编辑模型差异 |
| P1 | 正常 Key 列表先过滤吊销再 count/分页，返回脱敏标识，去掉成员重复 instance_id | models.py:96–127；repository.py:409–426 |
| P1 | Key 签发无幂等，不自动重试或持久保存明文；模糊名称不能当请求唯一标识 | repository.py:378–407；security.py |
| P1 | 保留 202/操作查询/If-Match；统一 UI 和 API 的 description、Header、错误校验 | http.py；UI app/api/contextdb/[...path]/route.ts；lib/contextdb-api.ts |
| P2 | 减少重复请求和高频使用时间写入，测量后再改；强 ETag 与独立变动使用统计的表示语义需澄清 | UI lib/contextdb.ts、middleware.ts；repository.authenticate |

敏感载荷问题已由专家补充独立静态复核，不能沿用初次报告“未发现 Critical”的中间判断。原生 MCP get_operation 未传 include_payload，当前风险明确来自 REST。未读取实际载荷或真实凭据，未在隔离环境复现。

布尔门禁建议：正常解码后读取参数列表；重复参数拒绝；单值与原生布尔解析一致，true/1/on/yes 等真值对业务身份拒绝，合法假值保留状态查询，非法值拒绝。不能只匹配原始字符串 true；管理员保留诊断。

## 取舍

同意首期保留 14 路由、单 Admin、离线初始化；不加角色、管理 MCP、在线恢复、全空间例外、Key 明文查询或通用幂等平台。authorization 采用 selected 的 workspaces 列表或 all 的统一 permission，PATCH 提交完整授权。空间 latest_operation_id 可作只读恢复字段，不暴露租约。

## 验证

RUN：读取 AGENTS/CLAUDE、指定工作流、优化清单和当前工作树；静态比较模型、Repository、UI 代理；核对官方 HTTP/OWASP 资料；补充复核敏感任务原始载荷调用链。

NOT RUN：HTTP/MCP 动态复现、测试、模型调用、数据库写入、DDL、重启、代码改动、提交推送。

当前代码基线及脏状态见 [代码基线](code-baseline.json)。最终整合文档意见见 [共识记录](review-summary.md)。

## 官方依据

- [RFC 9110：202](https://www.rfc-editor.org/rfc/rfc9110.html#section-15.3.3)：受理与完成不同，建议可查询状态。
- [RFC 9110：校验器](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.1)：区分完整表示校验与管理字段版本。
- [RFC 5789：PATCH](https://www.rfc-editor.org/rfc/rfc5789.html#section-2)：修改的原子性和条件请求。
- [OWASP REST Security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)：既有入口负责传输与限额，应用仍须逐资源授权。
