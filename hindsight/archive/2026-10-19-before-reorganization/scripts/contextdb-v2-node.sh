#!/usr/bin/env bash
# Source with DEPLOY pointing to the private instance directory.
# Commands run locally; the platform Agent remains responsible for supervision.
: "${DEPLOY:?Set DEPLOY to the existing instance directory before source}"
source "$DEPLOY/operator.env"
export PY="$DEPLOY/venv/bin/python"
export PYTHONPATH="$CODE/hindsight-extensions/contextdb-service"
export CTL="$RESEARCH/hindsight/scripts/contextdb-v2-control.py"
if [ -f "$DEPLOY/pg-target.env" ]; then source "$DEPLOY/pg-target.env"; fi

ctxctl() {
  "$PYTHON_CLI_BIN" "$CTL" --url "$API_URL" --credential-file "$DEPLOY/control-key.json" \
    --actor "$ACTOR" --state-dir "$DEPLOY" "$@"
}

wait_http() {
  local url=$1 n
  for n in $(seq 1 150); do
    if curl --noproxy '*' -fsS --max-time 3 "$url" >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  printf '未就绪: %s；检查本次 DEPLOY 下的日志\n' "$url" >&2
  return 1
}

ctxdb_port_free() {
  "$PYTHON_CLI_BIN" - "$1" <<'PY'
import socket,sys
with socket.socket() as connection:
    connection.bind(('0.0.0.0',int(sys.argv[1])))
PY
}

ctxdb_record_process() {
  local service=$1 pid=$2
  printf '%s\n' "$pid" > "$DEPLOY/$service.pid"
  ps -p "$pid" -o lstart= > "$DEPLOY/$service.started" || return
  [ -s "$DEPLOY/$service.started" ]
}

ctxdb_start_api() {
  ctxdb_port_free "$API_PORT" || return
  (
    cd "$CODE" || exit
    nohup env -i PATH="$PATH" HOME="$HOME" bash -c '
      set -e
      source "$1"
      export PYTHONPATH="$2"
      exec "$3" -m hindsight_api.main --host 0.0.0.0 --port "$4"
    ' -- "$DEPLOY/api.env" "$PYTHONPATH" "$PY" "$API_PORT" > "$DEPLOY/api.log" 2>&1 &
    ctxdb_record_process api "$!"
  ) || return
  wait_http "$API_URL/health/ready"
}

ctxdb_start_worker() {
  ctxdb_port_free "$WORKER_PORT" || return
  (
    cd "$CODE" || exit
    nohup env -i PATH="$PATH" HOME="$HOME" bash -c '
      set -e
      source "$1"
      export PYTHONPATH="$2"
      exec "$3" -m hindsight_api.worker.main --worker-id "$4" --http-host 127.0.0.1 --http-port "$5"
    ' -- "$DEPLOY/api.env" "$PYTHONPATH" "$PY" "$INSTANCE_ID-worker-1" "$WORKER_PORT" \
      > "$DEPLOY/worker.log" 2>&1 &
    ctxdb_record_process worker "$!"
  ) || return
  wait_http "http://127.0.0.1:$WORKER_PORT/health/ready"
}

ctxdb_start_ui() {
  ctxdb_port_free "$UI_PORT" || return
  (
    cd "$CODE" || exit
    # Load only the four UI settings in a clean environment. Do not expose API
    # model/DB/pepper credentials to Next; exec preserves the recorded PID.
    nohup env -i PATH="$PATH" HOME="$HOME" bash -c '
      set -e
      source "$1"
      export PORT="$3" HOSTNAME=0.0.0.0 NODE_ENV=production
      exec "$4" "$2"
    ' -- "$DEPLOY/ui.env" "$CODE/hindsight-control-plane/standalone/server.js" "$UI_PORT" "$NODE_BIN" \
      > "$DEPLOY/ui.log" 2>&1 &
    ctxdb_record_process ui "$!"
  ) || return
  wait_http "http://localhost:$UI_PORT/en/login"
}

ctxdb_status() {
  local service pid
  for service in api worker ui; do
    if [ -f "$DEPLOY/$service.pid" ]; then
      pid=$(cat "$DEPLOY/$service.pid")
      printf '%s: ' "$service"
      ps -p "$pid" -o pid=,command= || true
    fi
  done
  curl --noproxy '*' -fsS --max-time 5 "$API_URL/health/ready" || return
  curl --noproxy '*' -fsS --max-time 5 "http://127.0.0.1:$WORKER_PORT/health/ready" || return
  curl --noproxy '*' -fsS --max-time 5 "http://localhost:$UI_PORT/en/login" >/dev/null
}

ctxdb_stop_service() {
  local service=$1 pid command n started cwd code_cwd standalone_cwd
  case "$service" in api|worker|ui) ;; *) return 2 ;; esac
  [ -f "$DEPLOY/$service.pid" ] || return 0
  pid=$(cat "$DEPLOY/$service.pid")
  case "$pid" in ''|*[!0-9]*) printf 'Invalid PID\n' >&2; return 1 ;; esac
  command=$(ps -p "$pid" -o command=) || { rm "$DEPLOY/$service.pid"; return 0; }
  [ -s "$DEPLOY/$service.started" ] || { printf 'Missing process start identity\n' >&2; return 1; }
  started=$(ps -p "$pid" -o lstart=) || return
  [ "$started" = "$(cat "$DEPLOY/$service.started")" ] || { printf 'PID has been reused\n' >&2; return 1; }
  case "$service" in
    api) [[ "$command" == *"$PY"* && "$command" == *' -m hindsight_api.main '* ]] || return 1 ;;
    worker) [[ "$command" == *"$PY"* && "$command" == *' -m hindsight_api.worker.main '* ]] || return 1 ;;
    ui)
      # Next overwrites process.title; verify our PID/start time and package cwd
      # before accepting that title, rather than matching any next-server process.
      if [[ "$command" != *"$CODE/hindsight-control-plane/standalone/server.js"* ]]; then
        [[ "$command" == next-server* ]] || return 1
        cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
        code_cwd=$(cd "$CODE" && pwd -P) || return
        standalone_cwd=$(cd "$CODE/hindsight-control-plane/standalone" && pwd -P) || return
        [[ "$cwd" == "$code_cwd" || "$cwd" == "$standalone_cwd" ]] || return 1
      fi
      ;;
  esac
  kill -TERM "$pid" || return
  for n in $(seq 1 120); do
    if ! kill -0 "$pid" 2>/dev/null; then rm "$DEPLOY/$service.pid"; return 0; fi
    sleep 1
  done
  printf '%s 未退出；保留 PID，先查日志/在途任务，不强制 kill\n' "$service" >&2
  return 1
}
