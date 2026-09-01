#!/bin/sh
set -eu

if ! command -v javac >/dev/null 2>&1; then
    echo "BLOCKED: javac is required (JDK 17+)" >&2
    exit 127
fi
if ! command -v java >/dev/null 2>&1; then
    echo "BLOCKED: java is required (JDK 17+)" >&2
    exit 127
fi

build_dir=$(mktemp -d "${TMPDIR:-/tmp}/sprig-reference.XXXXXX")
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM
mkdir -p "$build_dir/classes"

find sealed/reference/src/main/java sealed/reference_tests/src/test/java \
    -name '*.java' -type f -print | LC_ALL=C sort > "$build_dir/sources.txt"
javac --release 17 -Xlint:all -Werror -d "$build_dir/classes" \
    @"$build_dir/sources.txt"
java -ea -cp "$build_dir/classes" dev.learningfactory.sprig.ReferenceTestMain
