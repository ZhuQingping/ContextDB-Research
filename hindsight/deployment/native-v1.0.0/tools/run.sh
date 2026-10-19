#!/usr/bin/env bash
set -euo pipefail
# Foreground processes are supervised by the existing node Agent/container runtime.
# Usage: run.sh api|worker|ui /absolute/native/source /absolute/private/runtime
role=${1:?api|worker|ui}
source_root=${2:?native source path}
runtime=${3:?private runtime path}
[[ "$source_root" = /* && "$runtime" = /* ]] || exit 2
[[ "$(git -C "$source_root" rev-parse HEAD)" = 39c65ffe2f140d0c84cee58566cad8900c5b9908 ]] || { echo 'Native v1.0.0 checkout required' >&2; exit 2; }
[[ -z "$(git -C "$source_root" status --porcelain --untracked-files=no)" ]] || { echo 'Native tracked source must be unmodified' >&2; exit 2; }
cd "$runtime"
set -a
case "$role" in
 api|worker) source "$runtime/api.env" ;;
 ui) source "$runtime/ui.env" ;;
 *) echo 'Expected api, worker or ui' >&2; exit 2 ;;
esac
set +a
case "$role" in
 api) exec "$source_root/.venv/bin/hindsight-api" ;;
 worker)
   export HINDSIGHT_API_RUN_MIGRATIONS_ON_STARTUP=false
   exec "$source_root/.venv/bin/hindsight-worker" ;;
 ui) exec node "$source_root/hindsight-control-plane/bin/cli.js" ;;
esac
