#!/bin/sh
# Run original tests in isolated copied source. Known missing external services are explicitly excluded.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 "$base/scripts/tests_run.py" --name tests-api-localml-offline --cwd "$base/tests-work/source/hindsight-api-slim" \
  env -u http_proxy -u https_proxy -u all_proxy -u ALL_PROXY -u HTTPS_PROXY \
  HF_HUB_DISABLE_XET=1 HF_HUB_OFFLINE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  "$base/tests-work/localml-venv/bin/python" -m pytest tests -n 2 -s \
  -m 'not hs_llm_mat and not hs_llm_core and not integration and not slow and not oracle' \
  --ignore=tests/test_fact_extraction_analysis.py \
  --ignore=tests/test_fact_extraction_output_ratio.py \
  --ignore=tests/test_file_storage_s3.py \
  '--deselect=tests/test_llm_timeout_propagation.py::test_every_network_provider_receives_the_resolved_timeout[github-copilot-extra3]' \
  --maxfail=30 --junitxml="$base/evidence/tests-api-localml-offline/junit.xml" --basetemp="$base/evidence/tests-api-localml-offline/tmp"
