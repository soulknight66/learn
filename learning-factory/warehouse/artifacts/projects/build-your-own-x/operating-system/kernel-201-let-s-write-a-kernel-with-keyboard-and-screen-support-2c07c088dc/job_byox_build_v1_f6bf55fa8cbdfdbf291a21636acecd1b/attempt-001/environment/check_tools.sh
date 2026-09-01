#!/bin/sh
set -eu

required="gcc make ld readelf python3"
optional="qemu-system-i386 grub-file grub-mkrescue xorriso"
missing=0

for tool in $required; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "required: $tool: found"
    else
        echo "required: $tool: MISSING"
        missing=1
    fi
done

for tool in $optional; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "optional: $tool: found"
    else
        echo "optional: $tool: unavailable"
    fi
done

exit "$missing"
