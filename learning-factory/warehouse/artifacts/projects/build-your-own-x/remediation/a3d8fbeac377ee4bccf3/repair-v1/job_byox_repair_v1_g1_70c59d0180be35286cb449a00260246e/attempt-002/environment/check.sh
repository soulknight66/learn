#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${FPC:-fpc}
binary=${MICA_BIN:-"$repo_dir/starter/bin/mica"}
runner="$repo_dir/environment/run_with_limits.py"
build_deadline=${MICA_BUILD_TIMEOUT_SECONDS:-60}
suite_deadline=${MICA_SUITE_TIMEOUT_SECONDS:-90}

if [[ ! -x "$binary" ]]; then
  if ! command -v "$compiler" >/dev/null 2>&1; then
    echo "PARTIAL: Pascal compiler '$compiler' is unavailable and MICA_BIN is not executable" >&2
    exit 2
  fi
  python3 "$runner" --timeout "$build_deadline" --max-output-bytes 131072 \
    --cwd "$repo_dir" -- make -C "$repo_dir/starter" "FPC=$compiler"
fi

MICA_BIN="$binary" python3 "$runner" --timeout "$suite_deadline" \
  --max-output-bytes 262144 --cwd "$repo_dir" -- \
  python3 -B "$repo_dir/public_tests/run_tests.py"
