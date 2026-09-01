#!/bin/sh
set -eu

kernel_path=${1:-starter/build/kernel.elf}

if ! command -v qemu-system-i386 >/dev/null 2>&1; then
    echo "qemu-system-i386 is unavailable" >&2
    exit 127
fi

if [ ! -f "$kernel_path" ]; then
    echo "kernel ELF does not exist: $kernel_path" >&2
    exit 2
fi

exec qemu-system-i386 \
    -kernel "$kernel_path" \
    -display curses \
    -no-reboot \
    -no-shutdown \
    -monitor none
