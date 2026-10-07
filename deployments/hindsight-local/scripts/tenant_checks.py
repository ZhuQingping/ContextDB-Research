#!/usr/bin/env python3
"""Probe the temporary Cell B with two real schema tenants, without LLM ingestion."""
import json
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
keys = json.loads((ROOT / ".secrets/cell-b-keys.json").read_text())
client = httpx.Client(base_url="http://127.0.0.1:8890", trust_env=False, timeout=120)
records = []
bank = "/v1/default/banks/shared-name"


def call(name, method, path, who=None, body=None, expected=200):
    headers = {"Authorization": f"Bearer {keys[who]}"} if who else {}
    response = client.request(method, path, headers=headers, json=body) if body is not None else client.request(method, path, headers=headers)
    data = response.json()
    records.append({"name": name, "method": method, "path": path, "actor": who or "anonymous",
                    "status": response.status_code, "response": data})
    (ROOT / "evidence/tenant-checks.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
    assert response.status_code == expected, (name, response.status_code)
    return data


call("unauthenticated-list-denied", "GET", "/v1/default/banks", expected=401)
for who, marker in [("team_a", "ALPHA_CANARY_4821"), ("team_b", "BETA_CANARY_7396")]:
    call("create-same-bank-name", "PUT", bank, who, {"retain_extraction_mode": "chunks", "enable_observations": False})
    call("retain-canary", "POST", bank + "/memories", who, {"items": [{
        "content": f"Synthetic tenant marker {marker}. This is private data for {who}.",
        "document_id": "same-document-id", "tags": ["scope:private"]}]})
a = call("tenant-a-list", "GET", bank + "/memories/list", "team_a")
b = call("tenant-b-list", "GET", bank + "/memories/list", "team_b")
assert "ALPHA_CANARY_4821" in json.dumps(a) and "BETA_CANARY_7396" not in json.dumps(a)
assert "BETA_CANARY_7396" in json.dumps(b) and "ALPHA_CANARY_4821" not in json.dumps(b)
aid = a["items"][0]["id"]
call("foreign-memory-id-denied", "GET", bank + f"/memories/{aid}", "team_b", expected=404)
recall = call("tenant-b-recall-cannot-find-alpha", "POST", bank + "/memories/recall", "team_b", {
    "query": "ALPHA_CANARY_4821 private data", "max_tokens": 500, "budget": "low"})
assert "ALPHA_CANARY_4821" not in json.dumps(recall)
call("delete-a-document", "DELETE", bank + "/documents/same-document-id", "team_a")
after = call("a-document-removed", "GET", bank + "/memories/list", "team_a")
assert not after["items"]
b_after = call("b-document-survives-a-delete", "GET", bank + "/documents/same-document-id", "team_b")
assert "BETA_CANARY_7396" in json.dumps(b_after)
call("spoof-bank-config-not-auth", "GET", "/v1/default/banks?tenant_id=team_b", "team_a")
print(f"PASS: {len(records)} tenant HTTP checks. Not a complete cloud ACL audit.")
