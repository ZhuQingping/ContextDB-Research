#!/usr/bin/env python3
"""Manage only this research deployment; credentials stay outside tracked files."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("component", choices=["api", "ui", "all"], default="all", nargs="?")
    args = parser.parse_args()
    env = os.environ.copy()
    env.update(json.loads((ROOT / "config.json").read_text()))
    env["HINDSIGHT_CP_DATAPLANE_API_URL"] = "http://127.0.0.1:8888"
    commands = {
        "api": [str(ROOT / ".venv/bin/hindsight-api")],
        "ui": ["node", str(RUNTIME / "ui/node_modules/@vectorize-io/hindsight-control-plane/bin/cli.js"),
               "--hostname", "127.0.0.1", "--port", "9999"],
    }
    names = ["api", "ui"] if args.component == "all" else [args.component]
    if args.action == "stop":
        names.reverse()
    (RUNTIME / "logs").mkdir(parents=True, exist_ok=True)
    for name in names:
        pid_file = RUNTIME / f"{name}.pid"
        pid = int(pid_file.read_text()) if pid_file.exists() else None
        running = pid is not None and alive(pid)
        if args.action == "start" and not running:
            with (RUNTIME / "logs" / f"{name}.log").open("ab") as log:
                proc = subprocess.Popen(commands[name], cwd=ROOT, env=env,
                                        stdin=subprocess.DEVNULL, stdout=log,
                                        stderr=subprocess.STDOUT, start_new_session=True)
            pid_file.write_text(str(proc.pid))
            print(f"{name}: started PID {proc.pid}; log .runtime/logs/{name}.log")
        elif args.action == "stop" and running:
            # Guard against a stale PID referring to an unrelated user process.
            command = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True)
            if str(ROOT) not in command:
                raise RuntimeError(f"Refusing to stop unrelated PID {pid}")
            os.killpg(pid, signal.SIGTERM)
            for _ in range(40):
                if not alive(pid):
                    break
                time.sleep(0.5)
            print(f"{name}: termination requested for PID {pid}")
            if not alive(pid):
                pid_file.unlink(missing_ok=True)
        else:
            print(f"{name}: {'running PID ' + str(pid) if running else 'stopped'}")
    if args.action == "status":
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for url in ["http://127.0.0.1:8888/health", "http://127.0.0.1:9999"]:
            try:
                with opener.open(url, timeout=5) as response:
                    print(f"{url}: HTTP {response.status}")
            except Exception as error:
                print(f"{url}: {type(error).__name__}")


if __name__ == "__main__":
    main()
