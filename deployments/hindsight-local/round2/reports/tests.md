# 测试与流水线：核对和本地验证

基线：`f7dd3f4fd7420f7beec60c32c965e5e5cf7be066`，Hindsight 0.10.2；本机 macOS arm64 / Python 3.12.13。只读上游源码，使用 `git archive HEAD` 副本 `round2/tests-work/source`，独立虚拟环境及 PG，未改测试断言。上游 CI pin Python 3.11；本次3.11下载未完成，采用已安装3.12，不能替代Linux/Python3.11生产流水线。

## 结论

没有一个“完整用例命令”能够证明全部功能完备。上游将机制正确性、真实模型行为、模型质量、SDK、客户端插件、UI、升级分别验证。服务化开发应复用这些层，再补你们自己的鉴权、租户、配额、删除、容灾用例。假模型的系统测试通过，不等于真实模型准确率或真实 Claude/Codex/Hermes/OpenClaw 会话通过。

最适合每个 PR 必跑的是 `hindsight-system-tests`：真实 API 进程、PG 和 Python SDK，经HTTP访问本地 stub LLM/Embedding/Rerank。模型请求结构与后台处理是真实路径，但模型答案/向量/排序是测试替身；不需要付费凭据或下载模型。源码：`hindsight-system-tests/README.md`、`hindsight_system_tests/server.py`；CI：`.github/workflows/test.yml:3595`。本基线收集到322例，默认独立PG15499。

## 上游分层及推荐门禁（建议，非已部署流水线）

| 层 | 上游入口 | 验证内容 | 产品门禁 |
|---|---|---|---|
| 静态检查 | `ruff check hindsight_api`、`ty check hindsight_api` | 代码规范/类型 | 每PR；0错误 |
| API机制 | `hindsight-api-slim/tests`；CI非LLM选择 `-m "not hs_llm_mat and not hs_llm_core"` | 函数、配置、数据库操作、错误重试 | 每PR；按依赖拆unit/PGintegration；跳过项必须逐项说明 |
| 系统组合 | `hindsight-system-tests/tests` | 写入/召回/替换/删除/整合/任务/知识页/隔离等组合 | 每PR，全部执行；0失败0错误 |
| 真LLM行为 | `pytest tests -m hs_llm_core`、`-m hs_llm_mat` | 抽取/提示词行为，独立judge；多个provider接入 | 夜间和模型/提示词变更；仅产品承诺支持的模型组合 |
| SDK与接口 | Python/TS/Rust/Go client tests；`client-coverage-check`、OpenAPI兼容检查 | 参数透传、SDK调用、API变更 | 公布的SDK必须测试；覆盖清单不是功能执行测试 |
| UI | `npm test --workspace=hindsight-control-plane`，`i18n:check`，build | 组件/构建与资源启动 | UI变更必跑；另补浏览器实际任务路径 |
| 客户端插件 | 各 `hindsight-integrations/<client>` tests | hook/配置/打包/传输 | 声明支持的客户端分别跑；mock插件测试不能代替真实客户端 |
| 真实模型质量 | `hindsight-system-evals`、AMB | 归纳质量、幻觉、来源优先级、语言/事实忠实性、Token成本 | 发布前固定模型/数据/设置做基线，比较多次运行；不把一次通过当准确率 |
| 升级与生成物 | `hindsight-dev/upgrade_tests`，生成OpenAPI/SDK后检查diff | 历史数据迁移、接口兼容、生成物同步 | 每次上游升级必跑，并测试备份恢复 |
| 云层新增 | 需你们实现 | 租户越权、Bank ACL、撤权、限额、幂等、任务受理、删除衍生、恢复 | 未通过不得上线；上游Bank隔离不等同云IAM验证 |

上游CI确有 secret-gated job：`test-api` 1926行依赖GCP/OpenAI/Cohere等凭据，拆3 shard；核心LLM 2027行；matrix 2118行附近。不要照抄“全部PR通过”而忽略跳过的job。

## 可复制执行方法

以下在隔离开发checkout执行；不要指向现有演示库/生产库。`.env` 对上游API测试具有 `override=True`，必须检查它不会覆盖独立数据库及模型配置（`tests/conftest.py:200`）。

