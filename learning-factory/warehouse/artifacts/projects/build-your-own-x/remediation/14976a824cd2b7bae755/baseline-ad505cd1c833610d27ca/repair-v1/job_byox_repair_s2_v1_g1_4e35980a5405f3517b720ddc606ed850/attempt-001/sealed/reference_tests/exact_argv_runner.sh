#!/usr/bin/env bash
set -eu

[ "$#" -eq 7 ] || exit 91
[ -d "$1" ] || exit 92
[ "$2" = argvcase ] || exit 93
[ "$3" = /bin/tool ] || exit 94
[ "$4" = 'two words' ] || exit 95
[ "$5" = '*' ] || exit 96
[ "$6" = 'semi;colon' ] || exit 97
[ -z "$7" ] || exit 98
exit 0
