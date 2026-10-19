# ctxdb_meta PG 内核审查

日期：2026-10-16。角色：PG 数据库内核专家。Status：PASS（作为待优化建议；不代表已实施或性能验收）。Code-edit permission：DENIED。

只写本报告；未修改源码、数据库、服务或已有优化文档，未执行测试、DDL、ANALYZE、压测、提交推送。

## 结论与范围

独享实例应优先减少重复的部署字段、索引和不必要的写入，不以合表数量作为简洁目标。接受用户已决定的边界：部署信息单行保存；普通表不为未来共享版保留 instance_id/cloud_tenant_id；api_keys.user_id 保留；在线安全删除当前承诺不变；management_operations 与 request_admissions 不强行合表。

审查基线：`/Users/zhuqingping/Work/Database/Context/.local/worktrees/contextdb-v2-simple-20261016`，HEAD `d5e851b60315b79696e995874e7edc1e9a7bae23` 加已有未提交首发简化版。实际 PG 目录依据主审只读采集的 `catalog-snapshot.json`，数据库 `contextdb_simple_20261016_091155`，快照时间 `2026-10-16T11:22:59.012123`。

确认：ctxdb_meta 共 8 表、78 列、20 个索引，表/列 COMMENT 均为零。不能从小库/零扫描统计得出某个索引无用、系统有性能瓶颈或优化已生效。

## 优先建议与依据

### K01：单行部署信息，减少重复作用域（P1，结构简化）

`schema.sql:6-19` 将格式版本与部署绑定拆为两个表，运行代码 `_verify_format/_verify_binding` 又要求各只有一条预期记录。可合并 `deployment_info`：单行标记（例如 `singleton boolean PRIMARY KEY CHECK(singleton)`）、`instance_id varchar(128)`、`cloud_tenant_id varchar(128)`、`metadata_version integer CHECK(metadata_version>0)`、`format_id`、`installed_at`。这会在数据库层限制至多一行；初始化原子插入、API/Worker 校验恰好一行。

移除 workspaces/users/api_keys/management_operations/request_admissions 的 instance_id，以及 workspaces/audit_events 的冗余 cloud_tenant_id；审计需要脱库集中导出时，由导出上下文附加实例/租户。保留绑定核对，避免连错数据库。部署表不是云管控实例目录。

复合唯一 `(instance_id,cloud_tenant_id)`、`(instance_id,workspace_id)`、`(instance_id,user_id)` 对当前全局主键没有额外唯一性收益，但**当前外键明确依赖它们，不能直接 DROP**。先将外键改为 workspace_id/user_id 单列主键，调整 SQL 与索引，再去掉重复列/索引。

### K02：保留真正的关系、幂等和在线删除屏障（P1，正确性边界）

`api_keys.user_id` 记录 Key 归属，必须保留直接 FK users(user_id)。workspace_id 记录任务/准入的目标；audit 中 user_id/key_id/workspace_id 是历史对象身份，不是重复租户信息，不能一概删除。

`repository.py:145-196,599-674`：create 的 target_id=''，delete 的 target_id=workspace_id。原 unique(instance_id,actor_subject,action,target_id,idempotency_key) 表达“创建在实例范围重试、删除在目标空间范围重试”，target_id 不是可随意删除的复制字段。去实例字段后应保留等价唯一范围和 request_hash 冲突检查。不要仅为减列改为复杂表达式约束。

management_operations 是 API 内 Lifecycle 循环领取的空间管理任务；request_admissions 是请求/任务提交入口登记的在途保护，不参与调度；audit_events 是管理历史。这三者结束/保留/恢复规则不同。保留空间墓碑、不可复用 ID、租约 ownership token、workspace_version 生命周期代际校验。不能用“超过 TTL”判断未知旧请求已结束；不能把 request_admissions 改成 UNLOGGED（崩溃后丢记录会影响安全判断）。

### K03：COMMENT 与字段语义（P1，可运维性）

