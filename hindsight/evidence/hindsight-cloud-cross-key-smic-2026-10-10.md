# Hindsight Cloud 同 Bank 跨 API Key 记忆可见性验证

- 验证时间：2026-10-10 10:04 UTC（本地时区 Asia/Shanghai）
- 服务：`https://api.hindsight.vectorize.io`
- Bank：`SMIC`
- 验证范围：2 把 API Key；1 次 Retain（key1）；2 次 Recall（分别 key1、key2）
- 凭据处理：证据中只用 `key1` / `key2` 标识，不保存 API Key 明文。
- 数据处理：仅新增一条合成测试记忆，没有修改/删除其他数据。该测试记忆目前仍保留在 `SMIC` Bank 中。

## 结论

**确认发生跨 Key 记忆可见：key1 写入的测试记忆，key1 和 key2 都能通过 Recall 读到。**因此，本次测试的两把 Key 对同一个 `SMIC` Bank 并未表现出用户级记忆隔离。

这是一次定向黑盒验证，证明 `key1 → retain → key1/key2 recall` 这条路径可见。没有测试 key2 写入后 key1 读取，也没有由此推断 Hindsight Cloud 所有 Organization、所有 Key 配置一概如此。

## 前置：确认两把 Key 都能访问同一个 Bank

先分别用两把 Key 对 `GET /v1/default/banks` 做只读查询，均返回 HTTP 200。两份列表中的 `SMIC` 项 `bank_id`、`name` 和 `created_at` 完全相同：

```json
{
  "key1": {
    "http_status": 200,
    "bank_id": "SMIC",
    "name": "SMIC",
    "created_at": "2026-10-10T09:49:22.669321+00:00"
  },
  "key2": {
    "http_status": 200,
    "bank_id": "SMIC",
    "name": "SMIC",
    "created_at": "2026-10-10T09:49:22.669321+00:00"
  }
}
```

这避免了把“Key 不同、实际访问不同 Bank”误判为“同 Bank 内成员隔离”。

## 请求记录

### 1. Retain（key1）

- 时间：`2026-10-10T10:04:40Z`
- 方法/路径：`POST /v1/default/banks/SMIC/memories`
- Authorization：`Bearer <key1，脱敏>`
- HTTP：`200`
- 请求体：

```json
{
  "items": [
    {
      "content": "Cross-key verification marker HSCROSSKEY-20261010: the test phrase is violet otter 731."
    }
  ]
}
```

- 完整响应：

```json
{
  "success": true,
  "bank_id": "SMIC",
  "items_count": 1,
  "async": false,
  "operation_id": null,
  "operation_ids": null,
  "usage": {
    "input_tokens": 2034,
    "output_tokens": 208,
    "total_tokens": 2242,
    "cached_tokens": 0,
    "thoughts_tokens": 0
  }
}
```

### 2. Recall（key1）

- 时间：`2026-10-10T10:04:49Z`
- 方法/路径：`POST /v1/default/banks/SMIC/memories/recall`
- Authorization：`Bearer <key1，脱敏>`
- HTTP：`200`
- 请求体：

```json
{
  "query": "What exact test phrase is associated with HSCROSSKEY-20261010?",
  "budget": "low",
  "max_tokens": 128
}
```

- 完整响应：

```json
{
  "results": [
    {
      "id": "d197cda9-a82b-449d-ac70-c938bd221cfc",
      "text": "The cross-key verification marker is HSCROSSKEY-20261010 and the test phrase is 'violet otter 731'.",
      "type": "observation",
      "entities": ["violet otter 731", "HSCROSSKEY-20261010"],
      "context": "",
      "occurred_start": "2026-10-10T00:00:00+00:00",
      "occurred_end": "2026-10-10T00:00:00+00:00",
      "mentioned_at": "2026-10-10T10:04:38.776000+00:00",
      "document_id": null,
      "metadata": {},
      "chunk_id": null,
      "tags": [],
      "source_fact_ids": null,
      "scores": {
        "final": 1.0997698546613395,
        "reranker": null,
        "semantic": 0.840172290802002,
        "keyword": 1.150728464126587
      },
      "attachments": null
    },
    {
      "id": "6141abf2-d9de-4be0-9241-fdbd71e421ea",
      "text": "The cross-key verification marker is HSCROSSKEY-20261010 and the test phrase is 'violet otter 731'. | When: 2026-10-10 | Verification process",
      "type": "world",
      "entities": ["violet otter 731", "HSCROSSKEY-20261010"],
      "context": "",
      "occurred_start": "2026-10-10T00:00:00+00:00",
      "occurred_end": "2026-10-10T00:00:00+00:00",
      "mentioned_at": "2026-10-10T10:04:38.776000+00:00",
      "document_id": "b1a77821-78e3-4709-916a-1cbb0c82aa0e",
      "metadata": {},
      "chunk_id": "SMIC_b1a77821-78e3-4709-916a-1cbb0c82aa0e_0",
      "tags": [],
      "source_fact_ids": null,
      "scores": {
        "final": 0.10997698546613392,
        "reranker": null,
        "semantic": 0.8268750309944153,
        "keyword": 1.366490125656128
      },
      "attachments": null
    }
  ],
  "trace": null,
  "entities": {
    "violet otter 731": {
      "entity_id": "16d3d9ce-6bbe-5b53-8829-ea09571c1269",
      "canonical_name": "violet otter 731",
      "observations": []
    },
    "HSCROSSKEY-20261010": {
      "entity_id": "72ad3813-fab6-5cf0-ad91-d9b19a0aea1d",
      "canonical_name": "HSCROSSKEY-20261010",
      "observations": []
    }
  },
  "chunks": null,
  "source_facts": null,
  "source_facts_truncated": null
}
```

