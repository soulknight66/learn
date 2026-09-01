#!/usr/bin/env bash

state=${MINICTR_HOME:-/tmp/minictr}

create() {
    name=$1
    rootfs=$2
    dir=$state/containers/$name
    if [ -e $dir ]; then
        echo already exists
        return
    fi
    mkdir -p $dir
    echo $rootfs >$dir/rootfs
}

run() {
    name=$1
    shift
    rootfs=$(cat $state/containers/$name/rootfs)
    command="$*"
    eval "unshare -m chroot $rootfs $command"
    echo CREATED >$state/containers/$name/status
}

delete() {
    rm -rf "$state/containers/$1"
}

"$@"

