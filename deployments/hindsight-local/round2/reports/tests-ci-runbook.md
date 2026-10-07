# 可复制的上游流水线入口

本页是固定commit f7dd3f4fd 的执行手册；入口来自本地上游CI/README，并不表示这些阶段已全部执行。实际结果见tests.md及JUnit。命令均从**独立源码checkout根目录**启动，CI secrets预先注入批准的测试模型配置；不得指向演示/生产库。使用Linux runner、仓库`.python-version`和Node24；本机Mac/Python3.12验证不替代目标Linux验收。

## 1. 静态、API机制与系统组合

依据：上游 `.github/workflows/test.yml:1926`（API三shard）、`:3595`（system）、`hindsight-api-slim/pyproject.toml:205`（默认8 worker）。

```sh
(cd hindsight-api-slim && uv sync --frozen --all-extras --index-strategy unsafe-best-match)
(cd hindsight-api-slim && uv run ruff check hindsight_api)
(cd hindsight-api-slim && uv run ty check hindsight_api)
# CI matrix 的每个job传入自己的1/2/3；每个job一套全新PG，job内默认8个xdist worker
: "${CONTEXTDB_TEST_SHARD:?must be 1, 2 or 3}"
: "${HINDSIGHT_API_DATABASE_URL:?must be isolated test PG}"
(cd hindsight-api-slim && uv run --with pytest-split pytest tests -m 'not hs_llm_mat and not hs_llm_core' --splits 3 --group "$CONTEXTDB_TEST_SHARD" --junitxml=api.xml)

(cd hindsight-system-tests && uv sync --frozen)
(cd hindsight-system-tests && PYTEST_ADDOPTS='' uv run pytest tests -v --junitxml=system.xml)
```

前置：PG可安装vector/pg_trgm等迁移依赖；本地BGE/MiniLM模型已缓存。API测试会以源码根`.env`覆盖shell变量，必须使用隔离checkout并核对该文件。API的非LLM marker过滤后仍有6个未正确标记的真实LLM用例、Docker S3及Copilot登录依赖；完整CI应供给这些前置，或明确移到对应必需阶段，不能直接忽略后称完整通过。本机排除项及离线复现命令见 `scripts/tests_full_localml.sh`。system默认自建PG15499；真实ONNX用例需要`HINDSIGHT_TEST_ONNX_MODEL_DIR`及local-onnx依赖。

## 2. 真模型行为与provider矩阵

依据：`.github/workflows/test.yml:2027`（core）、`:2118`（acceptance）；独立judge参数见 `hindsight-api-slim/tests/llm_judge.py:26`。

```sh
: "${HINDSIGHT_API_LLM_PROVIDER:?approved provider required}"
: "${HINDSIGHT_API_LLM_MODEL:?pinned model required}"
# provider相应凭据由secret store注入；VertexAI可用服务账号，并非所有provider都有API key
# 另注入 HINDSIGHT_TEST_JUDGE_PROVIDER / MODEL / API_KEY / BASE_URL（按judge provider）
(cd hindsight-api-slim && uv run pytest tests -m hs_llm_core --timeout 600 --junitxml=llm-core.xml)
(cd hindsight-api-slim && uv run pytest tests -m hs_llm_mat --timeout 600 --junitxml=llm-matrix.xml)
```

每个对外承诺的provider/model组合单独一job；不要自动沿用上游OpenAI/Gemini/Groq名单当作华为云支持矩阵。供应商凭据、judge或模型缺失使该必需阶段BLOCKED/失败，不允许转换成绿灯。上游core配置有reruns，产品CI应同时留存首次结果，不用重跑隐藏失败率。

## 3. SDK与UI

依据：`.github/workflows/test.yml:2366`（Python）、`:2478`（TS）、`:3125`（Rust）、`:3241`（Go）、`:1484`（UI）。

前置：CI已经启动**候选版本的隔离API+PG**，配置批准的真实模型且health通过；设定API URL，测试自行生成/删除测试Bank。不要使用默认localhost:8888，那里可能是用户正在使用的服务。

