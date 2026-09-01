#!/usr/bin/env bash

run_one() {
    entry=$1
    shift
    run_file=$entry/run

    echo $$ >"$run_file"
    trap 'rm -f "$run_file"' EXIT INT TERM
    "$MINICTR_ISOLATOR" "$(cat "$entry/rootfs")" "$@"
    rm -f "$run_file"
}

is_running() {
    pid=$(cat "$1/run")
    kill -0 "$pid" 2>/dev/null
}

