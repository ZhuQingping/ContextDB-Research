# 原生 Hindsight v1.0.0：节点部署合同

供管控与 ECS 节点 Agent 对接。本文只使用上游 `v1.0.0`（`39c65ffe2f140d0c84cee58566cad8900c5b9908`），不加载 ContextDB 自研扩展。具体命令见[操作指南](contextdb-service-integration-guide.md)。辅助脚本在 [deployment/native-v1.0.0](https://github.com/ZhuQingping/hindsight/tree/9d51cacde496baa628408e4b474f0f949220a90f/hindsight-extensions/contextdb-service/deployment/native-v1.0.0)，脚本由节点 Agent 执行，不修改 Hindsight。

## 一、交付边界

管控创建 ECS/RDS、数据库、服务账号、网络和 TLS，提供 MaaS Key、客户指定的 UI 密码。节点 Agent 拉取固定版本，写入配置，监管 API、Worker、UI；服务启动、升级和重启均通过 Agent 的进程/容器管理能力完成。Hindsight 没有“创建 ECS 实例”接口。

API 默认监听 `0.0.0.0:8888`，UI 默认 `0.0.0.0:9999`，端口可配置；远端经 ECS 安全组、路由及反向代理访问。UI 到 API 使用服务端地址，不能把浏览器地址当作容器内地址。本材料使用官方1.0.0-slim镜像及固定摘要，首版由 Agent 启动一个容器，容器内一个 Python 主进程运行 API/内置 Worker，一个 Node.js 主进程运行 UI。复用镜像原生 start-all.sh 监督启动和退出，不另启独立 Worker；PG 和 MaaS 外置。

| 能力 | 原生模式 |
| --- | --- |
| 空间 | 使用原生 Bank；多个 Bank 同属一个 `public` schema |
| API 认证 | 原生 `ApiKeyTenantExtension`，一个共享 Key 可访问全部 Bank，包括创建和删除 |
| UI 登录 | 客户输入 UI 密码；API Key 仅由 UI 服务端配置 |
| 用户、逐空间 Key 授权 | 本模式不提供；不能承诺客户之间权限隔离 |
| 自研管理接口、pepper、ctxdb_meta | 不使用 |

原生 Key 与 UI 后台 Key 相同，UI 登录密码独立。`HINDSIGHT_API_TENANT_API_KEY` 是完整 Key，不是 `MySQL:key1,PG:key2` 映射。不要把本联调配置当作已具备 ContextDB 成员权限模型的产品版本。

## 二、管控输入

`intent.example.json` 是完整的非秘密配置示例。`render.py` 拒绝未知字段、错误端口及已有输出，避免重试时换掉凭据。

| JSON 字段 | 规则 / 默认值 |
| --- | --- |
| database_url_file | 必填，绝对路径；UTF8 私密单行文件，权限 0600 |
| maas_api_key_file | 必填，同上 |
| ui_password_file | 必填，同上；客户密码至少 16 字符 |
| topology | 首版填写 `merged`；独立 Worker 仅保留为后续调研能力，不在首版部署流程中选择 |
| text_search | 首版 RDS 固定 `native`，内置英文全文，不要求另装全文插件 |
| ui_api_url | 必填，UI 服务端可达的 API origin；首版为容器内部 `http://127.0.0.1:8888`，随 API 端口修改 |
| api_port / ui_port | 默认 8888 / 9999，整数 1024–65535，不得相同 |
| db_pool_max | 默认 10，整数 2–100；每个进程的主池和读池各有独立预算 |
| llm_model | 默认 `deepseek-v4.1-flash`；首期固定，不展示为客户选项 |
| pg_search_tokenizer | 首版不填写；pg_search/中文 tokenizer 不属于本期 RDS 部署依赖 |

脚本生成私密目录（0700）下的 `api.env`、`ui.env`、`api-key`、`ports.env`（0600）。API Key 使用 48 字节随机数生成，持久化在此目录；重启复用原文件。不要重新渲染或在日志中输出文件内容。节点 Agent 应以临时目录完整生成后原子发布目录；部分失败时保留现场，不能以“重试”为由再生成一套凭据。备份秘密配置，轮换共享 Key 需要同步 API/UI 并重启，旧业务客户端随后失效。

## 三、PG 合同

一实例一专用 UTF8 数据库，先建库；指定的外部数据库不存在时启动失败，Hindsight 不会创建数据库。服务账号拥有数据库及业务 schema，可以迁移表/索引和创建 Bank，拒绝 SUPERUSER、CREATEDB、CREATEROLE、BYPASSRLS。安装扩展由 PG 管理员完成，运行时不依赖超级用户。

必须交付：IP/DNS、port、database、user、password 和已启用扩展清单。数据库 SSL 为可选项；仅选择证书校验时补充受信 CA 配置。URL 格式：

```text
postgresql://USER:PERCENT_ENCODED_PASSWORD@PG_HOST:5432/DATABASE
```

URI 中的密码必须百分号编码。容器内 `127.0.0.1` 指容器本身；RDS 使用实际 DNS。默认不指定 sslmode，按客户端默认策略连接，不要求 PG 已启用 SSL，也不要求客户端证书。若要明确不使用 SSL，可自行追加 `sslmode=disable`；若要启用完整服务器身份校验，则自行追加 `sslmode=verify-full&sslrootcert=/run/ca/pg-ca.pem`，并只读挂载对应 CA。部署器原样使用输入 URL，不强制添加或移除 SSL 参数；该选择不改变 PG 用户名/密码认证规则。

| 扩展 | 用途 / 选择 |
| --- | --- |
| vector | pgvector 向量列和索引，必需；SQL 名为 `vector`，配置值为 `pgvector` |
| pg_trgm | 字符串相似匹配，推荐安装；不承担中文分词 |
| btree_gin | 复合 GIN 索引的普通类型操作符类，推荐安装；不是全文引擎 |
| 原生全文 native | 英文：`english`；不需要另装全文扩展，不能据此承诺中文分词质量 |
| pg_stat_statements | 可选 SQL 诊断；预加载和重启由 PG 运维安排，不是 API 就绪的先决条件 |

二进制安装与每库 `CREATE EXTENSION` 是两步。`public` 中扩展的类型/函数/操作符可由其他 schema 的对象使用，需 USAGE 和正确 search_path；并非只有 public 的数据才能使用。首版选择 native + english，不安装 PGroonga/Groonga。中文内容及向量召回仍可使用，不承诺中文分词关键词全文；其他全文后端保留在上游能力与调研记录中，当前 RDS 部署不选择。

客户若拥有 PG 超级用户或服务对象所有者权限，就能修改业务及元数据，应用认证无法阻止。强隔离须由托管 PG 权限边界保证，禁止给客户服务 owner 账号。普通客户只经 API 访问；提供 SQL 查询时另建只读受限角色。

## 四、运行变量

`render.py` 实际写出以下变量；秘密值来自文件，不在本合同中列明。

| 变量 | 值及含义 |
| --- | --- |
| PYTHON_DOTENV_DISABLED | `1`，使用依赖已有开关，阻止意外 .env 覆盖 |
| HINDSIGHT_API_DATABASE_URL / DATABASE_SCHEMA | 上述 URL / `public` |
| HINDSIGHT_API_HOST / PORT / WORKERS | `0.0.0.0` / 配置端口 / `1` 个 API 进程 |
| HINDSIGHT_API_WORKER_ENABLED | 首版固定 `true`，在 API 进程内执行后台任务 |
| HINDSIGHT_API_WORKER_ID | `hindsight-native-worker-0`，同一实例重启保持稳定；不同独立数据库可使用相同标识 |
| HINDSIGHT_API_RUN_MIGRATIONS_ON_STARTUP | API=`true`，独立 Worker=`false`；先 API 就绪再启动 Worker |
| HINDSIGHT_API_MIGRATION_ISOLATION | `false`；迁移在当前进程执行，便于节点 Agent 管理生命周期 |
| HINDSIGHT_API_DB_POOL_MIN_SIZE / MAX_SIZE | `1` / db_pool_max |
| HINDSIGHT_API_READ_DB_POOL_MIN_SIZE / MAX_SIZE | `1` / db_pool_max；不同于主连接池 |
| HINDSIGHT_API_TENANT_EXTENSION | `hindsight_api.extensions.builtin.tenant:ApiKeyTenantExtension` |
| HINDSIGHT_API_TENANT_API_KEY | 脚本生成的共享 Key；通过 Bearer 访问 REST/MCP |
| HINDSIGHT_API_MCP_ENABLED | `true`；不设置 MCP_AUTH_TOKEN 或禁用租户认证 |
| HINDSIGHT_API_VECTOR_EXTENSION | `pgvector` |
| HINDSIGHT_API_TEXT_SEARCH_EXTENSION | 首版 `native`；NATIVE_LANGUAGE=`english` |
| HINDSIGHT_API_TEXT_SEARCH_EXTENSION_PG_SEARCH_TOKENIZER | 仅选择 pg_search 时写入 |
| HINDSIGHT_API_LLM_PROVIDER / BASE_URL / MODEL / API_KEY | `openai` / `https://api.modelarts-maas.com/v2` / 固定模型 / MaaS Key |
| HINDSIGHT_API_EMBEDDINGS_PROVIDER | `openai` |
| HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL / MODEL / API_KEY | `https://api.modelarts-maas.com/v1` / `bge-m3` / MaaS Key |
| HINDSIGHT_API_RERANKER_PROVIDER | `siliconflow`，复用其 query/documents 协议适配 |
| HINDSIGHT_API_RERANKER_SILICONFLOW_BASE_URL / MODEL / API_KEY | 同一 `/v1` / `bge-reranker-v2-m3` / MaaS Key |
| HINDSIGHT_API_LOG_LEVEL / LOG_FORMAT | `info` / `json` |
| HINDSIGHT_CP_ACCESS_KEY | UI 登录密码，独立于 API Key |
| HINDSIGHT_CP_DATAPLANE_API_URL / API_KEY | UI 后台地址 / 同一共享 API Key；不交给浏览器 |
| HOSTNAME / PORT | UI 绑定 `0.0.0.0` / 配置端口；不要误用 ContextDB 自研启动变量 |

Embedding 不设置 `HINDSIGHT_API_EMBEDDINGS_OPENAI_DIMENSIONS`；原生初始化探测 bge-m3 的 1024 维，避免向 MaaS 发送不支持的 dimensions 字段。更换维度或模型不能直接复用旧向量索引。Rerank 发 `query`，LLM `/v2` 与 embeddings/rerank `/v1` 不可混用。

首版固定单容器合并部署，API 内置 Worker，UI 同容器独立进程。Agent 只管理一个容器和 8888/9999 两个端口。减少部署对象和配置；代价是资源、故障和重启绑定。后续明确出现独立扩容或资源隔离需求后再评审拆分，本期不要求管控实现多种部署拓扑。Compose 的 2 vCPU / 4 GiB 仅为联调示例上限，可按节点调整；ECS/容器生产规格待压测确定，不固定要求节点4 vCPU/8 GiB或预留一半资源，详见[组件资源与磁盘预算](../contextdb-resource-sizing.md)。

## 五、替换 ContextDB 内核的边界

可复用 PG/MaaS/网络、API/UI 端口、Agent 启停和健康探测。原生 retain/recall/reflect URL 与主要请求格式继续保留。ContextDB 版本另有元数据初始化、管理员 Key、四个扩展入口、按空间 schema 及管理接口，不能仅把镜像标签换掉就自动获得权限和数据迁移。

联调 Bank 与测试数据可重建。需要保留原生 public 中的数据时，必须另做导出/导入与授权迁移验证；本文不承诺原库原地无损切换。参考[扩展版部署合同](../contextdb-deployment-contract.md)。


容器材料：`compose.yaml`只启动一个服务 hindsight，挂载 api.env 和 ui.env；API、UI 属同一容器和 UID 的信任边界，原生子进程继承入口环境，不提供组件级秘密隔离。原生单Key模式下API本身仍需要共享Key明文；这与ContextDB版本的PG摘要认证不同。Agent以非rootUID运行容器，并保证0600配置与此UID匹配。文件更新须在停服务后完成，再重建相关容器挂载，不删除PG数据或更换凭据。
