#!/bin/sh
set -eu

cc=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
python=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3

"$cc" --version | sed -n '1p'
"$python" --version
test -x /bin/sh
test -x /usr/bin/printf || test -x /bin/printf
printf '%s\n' 'environment prerequisites present'
