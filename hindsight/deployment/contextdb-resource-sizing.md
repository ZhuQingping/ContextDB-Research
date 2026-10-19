# 首版部署形态与资源预算

适用范围：Hindsight v1.0.0 原生联调及当前 ContextDB 自研版。**一个容器、两个应用主进程**：Python 运行 API 和内置 Worker，Node.js 运行 UI。RDS PG、MaaS 和宿主机节点 Agent 在容器外；不启动本地模型或嵌入式 PG。

## 1. 为什么首版这样部署

首版固定 `topology=merged`，减少容器、配置及排障分支。UI 通过 `http://127.0.0.1:8888` 访问同容器 API，外部仍开放可配置的 API 8888、UI 9999 两个端口。Worker 与 API 同进程，读取 PG 原生任务系统；无需额外 Worker 端口。

原生镜像复用官方 start-all.sh；自研版用 service.sh all 监督现有 api/ui 入口。启动先让 API 就绪，UI 再提供页面。正常停止需把 SIGTERM 转发到子进程并等待；自研监督器在任一应用进程退出后清理另一个进程。Compose stop_grace_period 为45秒，进程清理预算30秒。Docker restart 策略处理进程退出；健康检查失败不会自动重启，持续异常由现有节点 Agent 处理。

代价是组件共享资源、故障和重启绑定；同一 UID、同一容器不构成秘密强隔离。以后明确出现后台挤占在线请求、独立扩容或独立恢复需求后，再评审分容器，当前不让管控维护两套部署流程。历史分容器实验保留作对照，不作本期推荐。

## 2. CPU、内存分别花在哪里

下表的预算是外部 MaaS、小批量请求的**工程起点，不是本次实测峰值或生产容量保证**。API 与 Worker 共用一个 Python 进程，不能把两行当作两个独立进程的常驻内存相加。

| 组件 | CPU 的主要开销 | 内存的主要开销 | 首版预算解释 |
| --- | --- | --- | --- |
| API | HTTP/MCP、认证、文本切块与计数、结果解析/融合、JSON 编解码；同步 Retain/Recall/Reflect 也在此执行 | Python及依赖、连接池、缓存、在途文本/候选/向量和响应 | 与 Worker 合计预留约2 GiB正常工作预算，余量承受批次/并发波动；共用容器2 vCPU，不作独立CPU配额 |
| 内置 Worker | 任务轮询/调度、抽取结果解析、合并及批处理；等待 PG/MaaS 时不是持续占满 CPU | 与 API 共用基础运行时；每个在途任务额外持有文档、切块、模型响应和批次状态 | 不重复计一套 Python基础内存；并发及批量增加会提高同一进程峰值，须实测并限制任务并发 |
| UI | Node.js 处理页面、登录会话、服务端代理和结果序列化；交互渲染主要在浏览器 | Node/Next运行时、请求与响应缓冲及缓存 | 官方建议约256 MB；本方案先预留512 MiB，不作为512 MiB硬上限或并发保证 |
| init/监督器 | 信号、进程状态及健康检查 | 少量管理开销，计入整体余量 | 不另配业务CPU预算 |

三个模型都由 MaaS 推理，所以节点无须 GPU、模型权重或本地推理内存。向量/全文索引、排序及大部分持久检索由 PG 执行，消耗 RDS 的 CPU/内存/磁盘；不能把 RDS 开销算成“节点几乎不耗资源”。远端模型慢时连接和在途对象仍占内存，不能认为等待网络没有成本。