应通过有版本的迁移补 `COMMENT ON SCHEMA/TABLE/COLUMN`，重要约束和索引可补 COMMENT。重点说明：实体归属、状态各值、时间单位/时区、NULL 意义、清理时机、并发版本、权限来源；digest 为 HMAC 摘要且固定 32 字节；revoked_at 非 NULL 永久吊销；last_used_at 是观察性近似使用时间；request_admissions 中 interrupted 不允许定时直接清除；management_operations 的 succeeded 与 audit 的提交 success 不同。

COMMENT 不写真实密钥、密码、样本凭据或敏感连接信息。注释必须随迁移更新，不能只加 Python/SQL 文件行注释。原生抽样表也无注释不构成不补注释的理由。

### K04：字段上限/格式一致，避免把 varchar 当性能优化（P1，约束清晰）

`schema.sql:55-72` 已有 key_id 32 hex、name 1..64、digest 32 bytes、permission 枚举 CHECK，text 不是无约束。可统一内部 ID varchar(32)+精确格式 CHECK；name varchar(64)+非空/trim 合同；外部实例/租户 ID varchar(128)；schema_name 有界（生成格式为 41 个 ASCII 字符）；状态/access_mode/permission 有界 varchar+CHECK；description 512 字符上限可明确；错误描述保留 text。

**Key 名称 64、key_id 32、完整密钥 85/86 字符、摘要 32 字节分别是不同对象。** 不保存完整明文，更不能把完整密钥塞入 key_id varchar(64)。保留 bytea，不改为 64 字符十六进制摘要。

`name_key` 是 NFKC+casefold 后的规范名称，可比原始名称更长，不能直接照抄 name varchar(64)。保留 text 并限定应用输入，或者在定义可证明足够的规范化上限之后再限制；工作空间名称规范化后应再次校验最终名称长度，避免输入模型通过、DB CHECK 失败。成员/Key 的纯空白名也应统一拒绝。

补 users/api_keys 的 `CHECK(version>0)`、管理任务 `CHECK(attempts>=0)` 等轻量约束；数组当前 DB 只校验 cardinality 与 all/selected，API 已做 ID 格式和去重。若继续数组存储，需限制维度/元素 NULL、格式/数量、重复等；逐空间授权落地时优先用规范关系表，而不是再堆复杂数组 CHECK。

text/varchar 共用变长存储；短值通常行内，extended 只表示允许 TOAST，不是已经溢出。不要用 char(n)、SET STORAGE PLAIN 或固定 buffer“解决”短 ID 性能。各 FK/查询/迁移中同义 ID 保持同一类型/边界。

### K05：先减少 last_used_at 热点写（P1，性能候选）

`tenant.py:91,107` 指定 record_use=True；`repository.py:252-257` 每次使用无条件 UPDATE 同一 Key 的 last_used_at。这会生成 MVCC 行版本、WAL 并让同 Key 并发 UPDATE 竞争。该列当前不在索引里，在页空间足够时允许 HOT，但 HOT 仍不是零成本。

建议将其改成条件节流，例如仅在 last_used_at 为空或早于 now()-interval '1 minute' 时更新，解释 UI 为近似最近使用时间；SQL 条件在 DB 层检查以处理多进程，不靠单进程缓存。验证 auth 仍每次检查成员状态、revoked_at、授权；节流只针对观察字段，不能缓存授权一整分钟。遥测失败不得放宽鉴权；是否让遥测失败阻断请求应单独定义。本轮没有基准，不能宣称吞吐提升值。

### K06：审视全局锁，但不能伴随字段删除直接去锁（P2，后续测量）

`repository.py:85-94` 对唯一实例行 FOR UPDATE，串行化目录/Key 管理操作；目前低频管理场景代码简单，可以迁到 deployment_info 单行继续使用。它不是业务请求总锁。

若确需提高管理并行度，应按成员父行 -> Key 子行固定顺序锁定，版本 CAS 与唯一约束配合，验证成员删除/停用与签 Key、权限更新/吊销的并发结果。不能删除全局锁后继续把无锁读取+版本对比+UPDATE 当成 CAS。方案需要事务测试，不能本次仅靠审查声称等价。