```sh
# 1. 最小系统测试（上游原命令）
(cd hindsight-api-slim && uv sync --frozen --extra embedded-db)
(cd hindsight-system-tests && uv sync --frozen)
(cd hindsight-system-tests && PYTEST_ADDOPTS='' uv run pytest tests -v --junitxml=system.xml)

# 2. API全依赖及非LLM套件：与上游CI一致，但可能仍有外部provider依赖
(cd hindsight-api-slim && uv sync --frozen --all-extras --index-strategy unsafe-best-match)
(cd hindsight-api-slim && uv run pytest tests -m 'not hs_llm_mat and not hs_llm_core' --junitxml=api.xml)

# 3. 真模型：在隔离环境注入批准的provider凭据；judge也要独立配置
(cd hindsight-api-slim && uv run pytest tests -m hs_llm_core --timeout 600 --junitxml=llm-core.xml)
(cd hindsight-api-slim && uv run pytest tests -m hs_llm_mat --timeout 600 --junitxml=llm-matrix.xml)

# 4. 契约覆盖（不是执行SDK完整suite）
(cd hindsight-dev && uv run client-coverage-check)
(cd hindsight-dev && uv run cli-coverage-check)
```

质量评测必须按 `hindsight-system-evals/README.md` 配置真实模型/独立judge及dataset。读取结果要区分召回没命中与模型推理失败。本文未执行AMB或宣布任何准确率。

每次发布固定：上游commit、产品层commit、依赖锁、镜像digest、PG版本/扩展、embedding模型与维度、reranker、LLM、全部关键配置。留存JUnit、skip理由、API/Worker日志、真实模型成本、升级前后数据对照。故障测试同时覆盖API与Worker分进程部署，不能只测默认内嵌Worker。

## 本次执行记录

结果以各 `evidence/tests-*/command.json`、`run.log`、`junit.xml` 为准。独立PG15499（系统）和15500（API），未操作主PG55432。

| 验证 | 结果 | 边界 |
|---|---|---|
| static-keys-tenant 全suite | 50 passed | 扩展单测，不是生产IAM验收 |
| 20个核心API测试文件 | 548 passed / 134 skipped | 配置、worker、retry、migration shape等；跳过部分需local-ml |
| API 非LLM过滤后全suite | **8509 passed / 2138 skipped / 4 xfailed / 8 failed / 5 errors** | 10660例完成，132.55秒；没有全绿 |
| Python SDK选定12文件 | 73 passed | API参数映射/重试等unit；没有运行全部真实API客户端suite |
| UI完整unit suite | TZ=UTC/Node24：286 passed，39文件 | 首次Asia/Shanghai 285 passed / 1 failed；非浏览器E2E |
| ruff / ty | 均exit 0 | API生产源码静态检查 |
| SDK覆盖检查 | Python 67/67参数；TS89/89参数；各51 Bank配置 | 仅清单中覆盖操作；非完整所有端点实测 |
| CLI覆盖检查 | 99操作中73实现/26显式跳过；126参数中67覆盖/59跳过 | exit 0表示清单闭合，不是99操作都实现 |
| 系统黑盒全suite | 321 passed / 1 skipped（327.25秒） | 真实API/PG/SDK，假模型；跳过的真实ONNX例随后单独通过 |
| 原suite的ONNX补测 | 1 passed（85.04秒） | 本机E5真实embedding、PG、API；LLM/reranker仍为stub |

### 非LLM全套件为什么没全绿

证据：`evidence/tests-api-nonllm/failure-analysis.json`，包含每个失败节点、异常和skip计数。没有修改源码或断言以消除失败。

- 5个fact extraction ratio失败+1个analysis setup错误：真实OpenAI模型需要key，但这些测试未被 `not hs_llm_core/hs_llm_mat` 排除。**“not LLM marker”不等于“完全不调用模型”。**
- 4个S3 fixture错误：testcontainers找不到Docker socket；不是OBS兼容性测试结果。
- 1个GitHub Copilot timeout测试失败：本机没有Copilot登录资料，不能凭空补token。
- 1个HTTP代理测试失败：上游测试仅覆盖HTTP_PROXY，继承的其他代理环境影响结果。仅对子进程清除小写proxy/ALL_PROXY/HTTPS_PROXY，原文件11例全过，见 `tests-proxy-cleanenv`；未修改用户环境。
- 1个CLI repair-bank测试失败：CliRunner读取输出报 `ValueError: I/O operation on closed file`，默认pytest捕获模式独立重跑复现，见 `tests-api-failure-recheck`；同一个测试仅加 `-s` 禁用pytest输出捕获后1 passed（`tests-cli-stdio-recheck`），提示CLI测试与捕获环境交互，不能直接定性为业务缺陷；目标Linux CI仍需复核。
- 2138 skips主要为1935例embedding fixture缺local-ml、8例reranker fixture缺local-ml，110例迁移无CONCURRENTLY操作正常skip，另有Oracle和厂商API凭据缺失等；详细分布保存在JSON。4 xfailed也不算通过。

