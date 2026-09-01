#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)

if [ -n "${TMPDIR:-}" ]; then
    TEMPORARY_PARENT=$TMPDIR
elif [ -d /tmp ] && [ -w /tmp ]; then
    TEMPORARY_PARENT=/tmp
elif [ -w "$REPOSITORY_ROOT" ]; then
    TEMPORARY_PARENT=$REPOSITORY_ROOT
else
    printf '%s\n' 'No writable temporary directory; set TMPDIR to an existing writable directory.' >&2
    exit 1
fi

if [ ! -d "$TEMPORARY_PARENT" ] || [ ! -w "$TEMPORARY_PARENT" ]; then
    printf 'TMPDIR is not an existing writable directory: %s\n' "$TEMPORARY_PARENT" >&2
    exit 1
fi

BUILD_DIRECTORY=$(mktemp -d "$TEMPORARY_PARENT/kafkalite-reference-tests.XXXXXX")

cleanup() {
    rm -rf -- "$BUILD_DIRECTORY"
}
trap cleanup EXIT HUP INT TERM

javac --release 17 -Xlint:all -Werror \
    -d "$BUILD_DIRECTORY" \
    "$REPOSITORY_ROOT/sealed/reference/src/main/java/io/learningfactory/kafkalite/LogRecord.java" \
    "$REPOSITORY_ROOT/sealed/reference/src/main/java/io/learningfactory/kafkalite/PartitionLog.java" \
    "$REPOSITORY_ROOT/sealed/reference/src/main/java/io/learningfactory/kafkalite/ReplicatedPartition.java" \
    "$REPOSITORY_ROOT/public_tests/src/io/learningfactory/kafkalite/ContractTests.java" \
    "$REPOSITORY_ROOT/sealed/reference_tests/src/io/learningfactory/kafkalite/ReferenceTests.java"

java -cp "$BUILD_DIRECTORY" io.learningfactory.kafkalite.ContractTests
java -cp "$BUILD_DIRECTORY" io.learningfactory.kafkalite.ReferenceTests