```sh
: "${HINDSIGHT_API_URL:?isolated release-candidate endpoint required}"
(cd hindsight-clients/python && uv sync --frozen --extra test --index-strategy unsafe-best-match)
(cd hindsight-clients/python && uv run pytest tests -v --junitxml=python-client.xml)
(cd hindsight-clients/typescript && npm ci && npm run build && npm test)
(cd hindsight-clients/rust && cargo test --lib)
(cd hindsight-clients/go && go build ./... && go test -v -tags=integration)

npm ci --workspace=hindsight-control-plane --workspace=hindsight-clients/typescript
npm run build --workspace=hindsight-clients/typescript
TZ=UTC npm test --workspace=hindsight-control-plane
npm run i18n:check --workspace=hindsight-control-plane
npm run build --workspace=hindsight-control-plane
```

Python/TS/Rust/Go是可复制的**各语言完整入口**，本轮只执行选定Python unit、TS build和UI全unit/build；Rust/Go及完整真模型客户端suite没有执行。如果首期只发布Python/TS，Rust/Go应明确从产品支持矩阵排除，而非“测试通过”。UI还需浏览器执行租户登录、创建Bank、写入、召回、任务查询；build通过不证明鉴权正确。

## 4. 标准质量评测与AMB

依据：`hindsight-system-evals/README.md:275`、`.github/workflows/perf-test.yml:336`（system-evals）、`:146`附近（AMB）。

```sh
# 注入 HINDSIGHT_EVAL_LLM_PROVIDER / MODEL / API_KEY（或服务账号）
# 独立注入 HINDSIGHT_EVAL_JUDGE_PROVIDER / MODEL / API_KEY
: "${HINDSIGHT_EVAL_LLM_PROVIDER:?provider required}"
: "${HINDSIGHT_EVAL_LLM_MODEL:?model required}"
: "${HINDSIGHT_EVAL_JUDGE_MODEL:?independent judge required}"
(cd hindsight-system-evals && uv sync --frozen)
(cd hindsight-system-evals && PYTEST_ADDOPTS='' uv run pytest tests evals --full --output system-evals-results.json)
# 评估一个已部署的候选endpoint，另注入HINDSIGHT_EVAL_API_KEY
(cd hindsight-system-evals && PYTEST_ADDOPTS='' uv run pytest evals --api-url "$HINDSIGHT_API_URL" --full --output deployed-evals.json)
# AMB dataset/judge/scoring由独立AMB仓库提供；需要GEMINI_API_KEY、网络与成本额度
(cd hindsight-system-evals && uv run run-amb --dataset locomo --split locomo10)
(cd hindsight-system-evals && uv run run-amb --dataset longmemeval --split s)
```

每次用新评测PG实例，避免历史Bank后台任务被新模型key继续处理产生额外费用；上游README明确记录过该问题。固定corpus/model/judge/config，报告多次运行分布及成本，不把一次通过当准确率。本轮这些质量入口**未执行**，没有AMB新评分或华为MaaS准确率结论。

## 5. 升级、兼容与生成物

依据：`.github/workflows/test.yml:5366`（upgrade）、`:5506`（generated）、check-openapi-compatibility job；`hindsight-dev/upgrade_tests/conftest.py`。

```sh
# 需要完整git checkout及历史tags；本轮git archive副本没有这些前置
# 在隔离checkout中取已审阅的历史tags，再安装旧/新版本和批准的模型凭据
(cd hindsight-dev && uv sync --frozen --extra test --index-strategy unsafe-best-match)
(cd hindsight-dev && uv run pytest upgrade_tests/ -v --tb=short --junitxml=upgrade.xml)
(cd hindsight-dev && uv run check-openapi-compatibility /tmp/base-openapi.json ../hindsight-docs/static/openapi.json)
(cd hindsight-dev && uv run client-coverage-check)
(cd hindsight-dev && uv run cli-coverage-check)

# 以下会写生成文件，必须在可丢弃checkout执行并用git diff做门禁
./scripts/generate-openapi.sh
./scripts/generate-bank-template-schema.sh
./scripts/generate-clients.sh
./scripts/generate-docs-skill.sh
./scripts/hooks/lint.sh
git diff --exit-code
```

还需单独运行生产等价RDS备份恢复、PITR/主备切换、OBS读写/删除、API与Worker故障测试、容量/成本回归。上游升级suite通过不代表华为云运维合同已验收。这些入口未在本轮运行，必须在S7保留明确待验收状态。

实际分阶段依赖、范围和失败策略见 `tests-gate-manifest.json`。最小两job示例不应作为上线通过凭据。
