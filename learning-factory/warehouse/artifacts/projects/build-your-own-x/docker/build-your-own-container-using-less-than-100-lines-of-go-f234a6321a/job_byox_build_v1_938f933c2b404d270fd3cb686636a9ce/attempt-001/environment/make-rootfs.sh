#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 /absolute/path/to/new-rootfs" >&2
    exit 64
fi

target=$1
case "$target" in
    /*) ;;
    *) echo "rootfs path must be absolute" >&2; exit 64 ;;
esac
if [ "$target" = "/" ]; then
    echo "refusing to use host root" >&2
    exit 64
fi
if [ -L "$target" ]; then
    echo "refusing symbolic-link target" >&2
    exit 64
fi
if [ -e "$target" ] && [ ! -d "$target" ]; then
    echo "target exists and is not a directory" >&2
    exit 64
fi
if [ -d "$target" ] && [ -n "$(find "$target" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    echo "target directory must be empty" >&2
    exit 64
fi

mkdir -p "$target/bin" "$target/proc"
gcc -std=c11 -O2 -Wall -Wextra -Werror -static "$(dirname "$0")/probe.c" -o "$target/bin/probe"
chmod 0755 "$target/bin/probe"
echo "created static probe rootfs at $target"
