# Retain / Recall：真实接口 curl 验证

适用于基于官方Hindsight v1.0.0的ContextDB实例。接口和字段已与本机运行服务的OpenAPI核对；Retain/Recall均使用原生接口，不走管理接口。以下命令由使用者执行，会真实写入所选工作空间并调用已配置的MaaS模型，不是模型桩测试。

## 1. 准备参数

需要curl、jq及已存在的工作空间。当前本机可用：API `http://127.0.0.1:8888`，工作空间`jiamu`、`majing`；其他机器访问时将API_URL改为节点地址，例如`http://100.125.30.22:8888`。URL中的bank_id就是工作空间名称。

在当前机器，直接载入本次部署生成的私密配置，已包含可用的Admin Key和两个工作空间名称：

```bash
. /Users/zhuqingping/Work/Database/Context/test/hindsight_test/contextdb-local/20261020_150331/retain-recall-env.sh
```

该配置位于代码仓之外，权限0600，不复制进资料仓。Admin Key可访问两个空间。若使用UI创建的业务Key，将API_KEY换成其明文：写入需要目标空间读写权限，跨空间案例需要同时可访问两个空间。

其他环境按下面设置，当前机器已执行上面的载入命令时可跳过此段：

```bash
export API_URL='http://127.0.0.1:8888'
export BANK_ID='jiamu'
export OTHER_BANK_ID='majing'
export API_KEY='替换为Admin Key或有相应权限的业务Key'
export CASE_TAG="manual_$(date +%Y%m%d_%H%M%S)_$$"
export CASE_DIR="$(mktemp -d /tmp/contextdb-memory-case.XXXXXX)"
chmod 700 "$CASE_DIR"
export DOC_CN="${CASE_TAG}_cn"
export DOC_EN="${CASE_TAG}_en"
export DOC_ASYNC="${CASE_TAG}_async"
export DOC_OTHER="${CASE_TAG}_other"
```

`CASE_TAG`区分每轮测试；`document_id`是本轮源文档标识，不是workspace_id。工作空间必须已创建。按顺序执行，任一步结果不符合预期先停下检查；不要因为Retain超时或断连就重复POST，服务端可能仍在处理。

```bash
curl -fsS --max-time 10 "$API_URL/health/ready" | jq .
printf '工作空间=%s；本轮标签=%s；响应目录=%s\n' "$BANK_ID" "$CASE_TAG" "$CASE_DIR"
```

预期健康接口HTTP200、`status=healthy`、`database=connected`。下文使用`--fail-with-body`，接口错误时保留错误响应；请求和响应文件都保存到私有CASE_DIR。

## 2. 同步 Retain：写入中文事实

**请求：** `POST /v1/default/banks/{bank_id}/memories`。`async=false`表示等待本次提取和写入完成。`content`为源文本，`context`帮助理解语境，`tags`供后续筛选，`metadata`是调用者附加的字符串属性。

```bash
jq -n --arg tag "$CASE_TAG" --arg doc "$DOC_CN" '{
  items: [{
    content: "火星项目的负责人是嘉沐。火星项目使用PostgreSQL 18数据库。项目代码评审安排在每周三下午三点。",
    context: "人工验证：火星项目资料",
    document_id: $doc,
    tags: [$tag, "project_jiamu"],
    metadata: {source: "manual_curl", language: "zh"}
  }],
  async: false
}' > "$CASE_DIR/retain-cn.request.json"

curl --fail-with-body -sS --max-time 300 -X POST \
  "$API_URL/v1/default/banks/$BANK_ID/memories" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/retain-cn.request.json" \
  -o "$CASE_DIR/retain-cn.response.json"
jq . "$CASE_DIR/retain-cn.response.json"
jq -e '.success == true and .async == false and .items_count == 1' \
  "$CASE_DIR/retain-cn.response.json"
```

**预期：** HTTP200，核心字段示意如下；`items_count=1`表示输入1项，不表示只生成1条记忆。

```json
{"success":true,"bank_id":"jiamu","items_count":1,"async":false,"operation_id":null}
```

服务端可能同时返回`usage`等字段；模型可能拆成多条事实，也可能改写语言，不要求生成内容逐字一致。

## 3. Recall：中文提问

**请求：** `POST /v1/default/banks/{bank_id}/memories/recall`。`query`为问题；`budget=mid`控制检索预算；`max_tokens`限制返回记忆的文本预算，不是返回条数；`all_strict`要求标签匹配且排除无标签数据。限定`world/experience`便于先观察原始提取事实，不依赖后台合成知识完成。

```bash
jq -n --arg tag "$CASE_TAG" '{
  query: "谁负责火星项目？项目用的是什么数据库？",
  types: ["world", "experience"],
  budget: "mid",
  max_tokens: 1500,
  tags: [$tag],
  tags_match: "all_strict"
}' > "$CASE_DIR/recall-cn.request.json"

curl --fail-with-body -sS --max-time 120 -X POST \
  "$API_URL/v1/default/banks/$BANK_ID/memories/recall" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/recall-cn.request.json" \
  -o "$CASE_DIR/recall-cn.response.json"
jq '{count: (.results | length), results: [.results[] | {id,text,type,document_id,tags}]}' \
  "$CASE_DIR/recall-cn.response.json"
```

