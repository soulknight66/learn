#!/bin/sh
set -eu

JDK_ROOT=${JDK_ROOT:-/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11}
SOURCE_ROOT=${SOURCE_ROOT:-starter}
BUILD_DIR=$(mktemp -d .mica-public.XXXXXX)

cleanup() {
    case "$BUILD_DIR" in
        .mica-public.*) rm -r -- "$BUILD_DIR" ;;
        *) echo "refusing to remove unexpected build directory: $BUILD_DIR" >&2 ;;
    esac
}
trap cleanup EXIT HUP INT TERM

if [ ! -x "$JDK_ROOT/bin/javac" ] || [ ! -x "$JDK_ROOT/bin/java" ]; then
    echo "JDK_ROOT does not contain java and javac: $JDK_ROOT" >&2
    exit 2
fi
if [ ! -d "$SOURCE_ROOT/src/main/java/org/learningfactory/mica" ]; then
    echo "invalid SOURCE_ROOT: $SOURCE_ROOT" >&2
    exit 2
fi

"$JDK_ROOT/bin/javac" -Xlint:all -Werror -d "$BUILD_DIR" \
    "$SOURCE_ROOT"/src/main/java/org/learningfactory/mica/*.java \
    public_tests/src/test/java/org/learningfactory/mica/MicaPublicTest.java
"$JDK_ROOT/bin/java" -ea -cp "$BUILD_DIR" org.learningfactory.mica.MicaPublicTest