删除空间当前显式 `FOR UPDATE`（repository.py:613）与请求 `FOR KEY SHARE`（admission.py:313、tenant.py:176）互斥。**不可改成普通 UPDATE state 以为更轻量**：非键列更新一般 NO KEY UPDATE，与 KEY SHARE 兼容，将破坏关闭准入的串行点。GET 当前用 NO KEY UPDATE 可另评估降低无必要锁，但不把它与破坏性操作混同。

请求锁事务跨 HTTP/LLM 执行持有专用连接，metadata/admission 每进程各最多 10 连接，是需测的资源预算。不要使用过短 idle-in-transaction timeout 强杀正常长请求，也不能以池满时绕过登记。row lock 本身可能产生写，多并发 KEY SHARE 同行涉及 MultiXact；这些是测量维度，不是当前小环境故障结论。

### K07：索引重构先减确定冗余，再评估部分索引（P1/P2）

去实例作用域后，明确候选形态：

- workspace name unique(name_key) WHERE state<>'deleted'，保留软删除后同名重建的既有语义；schema_name UNIQUE 保留，显式映射保留方便诊断。
- users(created_at,user_id) WHERE status<>'deleted'；keys(user_id,created_at,key_id) WHERE revoked_at IS NULL（与待优化的正常列表过滤一起落地）。必须同步 WHERE/total/分页；不能只前端过滤。
- admissions(workspace_id) 支撑 EXISTS 和 workspace FK 访问；主键 admission_id 支撑结束登记。不要加 state 单列索引，仅凭状态低基数没有场景收益。
- management 幂等唯一约束保留等价范围；租约领取保留 SKIP LOCKED。现 `(instance_id,state,lease_until,created_at)` 对 OR+时间条件不能直接保证按 created_at 全局取最老记录无排序，且 lease_until 每 10 秒更新使 B-tree 键改变、失去 HOT 资格。

可实验比较 `ON management_operations(created_at,operation_id) WHERE state IN('pending','running')`，以 heap filter 检查 lease；它排除完成历史、提供稳定排序、续租可争取 HOT，但 lease 不可索引筛选可能扫描更多未到期任务。任务量小可保留当前实现，不要未测直接替换。领取排序最好显式追加 operation_id 作为同时间稳定键。**不强制新增每空间活动任务 UNIQUE**：现行 workspace 行锁已协调，新增约束需证明需求和重启/重试兼容，不能为“防御性设计”增复杂度。

当前 audit_workspace_time 代码仅写入，未找到产品查询 API；不是根据零扫描认定无用。先明确 DBA 按 workspace、全局时间、用户/Key、request_id 的实际查询合同，再选必要索引。不要把所有可能查询都建索引；现索引 workspace_id 在 created_at 前，不保证无 workspace 条件的全局时间查询最优。PG18 有 skip scan，也不意味着无需匹配查询实测。时间清理索引待保留策略和量级明确后再考虑，不先引入分区/BRIN/GIN。

### K08：历史清理、迁移和原生表经验（P1 语义、P2 实施）

原生 async_operations 使用任务领取部分索引、时间/状态查询、terminal cleanup 索引；MaintenanceLoop 以有限批次/SKIP LOCKED 清理终态任务及历史。可借鉴“按职责分表、按查询建索引、短事务批次清理”，不照搬其索引数量或全套调度到元数据。

管理任务完成后留存是状态查询/幂等重放的合同，不是仍在执行。清理前定义幂等有效期；到期 Key 的行为明确，不能突然把旧重试当新请求。不要按统一 TTL 处理失败任务、未解决准入屏障、空间墓碑、审计。审计与管理任务结果也不可互相替代。

meta `_audit` 与资源变更同事务，当前只记提交 success，不是完整成功/失败操作审计；原生 audit_log 记录业务请求/响应，通常异步 fire-and-forget，职责与可靠性合同不同。不建议为少一表把两者混合。审计不要加级联删除到 users/keys/workspaces；其历史在实体删除/清理后仍应可追溯。