**预期：** HTTP200、`results`包含与李明负责、PostgreSQL 18相关的记忆。检查`document_id`为DOC_CN、标签含CASE_TAG。Recall返回检索到的记忆，不保证直接生成一段问答；生成回答另用Reflect。

当前部署是native英文全文检索。中文可通过bge-m3向量及其他检索路径召回，本例成功不能证明已支持中文分词全文；事实条数、顺序及相关分数不是固定值。

## 4. 英文写入与英文召回

```bash
jq -n --arg tag "$CASE_TAG" --arg doc "$DOC_EN" '{
  items: [{
    content: "Emily is the database engineer on the Mars project. Emily prefers SQL examples and uses Python for automation.",
    context: "Manual validation: team preferences",
    document_id: $doc,
    tags: [$tag, "team_preferences"]
  }],
  async: false
}' > "$CASE_DIR/retain-en.request.json"

curl --fail-with-body -sS --max-time 300 -X POST \
  "$API_URL/v1/default/banks/$BANK_ID/memories" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/retain-en.request.json" \
  -o "$CASE_DIR/retain-en.response.json"
jq -e '.success == true and .async == false' "$CASE_DIR/retain-en.response.json"

jq -n --arg tag "$CASE_TAG" '{
  query: "What examples does Emily prefer, and what language does she use for automation?",
  types: ["world", "experience"],
  budget: "mid",
  max_tokens: 1500,
  tags: [$tag, "team_preferences"],
  tags_match: "all_strict"
}' > "$CASE_DIR/recall-en.request.json"

curl --fail-with-body -sS --max-time 120 -X POST \
  "$API_URL/v1/default/banks/$BANK_ID/memories/recall" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/recall-en.request.json" \
  -o "$CASE_DIR/recall-en.response.json"
jq '[.results[] | {text,document_id,tags}]' "$CASE_DIR/recall-en.response.json"
```

**预期：** 两次均HTTP200。召回SQL示例偏好、Python自动化等事实；结果源文档应为DOC_EN，不能因同在一个空间就忽略标签筛选。

## 5. 不存在的标签：验证筛选

```bash
jq --arg tag "${CASE_TAG}_not_written" '.tags=[$tag]' \
  "$CASE_DIR/recall-cn.request.json" > "$CASE_DIR/recall-missing-tag.request.json"

curl --fail-with-body -sS --max-time 120 -X POST \
  "$API_URL/v1/default/banks/$BANK_ID/memories/recall" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/recall-missing-tag.request.json" \
  -o "$CASE_DIR/recall-missing-tag.response.json"
jq -e '.results | length == 0' "$CASE_DIR/recall-missing-tag.response.json"
```

**预期：** HTTP200，`results=[]`。这是严格标签筛选的确定性检查；不要用“不相关问题必须返回空”作为同样的断言，语义检索可能仍返回最相近记忆。

## 6. 异步 Retain：提交、查询进度、再召回

```bash
jq -n --arg tag "$CASE_TAG" --arg doc "$DOC_ASYNC" '{
  items: [{
    content: "火星项目的技术文档由骏泽维护。每次发布前，骏泽会检查SQL示例是否可以执行。",
    context: "人工验证：文档维护职责",
    document_id: $doc,
    tags: [$tag, "async_case"]
  }],
  async: true
}' > "$CASE_DIR/retain-async.request.json"

curl --fail-with-body -sS --max-time 60 -X POST \
  "$API_URL/v1/default/banks/$BANK_ID/memories" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/retain-async.request.json" \
  -o "$CASE_DIR/retain-async.response.json"
jq . "$CASE_DIR/retain-async.response.json"
export OPERATION_ID="$(jq -er '.operation_id | select(type=="string" and length>0)' \
  "$CASE_DIR/retain-async.response.json")"
```

**预期：** HTTP200、`success=true`、`async=true`及非空`operation_id`。这只表示受理，不能立即当成写入完成。

```bash
for i in $(seq 1 120); do
  curl --fail-with-body -sS --max-time 20 \
    "$API_URL/v1/default/banks/$BANK_ID/operations/$OPERATION_ID" \
    -H "Authorization: Bearer $API_KEY" \
    -o "$CASE_DIR/operation-status.response.json" || break
  STATUS="$(jq -r '.status' "$CASE_DIR/operation-status.response.json")"
  printf 'operation=%s status=%s\n' "$OPERATION_ID" "$STATUS"
  case "$STATUS" in
    completed) break ;;
    failed|cancelled) jq . "$CASE_DIR/operation-status.response.json"; break ;;
  esac
  sleep 3
done
jq -e '.status == "completed"' "$CASE_DIR/operation-status.response.json"
```

只有最后检查成功才继续；否则先保留响应排查，不重发Retain。之后的合成/维护任务可能仍在后台执行。