UI时区问题：上游测试固定“现在”为2026-08-19T18:00Z、输入12:38Z。在上海时区这两个时间跨自然日，不能满足“当天只显示时分”的断言；UTC重跑全过。这里调整的是测试环境时区，不是用户产品时区。源码 `hindsight-control-plane/tests/lib/relative-time.test.ts:18`。首次安装环境Node23有engine warning，执行使用隔离npx Node24，不改全局Node。

SDK初次误用API环境，11个文件收集缺`aiohttp_retry`；改用已完整安装SDK依赖的系统测试venv，73例全过。首轮证据 `tests-python-sdk-unit` 和重跑 `tests-python-sdk-unit-retry` 都保留。

可审阅流水线草案：`scripts/tests_pipeline.example.yml`，仅给出已验证系统suite/static-keys命令在GitHub Actions的组织方式，未发布或运行远端workflow。真实模型、生产PG/OBS、API/Worker拆分故障注入、真实客户端和升级恢复必须另外设门禁，不能用此最小草案代替。

系统suite唯一个skip是 `test_76_onnx_embeddings.py` 未指定本地模型目录。补跑指定本机E5 snapshot，minimal API venv因缺transformers启动失败（证据tests-system-onnx）；换成隔离local-ml venv后原测试1 passed，验证了真实CPU ONNX retain→recall→原文替换。无CUDA测试。两次执行合计覆盖322例，不能表述为一次322例全绿。

## 补齐local-ml与构建（最终结果）

安装了独立 `tests-work/localml-venv`（`uv sync --frozen --extra embedded-db --extra local-ml`），没有修改原运行环境。原上游fixture的 BAAI/bge-small-en-v1.5 和 cross-encoder/ms-marco-MiniLM-L-6-v2 已下载并在CPU加载成功（`tests-localml-models`）。再次执行全API过滤suite，仅显式排除前述真实LLM两个文件、Docker S3文件与Copilot未登录一个参数例；原始失败证据保留，不把排除当通过。

首次local-ml重跑在HF元数据网络连接停留（一个worker持embedding初始化锁、对外IPv6 SYN_SENT）；主动SIGINT停止，3 passed/1 skipped，exit2，证据tests-api-localml。随后改为HF_HUB_OFFLINE=1读取已下载模型；不是替换模型或修改断言。最终离线运行已完成：**10477 passed / 185 skipped / 5 xfailed / 2 failed**，耗时1566.24秒，exit 1；无error。证据 `tests-api-localml-offline/command.json`、`junit.xml`、`failure-analysis.json`。

TypeScript SDK构建与UI生产构建（含standalone打包）均exit0，分别 `tests-typescript-build`、`tests-ui-build`，后者17.13秒；执行Node v24.21.0。UI i18n检查也exit0（tests-ui-i18n）。未启动这个新build对外提供服务，仍不能替代浏览器E2E。

### 并行与数据库隔离边界

上游 `hindsight-api-slim/pyproject.toml:205` 默认 `-n 8 --dist loadgroup`；CI `test-api` 再用pytest-split分3个独立runner，每个runner仍有8个xdist worker，共享本runner的pg0。**本机-n2是降并发，不是新引入并行**，但本机没有拆3个shard，全部文件在一个PG上执行，文件组合、调度和残留状态与CI不同。因此共享数据引起的失败不能直接归因产品，也不能拿本机重跑取代上游Linux CI。

建议正式流水线每job/shard使用独立PG；共享全库列表、schema迁移和DDL的机制用例按明确group/串行运行，避免把一个测试创建的Bank当成另一个测试的异常返回。生产服务的并发正确性另外用黑盒负载测试验收，不能通过减少业务并发或删除断言来“修复”测试。

