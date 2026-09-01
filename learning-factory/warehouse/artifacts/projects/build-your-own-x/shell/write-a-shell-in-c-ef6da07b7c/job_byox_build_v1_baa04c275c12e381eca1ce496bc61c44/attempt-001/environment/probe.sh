#!/bin/sh
set -u

status=0

for tool in cc make python3 printf true false tr seq wc pwd cat sleep; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf '%-10s %s\n' "$tool" "FOUND"
    else
        printf '%-10s %s\n' "$tool" "MISSING"
        status=1
    fi
done

if command -v cc >/dev/null 2>&1; then
    cc --version 2>/dev/null | sed -n '1p'
fi
if command -v python3 >/dev/null 2>&1; then
    python3 --version
fi

exit "$status"
