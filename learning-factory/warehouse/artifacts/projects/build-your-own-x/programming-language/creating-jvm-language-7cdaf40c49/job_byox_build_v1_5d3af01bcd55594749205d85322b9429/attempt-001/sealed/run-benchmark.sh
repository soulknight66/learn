#!/bin/sh
set -eu

if ! command -v javac >/dev/null 2>&1 || ! command -v java >/dev/null 2>&1; then
    echo "BLOCKED: java and javac are required (JDK 17+)" >&2
    exit 127
fi

build_dir=$(mktemp -d "${TMPDIR:-/tmp}/sprig-benchmark.XXXXXX")
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM
mkdir -p "$build_dir/classes"
find sealed/reference/src/main/java benchmarks/src -name '*.java' -type f -print \
    | LC_ALL=C sort > "$build_dir/sources.txt"
javac --release 17 -Xlint:all -Werror -d "$build_dir/classes" \
    @"$build_dir/sources.txt"
java -cp "$build_dir/classes" dev.learningfactory.sprig.BenchmarkMain
