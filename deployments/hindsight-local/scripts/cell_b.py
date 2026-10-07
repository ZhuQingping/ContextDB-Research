#!/usr/bin/env python3
"""Start/stop the disposable second PG cell used by tenant and restore checks."""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"])
    args = parser.parse_args()
    pid_file = ROOT / ".runtime/cell-b.pid"
    pid = int(pid_file.read_text()) if pid_file.exists() else None
    running = False
    if pid:
        try:
            os.kill(pid, 0)
            running = True
        except ProcessLookupError:
            pass
    if args.action == "stop" and running:
        cmd = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True)
        if str(ROOT) not in cmd:
            raise RuntimeError("PID no longer belongs to this deployment")
        os.killpg(pid, signal.SIGTERM)
        print("Cell B termination requested; PG data is retained")
        return
    if args.action != "start" or running:
        print("Cell B:", "running" if running else "stopped", pid)
        return
    env = os.environ.copy()
    env.update(json.loads((ROOT / "config.json").read_text()))
    key_file = ROOT / ".secrets/cell-b-keys.json"
    if not key_file.exists():
        key_file.parent.mkdir(exist_ok=True, mode=0o700)
        key_file.write_text(json.dumps({n: secrets.token_urlsafe(24) for n in ["team_a", "team_b"]}))
        key_file.chmod(0o600)
    keys = json.loads(key_file.read_text())
    env.update({"HINDSIGHT_API_PORT": "8890", "HINDSIGHT_API_DATABASE_URL": "pg0://contextdb-research-cell-b:55433",
                "HINDSIGHT_API_TENANT_EXTENSION": "hindsight_ext_static_keys_tenant:StaticKeysTenantExtension",
                "HINDSIGHT_API_TENANT_USERS": ",".join(k + ":" + v for k, v in keys.items()),
                "HINDSIGHT_API_WORKER_ID": "contextdb-cell-b",
                "PYTHONPATH": "/Users/zhuqingping/Work/Database/Context/hindsight/hindsight-extensions/static-keys-tenant"})
    with (ROOT / ".runtime/logs/cell-b.log").open("ab") as log:
        proc = subprocess.Popen([str(ROOT / ".venv/bin/hindsight-api")], cwd=ROOT, env=env,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pid_file.write_text(str(proc.pid))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(60):
        try:
            with opener.open("http://127.0.0.1:8890/health", timeout=2) as response:
                if response.status == 200:
                    break
        except OSError:
            pass
        time.sleep(1)
    # Global discovery routines live in public even when data lives in tenant schemas.
    env["HINDSIGHT_API_DATABASE_URL"] = "postgresql://hindsight:hindsight@127.0.0.1:55433/hindsight"
    with (ROOT / ".runtime/logs/cell-b-migrate.log").open("a") as log:
        subprocess.run([str(ROOT / ".venv/bin/hindsight-admin"), "run-db-migration", "--schema", "public"],
                       env=env, check=True, stdout=log, stderr=log)
    print("Cell B ready on 127.0.0.1:8890; two private keys remain in .secrets")


if __name__ == "__main__":
    main()
