#!/bin/sh
set -u

for tool in cc make arm-none-eabi-gcc qemu-system-arm; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf '%s: available\n' "$tool"
    else
        printf '%s: unavailable\n' "$tool"
    fi
done
