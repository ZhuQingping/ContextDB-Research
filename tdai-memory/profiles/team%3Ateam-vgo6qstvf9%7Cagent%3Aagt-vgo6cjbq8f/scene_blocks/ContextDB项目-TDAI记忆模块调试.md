-----META-START-----
created: 2026-09-22T05:28:35.047Z
updated: 2026-09-22T10:15:19.899Z
summary: zhuqingping（TencentDB-Agent-Memory MemoryCore 开发者，负责 VectorStore/SQLite 与 embedding 接入）调试 tdai：L0→L3 跑通（glm-5.3-flash、JSONL↔DB 对账差集归零）；embedding 排障闭环：bge-m3 不支持 matryoshka（400 ModelArts.81001）→ sendDimensions 开关 → store-pool.ts createSqliteStore() 未透传代码级根因修复 → 09:42 重启写入端闭环（l0_vec 14/15 条 1024 维向量、norm=1.0、sqlite-vec v0.1.7-alpha.2 linux-arm64 已加载、零新增错误）；l1_vec=0 行（存量 L1 均修复前写入、无向量）；检索端 401（换有效 Bearer token）后 vec0/hybrid 双路径仍 0 候选 0 命中——向量已在库而召回为 0，读端收窄至 query 侧待查；provider=proxy 经 /proxy/<iid>/v1+TDAI_MEMORY_SYSTEM_USER_KEY 集成 MemoryProxy；本地源码 /Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryCore。
heat: 25
-----META-END-----

## 用户基础信息
- 用户名：zhuqingping
- 职业：开发者（腾讯云 TencentDB-Agent-Memory / ContextDB 记忆系统研发），负责向量存储（VectorStore/SQLite）与 embedding 服务接入代码
- 项目：MemoryCore（tdai-memory-core）+ tdai-gateway（Docker 容器部署，v2-router 承载 L0 embedding 调用），TypeScript/Node.js；存储 SQLite 向量库（BM25 enabled，dbPath=/data/tdai-memory/vectors.db，sqlite-vec v0.1.7-alpha.2 linux-arm64 扩展）+ 远程 OpenAI 兼容 embedding（Huawei ModelArts MaaS https://api.modelarts-maas.com/v1，bge-m3，provider=openai、dimensions=1024）
- 本地源码：/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryCore（macOS）；成果文档《TecentDB Agent Memory.md》
- 另一在研项目：MemoryProxy，MemoryCore 以 provider=proxy 调用它，详见 MemoryProxy-开发调试.md

## 用户核心特征
用户是腾讯云分层记忆系统 MemoryCore 的核心开发者，调试风格极度系统化：故障必追到代码级根因，验证讲究读写双向端到端闭环与单变量隔离，对"配置声明与运行时实际生效路径脱节"的静默失败高度警觉——该直觉已被 store-pool.ts 透传缺失实证。

## 用户偏好
- 端到端验证读写双向：写入核对落库向量（embeddingDims=1024、embeddingNorm=1.0000），检索核对 vec0 向量路径与 hybrid 双路径召回
- 直查物理落库状态作闭环终检：sqlite-vec 扩展版本、l0_vec/l1_vec 行数、向量维度与 norm 逐一核对
- 根因追到代码级：env 已设且 resolved 正确仍复现时，沿 createStoreBundle→createSqliteStore→createEmbeddingService 调用链找参数透传断点
- 单变量隔离实证（裸请求→逐层加参数）、Mac+容器双环境 curl、配置修复必验 resolved 解析层
- 真实数据说话：JSONL↔DB 差集、l0_fts 行数、向量 dims/norm 落库核对
- 工具栈：LLM 提取 glm-5.3-flash（弃慢速 glm-5.3）、embedding bge-m3（ModelArts MaaS）；成果文档化
- 检索设计 filter 先行、embedding 慎用