隔离复现进展：在另一个全新PG15591，用相同代码/模型串行执行两个失败节点，2 passed；随后完整执行 `test_load_large_batch.py` 和 `test_bank_aliases.py`，24 passed（24.79秒）。证据 `tests-localml-issues-isolated`、`tests-localml-issue-files`。这些结果不能抹去完整并行suite的失败；完整trace确认：并发Retain测试9个任务报asyncio Lock绑定其他事件循环；Bank alias列表多出4条其他测试创建且名称包含搜索词的Bank。后者有运行中SQL查询证据，前者尚未定位到具体锁的生命周期根因；独立通过不证明生产并发无缺陷，需目标Linux原CI拓扑复核。

## 正式流水线依赖与上线门禁

最小可执行草案仍为 `scripts/tests_pipeline.example.yml`（system/static-keys两job）；它只说明接入方式，**不是完整上线流水线**。完整阶段定义在 `reports/tests-gate-manifest.json`，未安装/发布云CI。

| 阶段 | 前置 | 要求 | 本轮状态 |
|---|---|---|---|
| S0 固定构建环境 | 无 | commit/依赖锁/镜像/model snapshot/PG版本固定 | Mac环境验证；目标Linux未验收 |
| S1 静态与接口契约 | S0 | lint、type、SDK/CLI清单、对基线的OpenAPI兼容 | 前四项通过；没有新代码候选，未做跨版本兼容比较 |
| S2 API机制与PG集成 | S0 | 上游三shard，每job独立PG；0未解释失败；skip清单 | 本机-n2全suite及隔离重跑，结论见最终结果 |
| S3 系统黑盒 | S0 | 真实HTTP/API/PG/SDK，stub模型；启用承诺的真实ONNX测试 | 321+补测1通过；非真实模型质量验收 |
| S4 SDK/UI成品 | S1、S3 | SDK构建/运行套件、UI单测/i18n/build、浏览器关键任务 | 选定SDK73例与UI286例及build通过；全部SDK和新build浏览器E2E未跑 |
| S5 云服务合同 | S2、S3 | IAM/ACL/撤权/幂等/配额/受理/删除/分离Worker | 原型与本地机制证据由主任务提供；生产云集成未验收 |
| S6 真模型/真客户端夜间 | S3、S5 | 支持矩阵逐项；固定corpus和独立judge；模型/客户端升级重跑 | 真客户端由主任务提供；标准质量评测/华为MaaS/完整厂商矩阵未跑 |
| S7 升级与发布 | S1—S6 | 历史版本升级、生成物一致、RDS恢复/故障、OBS、负载/成本 | 尚未验收，不能把本机pg0测试当正式上线通过 |

**门禁规则：** 所声明能力的必需阶段必须在同一候选成品上通过。凭据缺失、客户端未安装、模型不支持、NOT_RUN和未解释skip都不能默默变绿；只能明确标记BLOCKED，或先从首期公开能力矩阵移除并记录范围决定。真实模型质量/成本/时延阈值要基于基线设定，本次不能凭空填一个准确率阈值。首次失败和复跑均保留。

各阶段已核对的上游CI路径、可复制命令及前置详见 `tests-ci-runbook.md`。manifest区分`entrypoint_templates`（需要输入的入口）、`planned_checks`（尚需实现的产品检查）和`executed_command_records`（实际运行argv/cwd/exit/time）；不能把阶段名当成已实现的脚本。

## 收尾状态

全套原始失败与隔离复跑均保留，没有改测试断言。凭据形状字符串已保守脱敏（可能是安全测试的合成fixture），记录在 `evidence/tests-redaction-manifest.json`，JUnit/JSON仍可解析。测试PG15499/15500/15591均正常停止、数据保留；主服务8888/9999/55432保留，见 `evidence/tests-cleanup.json`。

本轮完整入口见 [执行手册](tests-ci-runbook.md)。完整local-ml结果不等于生产认证：185 skip和5 xfail有逐项原因，缺外部凭据、CUDA、Oracle、真实TEI等不能计为通过；最初显式排除的真实LLM/S3/Copilot依赖仍需对应阶段补验。
