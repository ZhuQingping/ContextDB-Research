# 火山 embedding 批量超限与任务恢复

记录日期：2026-11-08，Asia/Shanghai。

## 原因与影响

本机 8892 实例通过 OpenAI 兼容适配调用火山 embedding；接口报错明确限制每次最多 10 条输入，而服务端该适配默认批量为 100。抽取事实较多时，一次发送 14—23 条等批次会返回 HTTP 400：`Embeddings API input limit exceeded: max 10, got 23`。这会使异步 retain 失败，API 健康与提交成功不能代表记忆已完成处理。

## 配置处理

已备份并修改 `/Users/zhuqingping/.local/share/contextbase/deployments/gpt61-20261107/runtime/api.env`：

```dotenv
CONTEXTBASE_API_EMBEDDINGS_OPENAI_BATCH_SIZE=10
```

已通过 manage.py 停止、重新启动 8892/9992 实例，按启动入口的配置别名加载流程确认有效 batch size 为 10；API 健康、PG 连接正常，UI login 返回 200。此次修改不改变向量维度、模型或产品默认值。

## 恢复方式与状态

通过官方 `POST /v1/default/banks/outer_space/operations/{operation_id}/retry`，使用本机已有运维管理员凭据恢复 4 组受影响的 retain 父子任务。重试父任务会由服务端恢复失败子任务，无需重发对话或修改数据库状态。

历史上另有 5 个知识页刷新超时记录，其对应的 3 个知识页均已有更晚成功的刷新任务，不重复执行已被后续成功覆盖的历史任务，保留原失败记录供排查。

已恢复完成：4 个 retain 子任务和对应的 4 个父任务全部为 `completed`，各次抽取错误数为 0。子任务当次返回数量依次为 15、16、3、3；这是各次处理量，不应相加当作当前有效记忆总数。

| retain 子任务 | 完成状态 | 当次提取数量 |
| --- | --- | --- |
| `5601ad0b-0dfb-4f47-a948-b33ca2fde074` | completed | 15 |
| `2ffaf843-2ccd-4451-980d-d81e53c05f91` | completed | 16 |
| `79310c6b-095e-4bbe-9e61-03f131a5488d` | completed | 3 |
| `2ca26bc0-efe9-43d7-86a0-660febd9cf7e` | completed | 3 |

重启后检查未发现 ERROR/CRITICAL 或 embedding 输入超限错误。API 健康、数据库连接正常、UI HTTP 200。另两个 Bank（agent_memory、deployment_smoke_20261107）未发现未完成任务。

最终检查时后续后台任务：consolidation pending `83d25010-e12b-4379-837b-1c88afda0d8a`；consolidation processing `50242f45-db17-4303-b802-28fbc6606222`。写入任务完成与观察整理完成是不同阶段；此处按现场状态记录。


证据目录：`/Users/zhuqingping/.local/share/contextbase/deployments/gpt61-20261107/tuning/embedding-batch-20261108/`。包括修改前任务快照、重试响应和恢复后任务状态；`api.env.before` 含秘密，仅作本机私有备份，不复制或分享。