### 3. Recall（key2）

- 时间：`2026-10-10T10:04:57Z`
- 方法/路径：`POST /v1/default/banks/SMIC/memories/recall`
- Authorization：`Bearer <key2，脱敏>`
- HTTP：`200`
- 请求体：与 key1 Recall 完全相同，`budget=low`、`max_tokens=128`。
- 完整响应：

```json
{
  "results": [
    {
      "id": "d197cda9-a82b-449d-ac70-c938bd221cfc",
      "text": "The cross-key verification marker is HSCROSSKEY-20261010 and the test phrase is 'violet otter 731'.",
      "type": "observation",
      "entities": ["violet otter 731", "HSCROSSKEY-20261010"],
      "context": "",
      "occurred_start": "2026-10-10T00:00:00+00:00",
      "occurred_end": "2026-10-10T00:00:00+00:00",
      "mentioned_at": "2026-10-10T10:04:38.776000+00:00",
      "document_id": null,
      "metadata": {},
      "chunk_id": null,
      "tags": [],
      "source_fact_ids": null,
      "scores": {
        "final": 1.0997698064497716,
        "reranker": null,
        "semantic": 0.840172290802002,
        "keyword": 1.150728464126587
      },
      "attachments": null
    },
    {
      "id": "6141abf2-d9de-4be0-9241-fdbd71e421ea",
      "text": "The cross-key verification marker is HSCROSSKEY-20261010 and the test phrase is 'violet otter 731'. | When: 2026-10-10 | Verification process",
      "type": "world",
      "entities": ["violet otter 731", "HSCROSSKEY-20261010"],
      "context": "",
      "occurred_start": "2026-10-10T00:00:00+00:00",
      "occurred_end": "2026-10-10T00:00:00+00:00",
      "mentioned_at": "2026-10-10T10:04:38.776000+00:00",
      "document_id": "b1a77821-78e3-4709-916a-1cbb0c82aa0e",
      "metadata": {},
      "chunk_id": "SMIC_b1a77821-78e3-4709-916a-1cbb0c82aa0e_0",
      "tags": [],
      "source_fact_ids": null,
      "scores": {
        "final": 0.10997698046613392,
        "reranker": null,
        "semantic": 0.8268750309944153,
        "keyword": 1.366490125656128
      },
      "attachments": null
    }
  ],
  "trace": null,
  "entities": {
    "violet otter 731": {
      "entity_id": "16d3d9ce-6bbe-5b53-8829-ea09571c1269",
      "canonical_name": "violet otter 731",
      "observations": []
    },
    "HSCROSSKEY-20261010": {
      "entity_id": "72ad3813-fab6-5cf0-ad91-d9b19a0aea1d",
      "canonical_name": "HSCROSSKEY-20261010",
      "observations": []
    }
  },
  "chunks": null,
  "source_facts": null,
  "source_facts_truncated": null
}
```

## Interpretation and limits

- Both keys were accepted for the same Bank; the same memory-unit IDs and text appeared in both recall results. This is direct evidence of cross-key visibility, not an inference from schema fields.
- The result establishes sharing in this direction: key1 wrote, key1 and key2 read. It does not test the reverse write direction.
- This test does not identify whether Cloud's internal implementation is one schema, multiple schemas, or a private authorization/filtering extension. It only establishes observed API behavior for these two keys and this Bank.
- The verification performed exactly one Retain and two Recall calls. Recall requests used `budget=low`, `max_tokens=128`. Retain reported 2,242 total tokens.
- No API Key value is included in this evidence.
