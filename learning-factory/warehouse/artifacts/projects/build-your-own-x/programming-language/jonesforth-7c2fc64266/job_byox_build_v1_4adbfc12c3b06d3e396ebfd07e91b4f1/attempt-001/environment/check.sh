#!/bin/sh
set -eu

test "$(uname -m)" = "x86_64"
command -v as
command -v ld
command -v make
command -v python3
as --version | sed -n '1p'
ld --version | sed -n '1p'
python3 --version

