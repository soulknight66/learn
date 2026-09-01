#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${FPC:-fpc}
binary=${MICA_BIN:-"$repo_dir/starter/bin/mica"}

if [[ ! -x "$binary" ]]; then
  if ! command -v "$compiler" >/dev/null 2>&1; then
    echo "PARTIAL: Pascal compiler '$compiler' is unavailable and MICA_BIN is not executable" >&2
    exit 2
  fi
  make -C "$repo_dir/starter" FPC="$compiler"
fi

MICA_BIN="$binary" python3 "$repo_dir/public_tests/run_tests.py"
