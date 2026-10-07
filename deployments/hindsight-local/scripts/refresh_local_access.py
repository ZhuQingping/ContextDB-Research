#!/usr/bin/env python3
"""Copy only the current local GPT access credential. Never change the source login."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
source = Path.home() / ".codex/auth.json"
data = json.loads(source.read_text())
if not data.get("tokens", {}).get("access_token"):
    raise SystemExit("The local login does not contain an OAuth access token")
data = {"auth_mode": data.get("auth_mode"), "tokens": {
    key: data["tokens"][key] for key in ["access_token", "account_id"] if key in data["tokens"]
}}
target = root / ".secrets/codex/auth.json"
target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
target.write_text(json.dumps(data))
target.chmod(0o600)
print("Private access-only copy refreshed. Restart this deployment's API to reload it.")
