#!/usr/bin/env python3
"""Node-Agent helper: render native v1.0.0 config without importing ContextDB."""

import argparse
import json
import os
import secrets
import shlex
import stat
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class NativeDeployment:
    database_url_file: str
    maas_api_key_file: str
    ui_password_file: str
    topology: str
    text_search: str
    ui_api_url: str
    api_port: int = 8888
    ui_port: int = 9999
    llm_model: str = "deepseek-v4.1-flash"
    db_pool_max: int = 10
    pg_search_tokenizer: str | None = None


def private_read(path: str) -> str:
    source = Path(path)
    if not source.is_absolute() or source.is_symlink() or not source.is_file() or source.stat().st_mode & 0o077:
        raise ValueError("Secret input must be an absolute private file (0600)")
    value = source.read_text().strip()
    if not value or any(char in value for char in "\r\n\0"):
        raise ValueError("Secret input must be a nonempty single line")
    return value


def write_env(path: Path, values: dict[str, str]) -> None:
    # Never truncate a provisioned credential/config on a repeated create request.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write("".join(f"{name}={shlex.quote(value)}\n" for name, value in values.items()))


def render(intent: Path, destination: Path) -> None:
    config = NativeDeployment(**json.loads(intent.read_text()))
    if config.topology not in {"merged", "split"} or config.text_search not in {"native", "pgroonga", "pg_search"}:
        raise ValueError("Unsupported native deployment mode")
    api_port, ui_port = config.api_port, config.ui_port
    if any(type(port) is not int or not 1024 <= port <= 65535 for port in (api_port, ui_port)) or api_port == ui_port:
        raise ValueError("Invalid or conflicting ports")
    budget = config.db_pool_max
    if type(budget) is not int or not 2 <= budget <= 100:
        raise ValueError("db_pool_max must be 2..100")
    url = urlsplit(config.ui_api_url)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username
        or url.query
        or url.fragment
        or url.path not in {"", "/"}
    ):
        raise ValueError("ui_api_url must be a credential-free API origin")
    if url.port is not None and not 1 <= url.port <= 65535:
        raise ValueError("Invalid UI API port")
    if not isinstance(config.llm_model, str) or not 1 <= len(config.llm_model) <= 128:
        raise ValueError("Invalid model identifier")
    if config.pg_search_tokenizer is not None and (
        not isinstance(config.pg_search_tokenizer, str) or not 1 <= len(config.pg_search_tokenizer) <= 128
    ):
        raise ValueError("Invalid tokenizer")
    database = private_read(config.database_url_file)
    db = urlsplit(database)
    if db.scheme not in {"postgresql", "postgres"} or not db.hostname or not db.path.strip("/"):
        raise ValueError("Provide an external PostgreSQL URL including database")
    maas, password = private_read(config.maas_api_key_file), private_read(config.ui_password_file)
    if len(password) < 16:
        raise ValueError("Use a UI password of at least 16 characters")
    tokenizer = config.pg_search_tokenizer
    if tokenizer and config.text_search != "pg_search":
        raise ValueError("Tokenizer applies only to pg_search")
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    if destination.is_symlink() or stat.S_IMODE(destination.stat().st_mode) & 0o077:
        raise ValueError("Output directory must be private (0700)")
    if any((destination / name).exists() for name in ("api.env", "ui.env", "api-key", "ports.env")):
        raise ValueError("Deployment already exists; reuse its configuration instead of regenerating keys")
    api_key = secrets.token_urlsafe(48)
    api = {
        "PYTHON_DOTENV_DISABLED": "1",
        "HINDSIGHT_API_DATABASE_URL": database,
        "HINDSIGHT_API_DATABASE_SCHEMA": "public",
        "HINDSIGHT_API_HOST": "0.0.0.0",
        "HINDSIGHT_API_PORT": str(api_port),
        "HINDSIGHT_API_WORKERS": "1",
        "HINDSIGHT_API_WORKER_ID": "hindsight-native-worker-0",
        "HINDSIGHT_API_WORKER_ENABLED": str(config.topology == "merged").lower(),
        "HINDSIGHT_API_RUN_MIGRATIONS_ON_STARTUP": "true",
        "HINDSIGHT_API_MIGRATION_ISOLATION": "false",
        "HINDSIGHT_API_DB_POOL_MIN_SIZE": "1",
        "HINDSIGHT_API_DB_POOL_MAX_SIZE": str(budget),
        "HINDSIGHT_API_READ_DB_POOL_MIN_SIZE": "1",
        "HINDSIGHT_API_READ_DB_POOL_MAX_SIZE": str(budget),
        "HINDSIGHT_API_TENANT_EXTENSION": "hindsight_api.extensions.builtin.tenant:ApiKeyTenantExtension",
        "HINDSIGHT_API_TENANT_API_KEY": api_key,
        "HINDSIGHT_API_MCP_ENABLED": "true",
        "HINDSIGHT_API_VECTOR_EXTENSION": "pgvector",
        "HINDSIGHT_API_TEXT_SEARCH_EXTENSION": config.text_search,
        "HINDSIGHT_API_TEXT_SEARCH_EXTENSION_NATIVE_LANGUAGE": "english",
        "HINDSIGHT_API_LLM_PROVIDER": "openai",
        "HINDSIGHT_API_LLM_BASE_URL": "https://api.modelarts-maas.com/v2",
        "HINDSIGHT_API_LLM_MODEL": config.llm_model,
        "HINDSIGHT_API_LLM_API_KEY": maas,
        "HINDSIGHT_API_EMBEDDINGS_PROVIDER": "openai",
        "HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL": "https://api.modelarts-maas.com/v1",
        "HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL": "bge-m3",
        "HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY": maas,
        "HINDSIGHT_API_RERANKER_PROVIDER": "siliconflow",
        "HINDSIGHT_API_RERANKER_SILICONFLOW_BASE_URL": "https://api.modelarts-maas.com/v1",
        "HINDSIGHT_API_RERANKER_SILICONFLOW_MODEL": "bge-reranker-v2-m3",
        "HINDSIGHT_API_RERANKER_SILICONFLOW_API_KEY": maas,
        "HINDSIGHT_API_LOG_LEVEL": "info",
        "HINDSIGHT_API_LOG_FORMAT": "json",
    }
    if tokenizer:
        api["HINDSIGHT_API_TEXT_SEARCH_EXTENSION_PG_SEARCH_TOKENIZER"] = tokenizer
    write_env(destination / "api.env", api)
    write_env(
        destination / "ui.env",
        {
            "HINDSIGHT_CP_ACCESS_KEY": password,
            "HINDSIGHT_CP_DATAPLANE_API_KEY": api_key,
            "HINDSIGHT_CP_DATAPLANE_API_URL": config.ui_api_url,
            "HOSTNAME": "0.0.0.0",
            "PORT": str(ui_port),
        },
    )
    write_env(
        destination / "ports.env",
        {
            "API_PORT": str(api_port),
            "UI_PORT": str(ui_port),
            "COMPOSE_PROFILES": "split" if config.topology == "split" else "",
        },
    )
    fd = os.open(destination / "api-key", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(api_key + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intent", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        render(args.intent, args.destination)
    except (OSError, ValueError, TypeError, KeyError):
        parser.exit(1, "Native configuration rejected; check fields, private input files and output directory.\n")
    print("Native API/UI configuration created; secrets are not printed.")


if __name__ == "__main__":
    main()
