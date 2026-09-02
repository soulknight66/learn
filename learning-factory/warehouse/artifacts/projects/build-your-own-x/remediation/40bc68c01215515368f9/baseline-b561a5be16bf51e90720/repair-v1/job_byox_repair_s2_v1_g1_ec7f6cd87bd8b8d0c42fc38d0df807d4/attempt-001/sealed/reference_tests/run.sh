#!/bin/sh
set -eu

JDK_ROOT=${JDK_ROOT:-/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11}
BUILD_DIR=$(mktemp -d .mica-reference.XXXXXX)

cleanup() {
    case "$BUILD_DIR" in
        .mica-reference.*) rm -r -- "$BUILD_DIR" ;;
        *) echo "refusing to remove unexpected build directory: $BUILD_DIR" >&2 ;;
    esac
}
trap cleanup EXIT HUP INT TERM

if [ ! -x "$JDK_ROOT/bin/javac" ] || [ ! -x "$JDK_ROOT/bin/java" ]; then
    echo "JDK_ROOT does not contain java and javac: $JDK_ROOT" >&2
    exit 2
fi

"$JDK_ROOT/bin/javac" -Xlint:all -Werror -d "$BUILD_DIR" \
    sealed/reference/src/main/java/org/learningfactory/mica/*.java \
    sealed/reference_tests/src/test/java/org/learningfactory/mica/MicaReferenceTest.java
"$JDK_ROOT/bin/java" -ea -cp "$BUILD_DIR" org.learningfactory.mica.MicaReferenceTest
