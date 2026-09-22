# tdai-memory-core 重部署命令（含 BGE-m3 embedding 配置）
# 前提：新镜像 agentmemory/memory-core:latest 已构建（含 TDAI_EMBEDDING_* env 支持）
#
# 变更说明：
#   1. 代码新增 TDAI_EMBEDDING_* 环境变量（commit 2958722），与 TDAI_LLM_* 同模式
#   2. TDAI_EMBEDDING_SEND_DIMENSIONS=false —— 华为 MaaS bge-m3 拒绝 dimensions
#      参数（ModelArts.81001 HTTP 400），必须不发
#   3. 无需挂载 yaml：embedding 全部走 env，部署回归纯 docker run 风格

docker rm -f tdai-memory-core

docker run -d --name tdai-memory-core \
  --network tdai-memory-stack --network-alias memory-core -p 8420:8420 \
  -v agent-memory-night-memory-core-data:/data/tdai-memory \
  -e TDAI_SKILL_ENABLED=1 -e TDAI_GATEWAY_HOST=0.0.0.0 -e TDAI_GATEWAY_API_KEY= \
  -e TDAI_DATA_DIR=/data/tdai-memory -e STORE_MODE=sqlite \
  -e TDAI_GATEWAY_PORT=8420 -e NODE_ENV=production \
  -e "NODE_OPTIONS=--max-old-space-size=1536" \
  -e TDAI_LLM_BASE_URL="https://st8tp3ajl0df3n8b8l8qu.apigateway-cn-beijing.volceapi.com/v1" \
  -e TDAI_LLM_API_KEY="62899175-9c17-4ff8-b60e-6290132a2390" \
  -e TDAI_LLM_MODEL="glm-5.3-flash" \
  -e TDAI_LLM_MAX_TOKENS=32000 -e TDAI_LLM_TIMEOUT_MS=300000 \
  -e TDAI_EMBEDDING_PROVIDER=openai \
  -e TDAI_EMBEDDING_BASE_URL="https://api.modelarts-maas.com/v1" \
  -e TDAI_EMBEDDING_API_KEY="Ud260vor3oiXWn7OeEbHdJxqat60lfgheziuPlZ60R2R9XqYmLLAIo3jSa0AxXZO2f0uKL5ycj3QNqyxklw_XQ" \
  -e TDAI_EMBEDDING_MODEL="bge-m3" \
  -e TDAI_EMBEDDING_DIMENSIONS=1024 \
  -e TDAI_EMBEDDING_SEND_DIMENSIONS=false \
  -e TDAI_EMBEDDING_TIMEOUT_MS=15000 \
  agentmemory/memory-core:latest
