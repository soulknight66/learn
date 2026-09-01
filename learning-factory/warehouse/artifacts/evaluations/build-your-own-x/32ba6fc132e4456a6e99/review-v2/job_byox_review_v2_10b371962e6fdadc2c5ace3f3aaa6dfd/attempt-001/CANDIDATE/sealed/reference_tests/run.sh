#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
BUILD_DIRECTORY=$(mktemp -d "${TMPDIR:-/tmp}/kafkalite-reference-tests.XXXXXX")

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