```bash
jq -n --arg tag "$CASE_TAG" '{
  query: "谁维护火星项目的技术文档？发布前会做什么？",
  types: ["world", "experience"],
  budget: "mid",
  max_tokens: 1500,
  tags: [$tag, "async_case"],
  tags_match: "all_strict"
}' > "$CASE_DIR/recall-async.request.json"

curl --fail-with-body -sS --max-time 120 -X POST \
  "$API_URL/v1/default/banks/$BANK_ID/memories/recall" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/recall-async.request.json" \
  -o "$CASE_DIR/recall-async.response.json"
jq '[.results[] | {text,document_id,tags}]' "$CASE_DIR/recall-async.response.json"
```

**预期：** 召回陈晨维护文档、检查SQL示例等事实，源文档为DOC_ASYNC。

## 7. 两个工作空间的数据隔离

先用同一Key、同一个Recall请求查询OTHER_BANK_ID；该空间还没有本轮标签的数据：

```bash
curl --fail-with-body -sS --max-time 120 -X POST \
  "$API_URL/v1/default/banks/$OTHER_BANK_ID/memories/recall" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/recall-cn.request.json" \
  -o "$CASE_DIR/other-before.response.json"
jq -e '.results | length == 0' "$CASE_DIR/other-before.response.json"
```

预期HTTP200且为空；403表示Key没有该空间权限，应先核对授权，不能当作已验证数据隔离。随后在第二空间使用相同CASE_TAG写入不同事实：

```bash
jq -n --arg tag "$CASE_TAG" --arg doc "$DOC_OTHER" '{
  items: [{
    content: "木星项目的负责人是马静。木星项目使用MySQL数据库。",
    context: "人工验证：第二工作空间的项目资料",
    document_id: $doc,
    tags: [$tag]
  }],
  async: false
}' > "$CASE_DIR/retain-other.request.json"

curl --fail-with-body -sS --max-time 300 -X POST \
  "$API_URL/v1/default/banks/$OTHER_BANK_ID/memories" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/retain-other.request.json" \
  -o "$CASE_DIR/retain-other.response.json"
jq -e '.success == true' "$CASE_DIR/retain-other.response.json"

jq '.query="木星项目由谁负责，用什么数据库？"' \
  "$CASE_DIR/recall-cn.request.json" > "$CASE_DIR/recall-other.request.json"
curl --fail-with-body -sS --max-time 120 -X POST \
  "$API_URL/v1/default/banks/$OTHER_BANK_ID/memories/recall" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/recall-other.request.json" \
  -o "$CASE_DIR/recall-other.response.json"
jq '[.results[] | {text,document_id,tags}]' "$CASE_DIR/recall-other.response.json"
jq -e --arg doc "$DOC_OTHER" \
  '(.results | length > 0) and all(.results[]; .document_id == $doc)' \
  "$CASE_DIR/recall-other.response.json"
```

**预期：** 第二空间召回马静、MySQL等事实，结果只来自DOC_OTHER。再执行第3节，第一空间仍只返回第一空间的本轮数据。这一项验证数据隔离，不等于业务Key越权访问测试。

## 8. 可选：只读 Key 的 Recall / Retain 权限

在UI创建仅有BANK_ID只读权限的业务Key，将下面的READ_ONLY_KEY替换为首次展示的明文。不复用Admin Key代替此项。

```bash
export READ_ONLY_KEY='替换为仅有只读权限的业务Key'
curl --fail-with-body -sS --max-time 120 -X POST \
  "$API_URL/v1/default/banks/$BANK_ID/memories/recall" \
  -H "Authorization: Bearer $READ_ONLY_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/recall-cn.request.json" | jq '.results'

curl -sS --max-time 30 -X POST \
  "$API_URL/v1/default/banks/$BANK_ID/memories" \
  -H "Authorization: Bearer $READ_ONLY_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @"$CASE_DIR/retain-cn.request.json" \
  -o "$CASE_DIR/readonly-retain.response.json" -w 'HTTP %{http_code}\n'
jq . "$CASE_DIR/readonly-retain.response.json"
```

**预期：** Recall为200，Retain为403且没有新增写入。对没有授权的其他空间访问也应403；换Key只需改变Authorization，不改变原生URL和请求参数。

## 9. 查看与排查

UI进入相应工作空间，在记忆/文档页面查看本轮源文档及提取事实。curl输出的CASE_DIR保留全部请求、响应和任务ID，方便比对。本手册不自动删除工作空间或测试数据。

| 现象 | 先检查 |
| --- | --- |
| 401 | Key是否完整、是否吊销，所属用户是否停用/删除 |
| 403 | 空间是否active、Key是否有目标空间和相应读写权限 |
| Retain返回200但success=false | 检查完整响应和服务日志，不能只看HTTP状态 |
| 异步一直pending/processing | 查询该operation及Worker状态，不重复提交 |
| 同步Retain超时 | 结果未知；先查目标文档/原生operations及日志 |
| Recall结果为空 | 是否完成Retain、空间/CASE_TAG是否一致、严格标签、类型及模型是否正常 |
| 400/422 | 查看响应中的字段校验信息，不把所有原生校验错误固定理解成400 |

这些是执行用例与预期，不冒充已完成的真实写入结果；生成时仅核对了本机健康、空间目录和接口定义。用户执行后的返回内容才是本轮业务验证证据。
