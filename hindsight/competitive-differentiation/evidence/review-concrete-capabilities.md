# 本轮检视：具体能力与证据纠错

日期：2026-10-08。检视范围：00–05、evidence 原报告及目录外存储/架构/Cloud 对比相关段落。本轮未部署资源、未验证产品实现、未跑效果或性能评测。

原 evidence 保留为历史调研输入；冲突事项按本记录及修订后的主文档阅读。官方底座支持不能证明 ContextDB 已接入。

## 1. 本轮外部核验

| 项目 | 证据与限制 | 修订结果 |
|---|---|---|
| RDS PG zhparser | 官方专页搜索返回完整说明，更新于 2026-01-08，包含实例查询方法 | 产品已公开支持；待验证目标实例、读写适配及历史重建 |
| PG 磁盘加密 | 国际站英文正文可读，更新于 2026-09-08，含 DEW、算法与操作约束 | 仅陈述存储层能力，不推导端到端或即时删除 |
| PG 备份加密 | 2024 FAQ PDF 索引说明 PG 加密备份；2026 磁盘页讨论有/无备份加密；MySQL 专页限制不能直接套用 PG | 撤回默认不加密判断，目标版本行为待官方/控制台确认及恢复演练 |
| 备份恢复警示 | 加密页警示处于密钥禁用/删除/冻结语境 | 不说加密备份一律无法恢复；明确密钥依赖 |
| 阿里导出 | 官方快速入门搜索索引仍返回记忆与知识库限制；本轮打开页未提取同段正文 | 有条件保留对照，发布前保存原文快照；不推导删除或审计缺失 |
| AWS metadata | 官方 Memory types/PDF 索引列出短期事件客户密钥覆盖限制 | 只比较 CMK 覆盖，不说完全无静态加密 |
| RDS HA/副本 | 官方产品页列主备、同步及只读扩展 | 只作底座输入，不直接套 SLA，也未证明 recall 无写副作用 |

直接来源（本轮访问）：

- [zhparser](https://support.huaweicloud.com/usermanual-rds-pg/rds_09_0065.html)
- [PG 磁盘加密](https://support.huaweicloud.com/intl/en-us/usermanual-rds-pg/rds_pg_05_0025.html)
- [RDS FAQ PDF](https://support.huaweicloud.com/rds_faq/rds-faq.pdf)（仅核对搜索索引相关文字，未作 PDF 版式检视）
- [MySQL 备份加密](https://support.huaweicloud.com/usermanual-rds-mysql/rds_08_0050.html)（用于辨别引擎范围，不作 PG 依据）
- [阿里快速入门](https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/rds-contextdb-quick-start)
- [AWS Memory types](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-types.html)
- [RDS PG 产品页](https://www.huaweicloud.com/product/pg.html)

## 2. 本地交叉检视与推理纠错

| 旧稿问题 | 依据/缺口 | 修订口径 |
|---|---|---|
| 火山企业/个人都是共享 | [原报告](source-tencent-volc.md) 写有企业版独占；本轮外部正文读取未成功 | 撤回共享判断，现行 SKU/隔离细节待核验 |
| 不可导出所以不可审计删除 | 两类能力无必然关系 | 各自调查 |
| 六方全部闭源/无评测 | 同目录记录了 OpenViking/WeKnora 开源及多方论文/评测 | 比较具体托管产品与范围，不说行业全集 |
| 治理都停在 IAM | 原报告已有知识审批、确认、revision、防投毒 | 比较对象与链路，不说唯一 |
| 上游导出=Workspace 全量导出 | [接口对比](../../hindsight-cloud-open-source-comparison.md) 仅证明部分接口，未证明完整资产语义 | 定义对象覆盖、分页、快照、权限、附件、关系与恢复 |
| 中文只改查询端即可 | [存储核验](../../backend-storage.md) 记录 search_vector 由应用计算 | 写入/查询同步适配，重建历史数据 |
| bge-m3 是通用默认 | 来源是本地 1024 维部署 | 标明部署范围，效果待测 |
| BYOK=自定义密钥；禁用即删除 | 无密钥材料导入及缓存/备份全覆盖证据 | CMK/BYOK 分开；不可访问和删除分开 |
| OBS 前缀=三隔离 | 前缀是命名范围 | 各种隔离分别验证 |
| SQL/CTS 即业务审计 | 底层账号不等于最终用户 | 应用层记录操作者、request_id、范围、结果 |
| PITR 直接租户回滚 | 实例与 Workspace 粒度不同 | 隔离恢复后提取，对齐附件，重放删除清单 |
| OperationValidator 即确认制 | 请求检查无法证明候选/后台过滤 | 验证 recall/reflect/组合查询/巩固链路 |
| 独立复现已确认，可继承成绩 | 原报告无复现报告/配置/脚本，还把 VT 列为合作研究方 | 原“独立复现”降为未验证，不作背书；作者成绩另标 |

## 3. 实施及发布前待关闭

- [ ] 目标 PG 区域/版本的备份加密、轮换与恢复行为。
- [ ] 实例 zhparser/pgvector 版本和 Hindsight 文本搜索适配入口。
- [ ] 全量对象遍历、导出/导入、一致性及引用覆盖。
- [ ] 主体删除的派生记忆、知识副本、附件、任务及备份处理范围。
- [ ] 治理过滤扩展点和人工版本保护。
- [ ] 阿里导出原文快照、火山独享 SKU 与隔离细节。
- [ ] 中文效果、规模、成本和端到端恢复报告。

这些是产品实施依赖，不能作为已支持的宣传依据。原竞品定价、版本与 star 数未在本轮全面刷新。
