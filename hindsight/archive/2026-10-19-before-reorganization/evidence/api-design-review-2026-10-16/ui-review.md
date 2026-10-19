# UI 专家审查摘要

日期：2026-10-16。主控根据独立专家报告整理。仅代码与合同审查，没有操作真实云 UI，不重复执行此前阿里验证。

## 判断

当前实现：**REVISE**。保留 14 个管理操作，通过原 PATCH 和必要只读字段即可改善交互，不必新增一批 API。

## 主要发现

| 级别 | 发现与建议 | 依据 |
| --- | --- | --- |
| P1 | Key 编辑不支持名称；应允许 name 单独提交，authorization 提交时完整替换；只改名不重验旧空间 active | models.py:76；contextdb-users-view.tsx:415；repository.py:311、449 |
| P1 | 列表缺脱敏标识且含吊销项；SQL 过滤后统一分页和计数，停用成员不等同吊销 | KeyMetadata；repository.py:415；contextdb-users-view.tsx:293 |
| P1 | 空间每页 50 项，未加载的已选项不能当作删除或静默丢弃；复用单空间 GET 解析 | contextdb-users-view.tsx:63、153、163、436 |
| P1 | 管理主目录调用原生 Bank 列表，仅 active，创建/删除失败状态不可见；改用扩展空间列表 | banks-overview.tsx:126；app/api/banks/route.ts:14；repository.py:278 |
| P1 | workspaceMutation 的进度只在函数内，120 秒抛错；应保存非敏感意图，刷新可继续查进度 | lib/contextdb-api.ts:86–106 |
| P1 | Key 创建超时为结果未知，不自动重签；不能模糊匹配后自动吊销他人 Key | 管理代理 15 秒超时；Key 创建无幂等 |
| P2 | middleware/代理重复查 admin/session，可按入口责任收敛，不能缓存授权或漏掉原生数据路由 | middleware.ts:60；lib/contextdb.ts:112；扩展 http.py:227 |

## 异步恢复的关键约束

latest_operation_id 只能恢复查询，不能重建原始请求。当前创建幂等 hash 在 NFKC/trim 前计算；从返回名称重建请求可能冲突。同幂等 Key 失败后可能重启任务，且受空间生命周期版本限制。

建议 sessionStorage 仅保存幂等 Key、原始请求、空间/操作 ID，不存任何凭据。初始响应丢失时复用原请求；查询进度不发 POST；failed 后的重新执行由用户明确确认。浏览器记录丢失后仍显示失败空间，允许删除后再建，不按名称猜测请求。

## 已有防护，不应误报为缺失

- Admin Key 只由服务端配置注入，浏览器不能选择上游地址或凭据。
- 管理代理有固定路径、方法和字段白名单。
- Origin/Host 和 Sec-Fetch-Site 检查已存在，写请求缺失/非法 Origin 拒绝。
- HttpOnly/SameSite 会话及成功签发以外的 secret/digest 过滤已存在。
- 新签 Key 明文仅在页面内存中，关闭/隐藏/超时清理；不能因此声称已完成公网安全验收。

## 验证

RUN：只读读取约束、优化文档、模型/Repository/UI/代理/认证及既有测试源码；确认代码 HEAD 加现有未提交实现。

NOT RUN：运行测试、HTTP 请求、真实 UI 操作、DDL、模型调用、重启、代码改动、提交推送。

详见 [共识记录](review-summary.md)。
