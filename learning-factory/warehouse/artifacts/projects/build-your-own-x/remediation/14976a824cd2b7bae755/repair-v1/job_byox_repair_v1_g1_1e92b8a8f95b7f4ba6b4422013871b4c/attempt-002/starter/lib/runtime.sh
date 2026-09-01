#!/usr/bin/env bash
# Durable control-plane functions for MiniCTR.
#
# This file is sourced by ../minictr. The four public functions below are the
# intended learner work surface. Keep state beneath MINICTR_HOME and treat all
# metadata as data, never as shell code.

minictr_runtime_todo() {
    local operation=$1
    minictr_die 70 "TODO: implement $operation"
}

minictr_runtime_create() {
    local name=$1
    local rootfs=$2
    : "$name" "$rootfs"

    # TODO: atomically register the canonical rootfs for this name.
    minictr_runtime_todo create
}

minictr_runtime_run() {
    local name=$1
    shift
    local -a command_argv=("$@")
    : "$name" "${command_argv[@]}"

    # TODO: claim the idle instance, invoke MINICTR_ISOLATOR (or the default
    # isolate.sh) with rootfs + command_argv, then clean up and return its status.
    minictr_runtime_todo run
}

minictr_runtime_ps() {
    # TODO: print the required header and one C-locale-sorted row per instance.
    minictr_runtime_todo ps
}

minictr_runtime_delete() {
    local name=$1
    : "$name"

    # TODO: serialize with run and remove only an idle registration.
    minictr_runtime_todo delete
}
