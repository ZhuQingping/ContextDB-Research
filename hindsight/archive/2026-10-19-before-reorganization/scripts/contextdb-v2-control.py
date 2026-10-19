#!/usr/bin/env python3
"""Executable integration examples, not a node Agent or a production scheduler.

Stdlib HTTP is deliberate: this is an operator CLI in the research repository,
separate from Hindsight's async runtime. Secrets remain in private state files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        tmp = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def public(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: public(item) for key, item in value.items() if key != "secret"}
    if isinstance(value, list):
        return [public(item) for item in value]
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        # A redirected management request must not forward the control credential.
        return None


class Client:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.root = Path(args.state_dir)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        parsed = urllib.parse.urlsplit(args.url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "--url must be an HTTP(S) API address without credentials/query"
            )
        self.base = args.url.rstrip("/")
        # Control calls use the selected node directly, never an ambient HTTP proxy.
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect()
        )

    def call(
        self, method: str, path: str, body: Any = None, request_id: str | None = None
    ) -> Any:
        credential = read(Path(self.args.credential_file))
        headers = {
            "X-ContextDB-Control-Key": credential["secret"],
            "X-ContextDB-Actor-Subject": self.args.actor,
        }
        if request_id:
            headers["Idempotency-Key"] = request_id
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + path, data=data, headers=headers, method=method
        )
        try:
            with self.opener.open(request, timeout=self.args.http_timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            try:
                detail = public(json.loads(error.read()))
            except (ValueError, UnicodeError):
                detail = "Non-JSON response; check the API/proxy address"
            raise ValueError(
                f"HTTP {error.code}: {json.dumps(detail, ensure_ascii=False)}"
            ) from None
        except (urllib.error.URLError, TimeoutError):
            raise ValueError(
                "HTTP request failed/timed out; execution outcome may be unknown. Keep the request ID."
            ) from None

    def bind(self, request_id: str, method: str, path: str, body: Any) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", request_id):
            raise ValueError("request ID: use 1-80 ASCII letters/digits/_/-")
        directory = self.root / "requests" / request_id
        envelope = {
            "url": self.base,
            "actor": self.args.actor,
            "method": method,
            "path": path,
            "body": body,
        }
        file = directory / "request.json"
        if file.exists():
            if read(file) != envelope:
                raise ValueError(
                    "Request ID already belongs to another URL/actor/method/path/body"
                )
        else:
            save(file, envelope)
        return directory

    def wait(self, operation_id: str) -> Any:
        deadline = time.monotonic() + self.args.wait_timeout
        while True:
            result = self.call(
                "GET", f"/ext/contextdb/v1/operations/{identifier(operation_id)}"
            )
            save(self.root / "operations" / f"{operation_id}.json", result)
            if result["state"] == "succeeded":
                return result
            if result["state"] == "failed":
                raise ValueError(
                    f"Operation failed: {result.get('error_code')}; operation_id={operation_id}"
                )
            if time.monotonic() >= deadline:
                raise ValueError(
                    f"Wait timed out; operation is NOT cancelled. Resume with operation-wait {operation_id}"
                )
            time.sleep(min(self.args.interval, max(0, deadline - time.monotonic())))


def identifier(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def write_env(path: Path, settings: dict[str, str]) -> None:
    with path.open("x") as stream:
        for key, value in settings.items():
            stream.write(f"export {key}={shlex.quote(value)}\n")


def configure(args: argparse.Namespace) -> None:
    import secrets

    root = Path(args.state_dir)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (root / "api.env").exists() or (root / "ui-password.json").exists():
        raise ValueError(
            "Deployment already configured; reuse its files. Do not regenerate pepper/password."
        )
    env = os.environ
    required = ["DB_URL", "INSTANCE_ID", "CLOUD_TENANT_ID", "MAAS_API_KEY"]
    if any(not env.get(key) for key in required):
        raise ValueError("Set DB_URL, INSTANCE_ID, CLOUD_TENANT_ID, MAAS_API_KEY first")
    credential = read(Path(args.credential_file))
    settings = {
        "CONTEXTDB_INSTANCE_ID": env["INSTANCE_ID"],
        "CONTEXTDB_CLOUD_TENANT_ID": env["CLOUD_TENANT_ID"],
        "CONTEXTDB_KEY_PEPPER": secrets.token_urlsafe(48),
        "CONTEXTDB_CONTROL_KEYS": json.dumps(
            [{"key_id": credential["key_id"], "sha256": credential["sha256"]}]
        ),
        "CONTEXTDB_CONTROL_NETWORKS": env.get(
            "CONTROL_NETWORKS", "127.0.0.1/32,::1/128"
        ),
        "CONTEXTDB_BOOTSTRAP_DATABASE_URL": env["DB_URL"],
        "HINDSIGHT_API_DATABASE_URL": env["DB_URL"],
        "HINDSIGHT_API_TENANT_EXTENSION": "hindsight_ext_contextdb.tenant:ContextDBTenantExtension",
        "HINDSIGHT_API_OPERATION_VALIDATOR_EXTENSION": "hindsight_ext_contextdb.validator:ContextDBOperationValidator",
        "HINDSIGHT_API_HTTP_EXTENSION": "hindsight_ext_contextdb.http:ContextDBHttpExtension",
        "HINDSIGHT_API_MCP_EXTENSION": "hindsight_ext_contextdb.mcp:ContextDBMCPExtension",
        "HINDSIGHT_API_MIGRATION_ISOLATION": "false",
        "HINDSIGHT_API_WORKER_ENABLED": "false",
        "HINDSIGHT_API_MCP_ENABLED": "true",
        "HINDSIGHT_API_DB_POOL_MAX_SIZE": "10",
        "HINDSIGHT_API_READ_DB_POOL_MAX_SIZE": "10",
        "HINDSIGHT_API_VECTOR_EXTENSION": "pgvector",
        "HINDSIGHT_API_TEXT_SEARCH_EXTENSION": "pgroonga",
        "HINDSIGHT_API_LLM_PROVIDER": "openai",
        "HINDSIGHT_API_LLM_BASE_URL": "https://api.modelarts-maas.com/v2",
        "HINDSIGHT_API_LLM_MODEL": "deepseek-v4.1-flash",
        "HINDSIGHT_API_LLM_API_KEY": env["MAAS_API_KEY"],
        "HINDSIGHT_API_EMBEDDINGS_PROVIDER": "openai",
        "HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL": "https://api.modelarts-maas.com/v1",
        "HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL": "bge-m3",
        "HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY": env["MAAS_API_KEY"],
        "HINDSIGHT_API_RERANKER_PROVIDER": "siliconflow",
        "HINDSIGHT_API_RERANKER_SILICONFLOW_BASE_URL": "https://api.modelarts-maas.com/v1",
        "HINDSIGHT_API_RERANKER_SILICONFLOW_MODEL": "bge-reranker-v2-m3",
        "HINDSIGHT_API_RERANKER_SILICONFLOW_API_KEY": env["MAAS_API_KEY"],
    }
    write_env(root / "api.env", settings)
    save(root / "ui-password.json", {"password": secrets.token_urlsafe(18)})
    print("Saved api.env and ui-password.json; secrets not printed.")


def configure_ui(args: argparse.Namespace) -> None:
    root = Path(args.state_dir)
    bootstrap = read(Path(args.bootstrap))
    # Registration returns BootstrapResult; recovery returns KeyIssued directly.
    key = bootstrap.get("admin_key") if "admin_key" in bootstrap else bootstrap
    if not key or not key.get("secret"):
        raise ValueError(
            "Bootstrap has no administrator secret; use the protected original response or recovery procedure"
        )
    password = read(root / "ui-password.json")["password"]
    settings = {
        "HINDSIGHT_CP_CONTEXTDB_ENABLED": "true",
        "HINDSIGHT_CP_ACCESS_KEY": password,
        "HINDSIGHT_CP_DATAPLANE_API_KEY": key["secret"],
        "HINDSIGHT_CP_DATAPLANE_API_URL": args.url.rstrip("/"),
    }
    target = root / "ui.env"
    if args.replace:
        # Explicit rotation reuses the UI password and replaces only its API Key.
        with tempfile.NamedTemporaryFile(mode="w", dir=root, delete=False) as stream:
            tmp = Path(stream.name)
            for name, value in settings.items():
                stream.write(f"export {name}={shlex.quote(value)}\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
    else:
        write_env(target, settings)
    print("Saved ui.env; secrets not printed.")


def execute(args: argparse.Namespace) -> Any:
    if args.command == "configure":
        return configure(args)
    if args.command == "configure-ui":
        return configure_ui(args)
    client = Client(args)
    prefix = "/ext/contextdb/v1"
    if args.command in {"instance-register", "admin-key-recover"}:
        register = args.command == "instance-register"
        body = (
            {
                "instance_id": args.instance_id,
                "cloud_tenant_id": args.cloud_tenant_id,
                "name": args.name,
            }
            if register
            else {"name": args.name}
        )
        path = prefix + (
            "/instances"
            if register
            else f"/instances/{identifier(args.instance_id)}/admin-keys"
        )
        directory = client.bind(args.request_id, "POST", path, body)
        response = directory / "response.json"
        # Never replace a saved one-time secret with a repeated registration's null.
        if response.exists():
            result = read(response)
        else:
            attempted = directory / "attempted.json"
            if not register and attempted.exists():
                raise ValueError(
                    "Recovery outcome is unknown; do not blindly retry. Inspect API audit before a new request ID."
                )
            save(attempted, {"attempted": True})
            result = client.call("POST", path, body)
            save(response, result)
        if register and not result.get("admin_key"):
            raise ValueError(
                "Instance exists but this response has no secret. Find original bootstrap or recover a new Key."
            )
        print(f"Protected response: {response}", file=sys.stderr)
        return public(result)
    if args.command == "instance-get":
        return client.call("GET", prefix + f"/instances/{identifier(args.instance_id)}")
    if args.command == "workspace-list":
        return client.call(
            "GET", prefix + f"/workspaces?limit={args.limit}&offset={args.offset}"
        )
    if args.command == "workspace-get":
        return client.call(
            "GET", prefix + f"/workspaces/{identifier(args.workspace_id)}"
        )
    if args.command in {"operation-get", "operation-wait"}:
        return (
            client.wait(args.operation_id)
            if args.command == "operation-wait"
            else client.call(
                "GET", prefix + f"/operations/{identifier(args.operation_id)}"
            )
        )
    if args.command in {"workspace-create", "workspace-delete"}:
        create = args.command == "workspace-create"
        body = {"name": args.name, "description": args.description} if create else None
        path = prefix + (
            "/workspaces" if create else f"/workspaces/{identifier(args.workspace_id)}"
        )
        method = "POST" if create else "DELETE"
        directory = client.bind(args.request_id, method, path, body)
        result = client.call(method, path, body, args.request_id)
        save(directory / "response.json", result)
        print(
            f"Accepted operation_id={result['operation_id']}; state={result['state']}",
            file=sys.stderr,
        )
        if args.no_wait:
            return result
        final = client.wait(result["operation_id"])
        save(directory / "final.json", final)
        if create:
            workspace = client.call(
                "GET", prefix + f"/workspaces/{identifier(result['workspace_id'])}"
            )
            if workspace["state"] != "active":
                raise ValueError("Operation succeeded but workspace is not active")
            save(directory / "workspace.json", workspace)
            return workspace
        return final
    raise ValueError("Unknown command")


def main() -> int:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8888")
    parser.add_argument("--credential-file", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--http-timeout", type=float, default=30)
    parser.add_argument("--wait-timeout", type=float, default=300)
    parser.add_argument("--interval", type=float, default=2)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("configure")
    ui = commands.add_parser("configure-ui")
    ui.add_argument("--bootstrap", required=True)
    ui.add_argument("--replace", action="store_true")
    for name in ("instance-register", "instance-get", "admin-key-recover"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--instance-id", required=True)
        if name != "instance-get":
            cmd.add_argument("--name", required=True)
            cmd.add_argument("--request-id", required=True)
        if name == "instance-register":
            cmd.add_argument("--cloud-tenant-id", required=True)
    listing = commands.add_parser("workspace-list")
    listing.add_argument("--limit", type=int, default=20, choices=range(101))
    listing.add_argument("--offset", type=int, default=0)
    for name in ("workspace-get", "workspace-delete"):
        cmd = commands.add_parser(name)
        cmd.add_argument("workspace_id")
        if name == "workspace-delete":
            cmd.add_argument("--request-id", required=True)
            cmd.add_argument("--no-wait", action="store_true")
    create = commands.add_parser("workspace-create")
    create.add_argument("--name", required=True)
    create.add_argument("--description", default="")
    create.add_argument("--request-id", required=True)
    create.add_argument("--no-wait", action="store_true")
    for name in ("operation-get", "operation-wait"):
        commands.add_parser(name).add_argument("operation_id")
    args = parser.parse_args()
    if args.http_timeout <= 0 or args.wait_timeout <= 0 or args.interval <= 0:
        parser.error("Timeouts and interval must be positive")
    try:
        result = execute(args)
        if result is not None:
            print(json.dumps(public(result), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, OSError) as error:
        # File-system messages do not contain credential contents. JSON errors have
        # only line/column information. No traceback of deployment configuration.
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
