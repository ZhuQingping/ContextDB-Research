"""The native handoff renders independently, preserves secrets and rejects bad input."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HELPERS = Path(__file__).parents[1]


def test_native_rds_example_uses_builtin_fulltext(tmp_path: Path) -> None:
    config = json.loads((HELPERS / "intent.example.json").read_text())
    for key, value in {
        "database_url_file": "postgresql://service:synthetic-password@db:5432/test",
        "maas_api_key_file": "synthetic-maas-key",
        "ui_password_file": "synthetic-ui-password",
    }.items():
        path = tmp_path / key
        path.write_text(value)
        path.chmod(0o600)
        config[key] = str(path)
    assert config["text_search"] == "native" and config["topology"] == "merged"
    intent = tmp_path / "intent.json"
    intent.write_text(json.dumps(config))
    subprocess.run(
        [sys.executable, "-I", "-S", str(HELPERS / "render.py"), str(intent), str(tmp_path / "runtime")], check=True
    )
    environment = (tmp_path / "runtime/api.env").read_text()
    assert "HINDSIGHT_API_TEXT_SEARCH_EXTENSION=native\n" in environment
    assert "HINDSIGHT_API_TEXT_SEARCH_EXTENSION_NATIVE_LANGUAGE=english\n" in environment
    assert "pgroonga" not in environment


@pytest.mark.parametrize("topology", ["merged", "split"])
def test_native_render_preserves_private_credentials_and_refuses_overwrite(tmp_path: Path, topology: str) -> None:
    values = {
        "database_url_file": "postgresql://service:synthetic-test-pass@db:5432/test",
        "maas_api_key_file": "synthetic-maas-key",
        "ui_password_file": "synthetic-ui-password-$'quoted",
    }
    config = {"topology": topology, "text_search": "native", "ui_api_url": "http://api:8888"}
    for key, value in values.items():
        path = tmp_path / key
        path.write_text(value)
        path.chmod(0o600)
        config[key] = str(path)
    intent = tmp_path / "intent.json"
    intent.write_text(json.dumps(config))
    output = tmp_path / "runtime"
    command = [sys.executable, "-I", "-S", str(HELPERS / "render.py"), str(intent), str(output)]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0 and not any(value in first.stdout + first.stderr for value in values.values())
    assert output.stat().st_mode & 0o077 == 0
    snapshot = {path.name: path.read_bytes() for path in output.iterdir()}
    assert all(path.stat().st_mode & 0o077 == 0 for path in output.iterdir())
    assert "CONTEXTDB_" not in (output / "api.env").read_text()
    expected = "true" if topology == "merged" else "false"
    assert f"HINDSIGHT_API_WORKER_ENABLED={expected}" in (output / "api.env").read_text()
    # Shell quoting must preserve caller-specified punctuation, rather than execute it.
    check = subprocess.run(
        [
            "bash",
            "-c",
            'set -a; source "$1"; python3 -c \'import os; assert os.environ["HINDSIGHT_CP_ACCESS_KEY"] == os.environ["EXPECTED"]\'',
            "test",
            str(output / "ui.env"),
        ],
        env={**os.environ, "EXPECTED": values["ui_password_file"]},
        capture_output=True,
    )
    assert check.returncode == 0
    repeated = subprocess.run(command, capture_output=True, text=True)
    assert repeated.returncode != 0
    assert snapshot == {path.name: path.read_bytes() for path in output.iterdir()}
    # Never permit a public secret input or leak it in validation errors.
    (tmp_path / "maas_api_key_file").chmod(0o644)
    rejected = subprocess.run([*command[:-1], str(tmp_path / "other")], capture_output=True, text=True)
    assert rejected.returncode != 0 and not (tmp_path / "other").exists()
    assert "synthetic-maas-key" not in rejected.stdout + rejected.stderr