## 隐性信号
- store-pool.ts 透传缺失被实证后，他对配置链的信任边界已降到"代码级接线核查"，而非 resolved 输出——后续每条配置大概率都做调用链核查。
- "0 total errors" 仪表与 L0 静默降级（metadata-only）并存：指标健康≠链路健康，embedding 失败不计错、落库无告警的监控盲区是其隐性痛点，可能推动可观测性改进。
- 写入端刚闭环立即转检索端验证：他对"端到端"的定义包含读召回，写入成功≠系统可用。
- l0_vec 已确认 14 条向量在库而双路径仍 0 候选——"库空"假设被排除，怀疑面收窄到 query 侧：query embedding 是否真的发出并返回向量、vec0 虚表绑定与 metadata 过滤是否匹配、hybrid 的 FTS 侧状态。
- l0_vec 14/15 的 1 条缺口与 l1_vec 全 0 说明故障期数据是"metadata-only 幽灵行"：他不假设系统自愈，存量补写大概率需显式执行并回归验证。
- 镜像缺 tsx 未即时修而先保主链路：问题隔离优先于顺手修复。

## 核心叙事
2026-09-22 凌晨 L1 episodic 恒为 0（**触发**），定位根因为 l1-extractor 180s 超时+glm-5.3 过慢+llmRunner 忽略 model 参数，切 glm-5.3-flash 跑通 L0→L3，并以 MySQL-Code-Review Agent 完成 JSONL↔DB 对账（差集归零）。随后沿零向量下探：bge-m3 拒收 dimensions（400 ModelArts.81001，不支持 matryoshka），遂将修复落为 sendDimensions 开关（默认 true 兼容 OpenAI text-embedding-3-*，BGE-M3 需 false），设 env 并验证 resolved 后仍 400（**行动**）——追至代码级根因：store-pool.ts 的 createSqliteStore() 调 createEmbeddingService 未透传 sendDimensions。09:41-09:42 修复透传并重启（09:42:04 listening），L0-upsert 向量写入 sqlite 成功（1024 维、norm=1.0000、重启后零错误），写入端闭环；检索端随即暴露断层：先 401，修正为有效 Bearer token 后 vec0 与 hybrid 双路径仍 0 候选 0 命中。09:44 直查落库状态收口：sqlite-vec v0.1.7-alpha.2（linux-arm64）确认已加载，l0_vec 积累 14/15 条 1024 维向量（provider=openai、model=bge-m3、dimensions=1024），l1_vec=0 行——存量 L1 记录均为修复前写入、无向量，400 根因同步坐实（**结果**）。关键张力：向量已在库而召回为 0，读端问题收窄至 query 侧，排障进行中。

## 演变轨迹
- [2026-09-22]: L1 提取模型从 glm-5.3 转向 glm-5.3-flash（180s 超时下速度优先），并扩展为跨项目统一快速模型
- [2026-09-22]: 验证标准从"功能跑通"升级为"验证+对账"双重闭环，再到"表结构+配置面+模型能力"三层审计与容器内运行时实证；进一步确立"读写双向端到端"标准（写入闭环后必验检索召回），并以直查物理落库状态（向量表行数/维度/扩展版本）作为闭环终检
- [2026-09-22]: 新增认知：dimensions 非普适参数（matryoshka 专属），sendDimensions 是为兼容差异模型生态设计的开关；配置链验证必须下探代码级参数透传（store-pool.ts 教训）；provider=proxy 有独立系统密钥体系

## 待确认/矛盾点
- 读端 0 候选/0 命中根因未定，"库空"假设已被 l0_vec 14 条向量排除；剩余怀疑：query embedding 是否真的发出并返回向量、vec0 虚表绑定/metadata 过滤是否匹配、hybrid 的 FTS 侧状态
- 存量补写未执行：l1_vec=0 行确认存量 L1 均为修复前写入、无向量；l0_vec 14/15 有 1 条缺口（疑故障期写入），旧零向量行是否显式补写待确认
- gzip CE/CT 头剥离（应用内 OpenAIEmbeddingService JSON 解析失败）的修复动作未记录，但 09:42 后写入已通——代码修复还是服务端行为变化待澄清；剥离确切位置（服务封装层 vs undici）仍未定
- env 场景 PARTIAL（provider=none）根因待回归确认；容器缺 tsx 修复路径（Dockerfile 依赖 vs 预编译）未定
- 本地源码路径记录不一致：新记录 /Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryCore vs 早前 /Users/zhuqingping/Work/Database/Context/ContextDB-Research/——两个 checkout 还是笔误待澄清
- provider=proxy 的 <iid> 与 MemoryProxy 路由/密钥隔离对应关系待澄清
- pipeline-worker lock conflict parked（depth=4）根因未定位