官方 v1.0.0 安装说明给出 Slim API 约512 MB最低、1 GB建议，UI约128 MB最低、256 MB建议；独立 Worker另计。这里使用更宽松的合并容器预算，避免把低并发启动下限当作产品规格。依据：[固定 v1.0.0 安装说明](https://github.com/vectorize-io/hindsight/blob/39c65ffe2f140d0c84cee58566cad8900c5b9908/hindsight-docs/docs/developer/installation.md)、[官方内存规划说明](https://hindsight.vectorize.io/guides/2026/04/28/guide-size-hindsight-memory-footprint-for-deployments)。

## 3. 示例资源限制与待确认规格

| 对象 | 初始建议 | 说明 |
| --- | --- | --- |
| Hindsight容器 | Compose示例上限 **2 vCPU / 4 GiB**，可覆盖 | 仅为既有联调配置，不是官方推荐或产品最小/标准规格 |
| ECS节点 | **待目标负载压测确定** | 不固定要求4 vCPU/8 GiB，也不将其中一半资源预留为空闲；系统、Docker、Agent和监控占用单独观测 |
| 节点磁盘 | **40 GiB可用容量起步** | 覆盖一套系统、镜像轮换和有限日志；基于已有系统盘时核对实际剩余空间，不重复计算系统占用 |
| RDS PG | 独立选型 | 按文档量、切块量、索引、读写并发、连接上限及备份保留测算，不能从容器规格推导 |

4 vCPU/6 GiB容器和4 vCPU/8 GiB节点的组合没有官方或本次压测依据，不作为交付标准。CPU上限限制可用算力，不是专门给系统预留CPU；单实例节点可按实际规格调整。内存上限需根据宿主机与容器的实际峰值确定，不预设固定扣留2 GiB。

用 `HINDSIGHT_CPUS/HINDSIGHT_MEMORY`（原生）或 `CONTEXTDB_CPUS/CONTEXTDB_MEMORY`（自研）覆盖Compose默认值；这两个变量只控制容器资源，不增加API进程或改变任务并发。API进程数固定1，Worker ID重启稳定。tmpfs最大256 MiB及自研UI缓存64 MiB按使用量消耗内存，已包含在容器4 GiB内，不是额外赠送容量。

当容器内存持续接近上限、CPU节流或任务积压时，先区分批量/并发、PG、MaaS配额和网络瓶颈；调小批量/并发或提高整体规格。明确有组件独立扩缩容需求后再拆分，不能用加CPU解决MaaS限流或PG慢查询。

## 4. 磁盘大小与数据去向

| 类别 | 存放位置与预算 |
| --- | --- |
| 镜像 | 节点Docker存储；本机ARM64 `docker image ls`显示官方1.0.0-slim约1.33 GB、自研旧验证镜像约1.19 GB，是解压后逻辑大小，不是压缩下载量或本次新镜像大小。API/UI共用同一镜像，不按进程重复占三份；保留新旧版本和拉取临时空间时先预留约6～10 GiB，按目标架构实际镜像复核 |
| 业务数据与索引 | 外部PG，节点不保存一份本地业务数据库；文档、切块、记忆、向量、全文/图索引以及数据库日志/审计都要计入RDS增长 |
| 配置和秘密 | `/srv/hindsight/runtime`或`/srv/contextdb/runtime`，通常很小，但必须持久化并加密备份；不能随容器删除或重新生成 |
| 运行日志 | stdout/stderr交Docker；当前json-file每个容器20 MiB×5轮换文件，约100 MiB量级，不是完整审计保留方案。Agent采集副本、journald和其他服务日志另计，日志不打印密钥 |
| 临时文件与缓存 | 上传、导入导出、批处理可能增加临时占用；自研示例/tmp为256 MiB tmpfs，UI缓存64 MiB tmpfs，可丢弃但消耗内存。大文件操作须另定限制与临时卷容量，不默认支持任意大小 |
| 构建缓存 | 仅构建机：Python/npm依赖、源码和多阶段构建层，可能明显大于运行镜像；不计入运行节点预算，节点应拉取批准镜像而非现场编译 |

1024维float32向量的原始数值约4 KiB/条，**不等于PG每条记忆只占4 KiB**；还要计文本、行开销、索引、关联及WAL。通过实际数据的 `pg_database_size`、`pg_total_relation_size` 及备份/WAL保留增长规划RDS，不能只乘原始向量大小。

检查节点实际占用：

```bash
docker image inspect "$NATIVE_IMAGE" --format '{{.Size}}'
docker system df
df -h /srv /var/lib/docker
```

自研镜像把NATIVE_IMAGE替换为CONTEXTDB_IMAGE；Docker Root Dir不是/var/lib/docker时按实际路径查询。不要自动执行全局prune删除其他服务的缓存或镜像。

## 5. 如何验收资源预算

先确认一个运行容器、两个应用主进程（另有监督器/健康探测），再测空闲、持续写入、纯查询、混合读写及大批次；记录文档大小、并发、任务并发、模型与PG规格，不只记录一次启动值。

原生项目示例；自研替换项目名、Compose路径和变量：

```bash
CONTAINER=$(docker compose --env-file "$RUN/ports.env" -f "$HELPERS/compose.yaml" -p hindsight-native ps -q hindsight)
docker stats --no-stream "$CONTAINER"
docker top "$CONTAINER" -eo pid,ppid,comm,rss
```

容器总体指标是资源限额依据；RSS只能解释各进程开销，共享页可能重复，不能把各进程RSS之和当作容器精确内存。采样CPU、内存峰值、OOM/重启、CPU节流、磁盘/日志增长，并联看API p50/p95、异步队列积压、PG连接/慢查询、MaaS错误和限流。测试正常停止和故障退出后没有遗留服务，再重启验证同一凭据、UI和任务恢复。

## 6. 本次单容器验证（2026-10-19）

原生官方1.0.0-slim镜像和自研镜像均已按一个运行容器启动，通过API/UI联合健康检查、真实MaaS Retain/中文Recall/Reflect、UI密码登录和异步任务完成；自研版另通过两空间及逐Key读写隔离、管理越权拒绝、删除同名重建隔离。自研验证镜像在上一轮已验证镜像上只覆盖本次启动脚本，未重新构建UI；正式发布仍须用当前Dockerfile完整构建并记录源码及镜像摘要。

本机Colima ARM沿用已记录的OPENSSL_armcap=0兼容覆盖；不将它写入ECS默认配置。单次轻负载采样：官方容器475.7 MiB、自研容器386.6 MiB；两个镜像的API进程RSS均约346 MiB、UI约116～121 MiB。采样时点不同，共享页/缓存统计口径不同，不按RSS相加比较容器总内存，不据此评价两个版本效率或估算峰值。

部署/监督器专项测试29项通过，1项可选测试跳过；新测试覆盖正常SIGTERM、任一主进程正常/异常提前退出时终止另一进程。两个真实容器还分别终止UI进程，确认整个容器自动重启、API/UI重新健康、原UI密码可继续登录。上述功能与瞬时内存证据不是混合负载压测。目标ECS默认CPU兼容、RDS恢复和生产容量仍需独立验收。
