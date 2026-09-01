#!/bin/sh

set -u

check_tool() {
    tool=$1
    if command -v "$tool" >/dev/null 2>&1; then
        first_line=$($tool --version 2>/dev/null | sed -n '1p')
        printf '%-28s FOUND   %s\n' "$tool" "$first_line"
    else
        printf '%-28s MISSING\n' "$tool"
    fi
}

printf '%s\n' 'Host requirements:'
check_tool cc
check_tool make
printf '%s\n' 'Optional Raspberry Pi target tools:'
check_tool aarch64-none-elf-gcc
check_tool qemu-system-aarch64

if command -v cc >/dev/null 2>&1 && command -v make >/dev/null 2>&1; then
    printf '%s\n' 'HOST_READY=yes'
    exit 0
fi

printf '%s\n' 'HOST_READY=no'
exit 1
