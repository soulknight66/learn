#!/bin/sh
set -eu

for tool in cc make python3; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "missing required tool: $tool" >&2
        exit 1
    fi
    echo "$tool: $(command -v "$tool")"
done

printf 'C compiler: '
cc --version 2>/dev/null | sed -n '1p'
printf 'make: '
make --version 2>/dev/null | sed -n '1p'
printf 'python: '
python3 --version 2>&1
