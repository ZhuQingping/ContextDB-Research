#!/usr/bin/env python3
"""Real HTTP/LLM smoke stories. Synthetic data only; not an accuracy benchmark."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[1]
BANK = "huawei-contextdb-demo"
KB = "huawei-contextdb-knowledge"
EMPTY = "huawei-contextdb-isolation"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="Read existing data without new writes/model generation")
    parser.add_argument("--output", default="acceptance.json")
    args = parser.parse_args()
    records = []
    client = httpx.Client(base_url="http://127.0.0.1:8888", timeout=240, trust_env=False)

    def call(name, method, path, body=None, expected=(200, 201, 202)):
        started = time.monotonic()
        response = client.request(method, path, json=body) if body is not None else client.request(method, path)
        try:
            result = response.json()
        except ValueError:
            result = response.text[:2000]
        records.append({"name": name, "method": method, "path": path,
                        "status": response.status_code, "elapsed_s": round(time.monotonic() - started, 3),
                        "response": result})
        save()
        if response.status_code not in expected:
            raise AssertionError(f"{name}: unexpected HTTP {response.status_code}")
        return result

    def save():
        (ROOT / "evidence" / args.output).write_text(json.dumps({
            "time_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Local synthetic functional smoke; no production SLO or benchmark claim",
            "records": records}, ensure_ascii=False, indent=2) + "\n")

    def bank_path(bank, suffix=""):
        return f"/v1/default/banks/{bank}{suffix}"

    def wait_operation(bank, operation_id, timeout=240):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = call("operation-status", "GET", bank_path(bank, f"/operations/{operation_id}"))
            status = value.get("status")
            if status == "completed":
                return value
            if status in ["failed", "cancelled"]:
                raise AssertionError(f"Operation {operation_id}: {status}")
            time.sleep(3)
        raise TimeoutError(f"Operation {operation_id}: did not finish within {timeout}s")

    call("health", "GET", "/health")
    call("version", "GET", "/version")
    if not args.check_only:
        for bank in [BANK, KB, EMPTY]:
            call("create-bank", "PUT", bank_path(bank), {
                "retain_extraction_mode": "chunks" if bank == KB else "concise",
                "enable_observations": bank == BANK,
                "reflect_mission": "这是合成的数据库运维验收样例。仅根据记忆和原文回答，区分历史记录与当前结论，不编造生产操作。"})
        operation_id = str(uuid.uuid4())
        content = (
            "【合成验收数据，不是真实生产记录】2026年10月3日，海星项目数据库小组复盘工单 INC-2048。"
            "现象：发布后数据库连接数达到480，应用连接池上限为500。"
            "排查发现应用未及时归还空闲连接；团队将应用连接池上限调整为120，并修复连接归还逻辑。"
            "复测中连接数稳定在85。负责人为林岚。后续排查先看连接池指标与pg_stat_activity，"
            "不要仅凭连接数高就判定CPU不足或直接扩容。林岚偏好先给结论再给证据的中文报告。"
        )
        retain_body = {"async": True, "operation_id": operation_id, "items": [{
            "content": content, "document_id": "incident-2048-v1", "timestamp": "2026-10-03T10:00:00+08:00",
            "tags": ["project:starfish", "source:synthetic"], "metadata": {"source": "acceptance-fixture", "revision": "1"}}]}
        first = call("retain-async", "POST", bank_path(BANK, "/memories"), retain_body)
        duplicate = call("retain-idempotent-retry", "POST", bank_path(BANK, "/memories"), retain_body)
        assert first["operation_id"] == duplicate["operation_id"] == operation_id
        wait_operation(BANK, operation_id)
        call("knowledge-raw-chunks", "POST", bank_path(KB, "/memories"), {"items": [{
            "content": "【合成规范 RUNBOOK-17，版本1，已审核】处理连接耗尽时，先检查应用连接池配置和连接归还。记录pg_stat_activity中的state、wait_event及事务开始时间。未经审批不得终止生产连接。此文不规定统一的max_connections推荐值。",
            "document_id": "runbook-17-v1", "tags": ["status:approved", "source:synthetic"],
            "metadata": {"revision": "1", "approved_by": "demo-reviewer"}}]})
    result = call("recall-chinese", "POST", bank_path(BANK, "/memories/recall"), {
        "query": "海星项目连接耗尽的原因、修复措施和负责人是什么？", "budget": "low", "max_tokens": 1200,
        "include": {"chunks": {"max_tokens": 1500}}, "trace": True})
    assert result.get("results"), "Recall returned no memories"
    other = call("empty-bank-isolation", "POST", bank_path(EMPTY, "/memories/recall"), {
        "query": "海星项目 INC-2048 林岚 连接池", "budget": "low", "max_tokens": 1200})
    assert not other.get("results"), "Unexpected data in empty bank"
    call("source-document", "GET", bank_path(BANK, "/documents/incident-2048-v1"))
    call("knowledge-recall", "POST", bank_path(KB, "/memories/recall"), {
        "query": "是否可以直接终止生产连接？", "max_tokens": 1000, "budget": "low"})
    if not args.check_only:
        reflected = call("reflect-with-evidence", "POST", bank_path(BANK, "/reflect"), {
            "query": "根据海星项目INC-2048的复盘，用中文简述原因、处理措施、复测连接数和负责人。没有的事实不要补充。",
            "budget": "low", "max_tokens": 650, "include": {"facts": {}, "tool_calls": {"output": False}}})
        assert reflected.get("text"), "Reflect generated empty text"
        # The text is kept for human assessment; presence is not scored as factual accuracy.
        call("invalid-request", "POST", bank_path(BANK, "/memories/recall"), {}, expected=(422,))
        folder = call("knowledge-folder", "POST", bank_path(BANK, "/knowledge-base/folders"), {"name": "验收复盘"})
        call("knowledge-page-create", "POST", bank_path(BANK, "/knowledge-base/pages"), {
            "name": "连接池排查经验", "source_query": "海星项目INC-2048给数据库连接池排查带来哪些经验？保留证据和数字。",
            "parent_id": folder.get("id"), "max_tokens": 1000})
    call("knowledge-tree", "GET", bank_path(BANK, "/knowledge-base/tree"))
    call("bank-stats", "GET", bank_path(BANK, "/stats"))
    client.close()
    print(f"PASS: {len(records)} HTTP records; evidence/{args.output}")


if __name__ == "__main__":
    main()
