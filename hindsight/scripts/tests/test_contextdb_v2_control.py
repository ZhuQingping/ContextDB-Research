"""CLI integration tests with a local HTTP server; no real PG or cloud writes."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPT = Path(__file__).resolve().parents[1] / "contextdb-v2-control.py"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.handle_call()

    def do_POST(self):
        self.handle_call()

    def do_DELETE(self):
        self.handle_call()

    def handle_call(self):
        server = self.server
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length)) if length else None
        server.calls.append(
            {
                "method": self.command,
                "path": self.path,
                "headers": dict(self.headers),
                "body": body,
            }
        )
        if server.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "/sink")
            self.end_headers()
            return
        if server.mode == "http-error":
            return self.reply(
                403, {"error": {"code": "forbidden", "secret": "must-not-print"}}
            )
        if self.path.endswith("/admin-keys"):
            if server.mode == "lost-recovery":
                self.connection.shutdown(2)
                self.connection.close()
                return
            return self.reply(
                201, {"key_id": "k1", "secret": "admin-secret", "access_mode": "all"}
            )
        if self.path.endswith("/instances"):
            return self.reply(
                201,
                {
                    "instance": {"instance_id": "i1"},
                    "admin_user": {"role": "admin"},
                    "admin_key": None
                    if server.mode == "registered"
                    else {"secret": "admin-secret"},
                },
            )
        if "/operations/" in self.path:
            server.polls += 1
            state = (
                "failed"
                if server.mode == "failed"
                else (
                    "running"
                    if server.mode == "timeout" or server.polls == 1
                    else "succeeded"
                )
            )
            return self.reply(
                200,
                {
                    "operation_id": "op1",
                    "workspace_id": "ws1",
                    "state": state,
                    "error_code": "waiting_for_tasks" if state == "running" else None,
                },
            )
        if self.path.endswith("/workspaces") and self.command == "POST":
            return self.reply(
                202, {"operation_id": "op1", "workspace_id": "ws1", "state": "pending"}
            )
        if self.command == "DELETE":
            return self.reply(
                202, {"operation_id": "op1", "workspace_id": "ws1", "state": "pending"}
            )
        if self.path.endswith("/workspaces/ws1"):
            return self.reply(
                200, {"workspace_id": "ws1", "name": "中文空间", "state": "active"}
            )
        return self.reply(200, {"items": [], "total": 0, "limit": 20, "offset": 0})


class ControlCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.credential = self.root / "control-key.json"
        self.credential.write_text(
            json.dumps(
                {"secret": "control-secret", "key_id": "a" * 32, "sha256": "b" * 64}
            )
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.mode = "ok"
        self.server.calls = []
        self.server.polls = 0
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = [
            "python3",
            str(SCRIPT),
            "--url",
            f"http://127.0.0.1:{self.server.server_port}",
            "--credential-file",
            str(self.credential),
            "--actor",
            "real-console-user",
            "--state-dir",
            str(self.root),
            "--interval",
            ".01",
            "--wait-timeout",
            ".12",
        ]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def run_cli(self, *args, expected=0, env=None, base=None):
        result = subprocess.run(
            [*(base or self.base), *args], capture_output=True, text=True, env=env
        )
        self.assertEqual(result.returncode, expected, result.stderr)
        self.assertNotIn("admin-secret", result.stdout + result.stderr)
        self.assertNotIn("control-secret", result.stdout + result.stderr)
        return result

    def register(self):
        return self.run_cli(
            "instance-register",
            "--instance-id",
            "i1",
            "--cloud-tenant-id",
            "t1",
            "--name",
            "实例",
            "--request-id",
            "init1",
        )

    def test_registration_caches_one_time_secret(self):
        self.register()
        saved = self.root / "requests/init1/response.json"
        original = saved.read_bytes()
        self.server.mode = "registered"
        self.register()
        self.assertEqual(saved.read_bytes(), original)
        self.assertEqual(len(self.server.calls), 1)
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(original)["admin_key"]["secret"], "admin-secret")

    def test_registration_null_secret_needs_recovery(self):
        self.server.mode = "registered"
        self.run_cli(
            "instance-register",
            "--instance-id",
            "i1",
            "--cloud-tenant-id",
            "t1",
            "--name",
            "实例",
            "--request-id",
            "init1",
            expected=1,
        )
        self.assertIsNone(
            json.loads((self.root / "requests/init1/response.json").read_text())[
                "admin_key"
            ]
        )

    def test_create_waits_and_checks_active(self):
        out = self.run_cli(
            "workspace-create", "--name", "中文空间", "--request-id", "create1"
        )
        self.assertEqual(json.loads(out.stdout)["state"], "active")
        first = self.server.calls[0]
        self.assertEqual(first["path"], "/ext/contextdb/v1/workspaces")
        self.assertEqual(first["body"], {"name": "中文空间", "description": ""})
        self.assertEqual(first["headers"]["X-Contextdb-Control-Key"], "control-secret")
        self.assertEqual(
            first["headers"]["X-Contextdb-Actor-Subject"], "real-console-user"
        )
        self.assertEqual(first["headers"]["Idempotency-Key"], "create1")
        self.assertTrue((self.root / "requests/create1/workspace.json").exists())
        self.assertEqual(self.server.polls, 2)

    def test_request_id_binding_rejects_changed_body_or_actor(self):
        self.run_cli(
            "workspace-create", "--name", "A", "--request-id", "same", "--no-wait"
        )
        self.run_cli(
            "workspace-create",
            "--name",
            "B",
            "--request-id",
            "same",
            "--no-wait",
            expected=1,
        )
        other = list(self.base)
        other[other.index("--actor") + 1] = "another-user"
        self.run_cli(
            "workspace-create",
            "--name",
            "A",
            "--request-id",
            "same",
            "--no-wait",
            expected=1,
            base=other,
        )
        self.assertEqual(len(self.server.calls), 1)

    def test_no_wait_and_resume(self):
        out = self.run_cli(
            "workspace-create", "--name", "A", "--request-id", "async1", "--no-wait"
        )
        self.assertEqual(json.loads(out.stdout)["state"], "pending")
        self.assertEqual(self.server.polls, 0)
        out = self.run_cli("operation-wait", "op1")
        self.assertEqual(json.loads(out.stdout)["state"], "succeeded")

    def test_delete_uses_delete_and_retains_waiting_operation(self):
        out = self.run_cli("workspace-delete", "ws1", "--request-id", "delete1")
        self.assertEqual(json.loads(out.stdout)["state"], "succeeded")
        self.assertEqual(self.server.calls[0]["method"], "DELETE")
        self.assertEqual(
            self.server.calls[0]["path"], "/ext/contextdb/v1/workspaces/ws1"
        )
        self.assertIsNone(self.server.calls[0]["body"])
        self.assertTrue((self.root / "requests/delete1/final.json").exists())

    def test_failed_operation_returns_nonzero_and_saves_evidence(self):
        self.server.mode = "failed"
        out = self.run_cli(
            "workspace-create", "--name", "A", "--request-id", "failed1", expected=1
        )
        self.assertIn("Operation failed", out.stderr)
        self.assertEqual(
            json.loads((self.root / "operations/op1.json").read_text())["state"],
            "failed",
        )

    def test_wait_timeout_does_not_submit_new_operation(self):
        self.server.mode = "timeout"
        self.run_cli(
            "workspace-create", "--name", "A", "--request-id", "timeout1", expected=1
        )
        self.server.mode = "ok"
        self.run_cli("operation-wait", "op1")
        self.assertEqual(sum(call["method"] == "POST" for call in self.server.calls), 1)

    def test_recovery_response_shape_and_explicit_ui_rotation(self):
        self.run_cli(
            "admin-key-recover",
            "--instance-id",
            "i1",
            "--name",
            "recovery",
            "--request-id",
            "recover1",
        )
        response = self.root / "requests/recover1/response.json"
        self.assertEqual(json.loads(response.read_text())["secret"], "admin-secret")
        (self.root / "ui-password.json").write_text(
            json.dumps({"password": "stable-ui-password"})
        )
        self.run_cli("configure-ui", "--bootstrap", str(response))
        initial = (self.root / "ui.env").read_text()
        self.assertIn("stable-ui-password", initial)
        self.assertIn("admin-secret", initial)
        self.run_cli("configure-ui", "--bootstrap", str(response), expected=1)
        self.run_cli("configure-ui", "--bootstrap", str(response), "--replace")
        self.assertEqual((self.root / "ui.env").read_text(), initial)

    def test_unknown_recovery_outcome_cannot_be_blindly_retried(self):
        self.server.mode = "lost-recovery"
        args = [
            "admin-key-recover",
            "--instance-id",
            "i1",
            "--name",
            "recovery",
            "--request-id",
            "recover1",
        ]
        self.run_cli(*args, expected=1)
        self.server.mode = "ok"
        self.run_cli(*args, expected=1)
        self.assertEqual(len(self.server.calls), 1)

    def test_http_error_is_nonzero_and_redacts_secret(self):
        self.server.mode = "http-error"
        out = self.run_cli("workspace-list", expected=1)
        self.assertIn("HTTP 403", out.stderr)
        self.assertNotIn("must-not-print", out.stderr)

    def test_redirect_is_not_followed(self):
        self.server.mode = "redirect"
        out = self.run_cli("workspace-list", expected=1)
        self.assertIn("HTTP 302", out.stderr)
        self.assertEqual(len(self.server.calls), 1)

    def test_configure_is_one_time_and_no_dimensions(self):
        env = dict(
            os.environ,
            DB_URL="postgresql://service:pw@127.0.0.1:5540/newdb",
            INSTANCE_ID="i1",
            CLOUD_TENANT_ID="t1",
            MAAS_API_KEY="private-maas-key",
        )
        self.run_cli("configure", env=env)
        config = (self.root / "api.env").read_bytes()
        self.assertIn(b"HINDSIGHT_API_WORKER_ENABLED=false", config)
        self.assertNotIn(b"OPENAI_DIMENSIONS", config)
        self.assertEqual((self.root / "api.env").stat().st_mode & 0o777, 0o600)
        self.run_cli("configure", expected=1, env=env)
        self.assertEqual((self.root / "api.env").read_bytes(), config)


class NodeFunctions(unittest.TestCase):
    def test_fresh_shell_restores_paths_and_ui_gets_only_its_config(self):
        import shlex
        import sys
        import time

        node_script = SCRIPT.with_name("contextdb-v2-node.sh")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            code = root / "code"
            code.mkdir()
            bin_dir = root / "bin"
            bin_dir.mkdir()
            server = code / "hindsight-control-plane/standalone/server.js"
            server.parent.mkdir(parents=True)
            server.write_text("// fake server artifact")
            node = bin_dir / "node"
            node.write_text(
                f'#!{sys.executable}\nimport json,os,sys,time\nopen(sys.argv[1]+".env.json","w").write(json.dumps(dict(os.environ)))\ntime.sleep(1)\n'
            )
            node.chmod(0o700)
            settings = {
                "DEPLOY": str(root),
                "CODE": str(code),
                "RESEARCH": str(root / "research"),
                "ACTOR": "operator",
                "INSTANCE_ID": "i1",
                "API_URL": "http://127.0.0.1:8890",
                "API_PORT": "8890",
                "WORKER_PORT": "8891",
                "UI_PORT": "9998",
                "PG_BIN": "/private/pg/bin",
                "NODE_BIN": str(node),
                "PYTHON_CLI_BIN": sys.executable,
            }
            (root / "operator.env").write_text(
                "".join(f"export {k}={shlex.quote(v)}\n" for k, v in settings.items())
            )
            (root / "ui.env").write_text(
                "export HINDSIGHT_CP_CONTEXTDB_ENABLED=true\nexport HINDSIGHT_CP_ACCESS_KEY=ui-password\nexport HINDSIGHT_CP_DATAPLANE_API_KEY=ui-api-key\nexport HINDSIGHT_CP_DATAPLANE_API_URL=http://127.0.0.1:8890\n"
            )
            env = dict(
                os.environ,
                DEPLOY=str(root),
                PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
                DB_URL="private-database",
                HINDSIGHT_API_DATABASE_URL="private-database",
                CONTEXTDB_BOOTSTRAP_DATABASE_URL="private-database",
                CONTEXTDB_KEY_PEPPER="private-pepper",
                MAAS_API_KEY="private-model",
                CONTEXTDB_CONTROL_KEYS="private-control",
            )
            bash = f"source {shlex.quote(str(node_script))}\n"
            bash += 'test "$PY" = "$DEPLOY/venv/bin/python"\ntest "$PYTHONPATH" = "$CODE/hindsight-extensions/contextdb-service"\n'
            bash += "type ctxctl >/dev/null\ntype ctxdb_start_api >/dev/null\n"
            # Bypass only readiness/port probes; exercise the real clean-env launcher.
            bash += "ctxdb_port_free() { return 0; }\nwait_http() { return 0; }\nctxdb_start_ui\n"
            result = subprocess.run(
                ["bash", "-e", "-c", bash], env=env, capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = Path(str(server) + ".env.json")
            for _ in range(250):
                if output.exists():
                    break
                time.sleep(0.02)
            self.assertTrue(output.exists(), (root / "ui.log").read_text())
            settings = json.loads(output.read_text())
            self.assertEqual(settings["HINDSIGHT_CP_ACCESS_KEY"], "ui-password")
            self.assertEqual(settings["HINDSIGHT_CP_DATAPLANE_API_KEY"], "ui-api-key")
            self.assertEqual(settings["HOSTNAME"], "0.0.0.0")
            for key in [
                "DB_URL",
                "HINDSIGHT_API_DATABASE_URL",
                "CONTEXTDB_BOOTSTRAP_DATABASE_URL",
                "CONTEXTDB_KEY_PEPPER",
                "MAAS_API_KEY",
                "CONTEXTDB_CONTROL_KEYS",
            ]:
                self.assertNotIn(key, settings)

    def test_stop_accepts_our_next_title_with_start_identity_and_package_cwd(self):
        import shlex
        import shutil
        import sys

        node_bin = shutil.which("node")
        self.assertIsNotNone(
            node_bin, "Node must be installed to validate its process title"
        )
        node_script = SCRIPT.with_name("contextdb-v2-node.sh")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            code = root / "code"
            standalone = code / "hindsight-control-plane/standalone"
            standalone.mkdir(parents=True)
            ready = standalone / "ready"
            server = standalone / "server.js"
            server.write_text(
                'process.title="next-server (fixture)"; process.chdir(__dirname); '
                'require("fs").writeFileSync("ready","ok"); setInterval(()=>{},1000);'
            )
            settings = {
                "DEPLOY": str(root),
                "CODE": str(code),
                "RESEARCH": str(root),
                "UI_PORT": "9998",
                "NODE_BIN": node_bin,
                "PYTHON_CLI_BIN": sys.executable,
            }
            (root / "operator.env").write_text(
                "".join(f"export {k}={shlex.quote(v)}\n" for k, v in settings.items())
            )
            (root / "ui.env").write_text("export HINDSIGHT_CP_CONTEXTDB_ENABLED=true\n")
            commands = f"source {shlex.quote(str(node_script))}\n"
            commands += "ctxdb_port_free() { return 0; }\n"
            commands += f"wait_http() {{ for n in $(seq 1 100); do [ -f {shlex.quote(str(ready))} ] && return 0; sleep .02; done; return 1; }}\n"
            commands += "ctxdb_start_ui\n"
            commands += 'pid=$(cat "$DEPLOY/ui.pid"); ps -p "$pid" -o command=\n'
            commands += "ctxdb_stop_service ui\n"
            try:
                result = subprocess.run(
                    ["bash", "-e", "-c", commands],
                    env=dict(os.environ, DEPLOY=str(root)),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("next-server", result.stdout)
                self.assertFalse((root / "ui.pid").exists())
            finally:
                pidfile = root / "ui.pid"
                if pidfile.exists():
                    # This is only the subprocess created by the isolated fixture.
                    try:
                        os.kill(int(pidfile.read_text()), 15)
                    except ProcessLookupError:
                        pass

    def test_stop_rejects_an_unrelated_live_pid(self):
        import shlex

        node_script = SCRIPT.with_name("contextdb-v2-node.sh")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "operator.env").write_text(
                f"export CODE={shlex.quote(str(root))}\nexport RESEARCH={shlex.quote(str(root))}\n"
            )
            (root / "api.pid").write_text(str(os.getpid()))
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    f"source {shlex.quote(str(node_script))}; ctxdb_stop_service api",
                ],
                env=dict(os.environ, DEPLOY=str(root)),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            os.kill(os.getpid(), 0)


if __name__ == "__main__":
    unittest.main()