原生 `c3e5a7b9d1f4_widen_history_bank_id_to_text.py` 明确记录 bank_id 某些表 varchar(64)、另一些 text，导致历史回填截断并阻断启动迁移。这个经验支持“同义字段跨表/API/迁移边界一致”，不是支持所有字段无限长。原生 metadata JSONB、数组广泛使用，也不代表授权可以放任意 JSON：逐空间 permission 建议显式 key_workspace_permissions(key_id,workspace_id,permission)，PK(key_id,workspace_id)，非空+枚举 CHECK、FK 保留；all 模式默认 permission 在 Key 上，selected 模式关系行是唯一授权来源。暂不增加 GIN。

`CREATE TABLE IF NOT EXISTS` 不是升级迁移。应有显式有序版本迁移，预检查长度/格式/孤儿/重复数据，事务内迁移部署信息和约束，原子更新版本；API/Worker 对不支持版本拒绝运行。不能承诺加一个 JSONB metadata 就永不需要 schema 升级。

## 官方核实资料

- [PG18 字符类型](https://www.postgresql.org/docs/18/datatype-character.html)：text/varchar 性能与字符/字节边界。
- [PG18 TOAST](https://www.postgresql.org/docs/18/storage-toast.html)：约 2 KiB 行阈值与 extended 含义。
- [PG18 HOT](https://www.postgresql.org/docs/18/storage-hot.html)：索引引用列不变且页空间足够是 HOT 前提。
- [PG18 行锁](https://www.postgresql.org/docs/18/explicit-locking.html)：KEY SHARE/NO KEY UPDATE/UPDATE 冲突与长事务。
- [PG18 部分索引](https://www.postgresql.org/docs/18/indexes-partial.html)：查询必须能蕴含索引谓词。
- [PG18 约束](https://www.postgresql.org/docs/18/ddl-constraints.html)：FK 与唯一约束关系。
- [PG18 SELECT](https://www.postgresql.org/docs/18/sql-select.html)：SKIP LOCKED 适合队列式领取，不是通用一致性视图。
- [PG18 COMMENT](https://www.postgresql.org/docs/18/sql-comment.html)：COMMENT 运维语义。

以上为转述，没有大段引用。

## 证据与核验状态

RUN（exit 0）：`cat AGENTS.md CLAUDE.md`；读取工作流 common/{precedence,review-gate,verification-matrix,agent-report-template}.md 与 scenarios/external-docs.md；读取优化清单；`rg/sed/nl` 检视 schema.sql/repository.py/admission.py/lifecycle.py/tenant.py/models.py/__main__.py、原生 Alembic 与 engine/task_backend.py/maintenance.py；Python 只读解析 code-baseline.json/catalog-snapshot.json，核实 8 表 78 列 20 索引与注释 0。官方 web open 结果成功。DBA 专家交叉讨论后上述建议一致。

NOT RUN：生产库 DDL、迁移、补注释、服务重启、ANALYZE、EXPLAIN ANALYZE、容量/并发压测、crash/failover 测试、全部单元/系统测试。原因：本任务仅审查和记录，未授权实现；小库不适合作性能结论。

RECOMMENDED（未来实施）：新建库+当前首版升级两条路径；迁移失败回滚/版本校验；超长与 Unicode 规范化边界；成员停用/删除并发签 Key；Key 吊销和权限修改 REST/MCP 一致性；旧任务 token 重放/租约失效；请求执行时在线删空间/崩溃断连/任务续提；幂等到期与历史清理；代表性请求量下记录 WAL、HOT、dead tuples、autovacuum、锁等待、连接预算、P95/P99，再评估索引/fillfactor/清理批次。不得用仅三个空间的小库结果删除索引或许诺性能。

建议下一步：主审将 K01～K08 作为待实施项写入宽泛优化清单，不改运行库；首轮先做已确认的结构/注释/约束与字段写入节流，索引与并发机制变更在独立验证环境评估。
