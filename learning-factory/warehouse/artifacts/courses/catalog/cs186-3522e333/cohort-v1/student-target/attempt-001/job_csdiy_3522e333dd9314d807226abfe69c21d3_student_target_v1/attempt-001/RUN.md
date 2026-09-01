# Build and Run

Run the following block from the repository root. It requires JDK 8 or newer with `javac` and `java`
on `PATH`. It uses only POSIX shell utilities and the JDK, cleans the bounded class-output directory,
compiles production and test sources together, runs the test main, displays its output, and preserves
the first failing command's status. Build and test standard output and standard error are captured in
`test-output.txt`, including a missing-toolchain failure.

```sh
test_status=0
sh <<'SH' > test-output.txt 2>&1 || test_status=$?
set -eu

printf 'PROVENANCE=RUN.md clean build/test command\n'
printf 'VALIDATION_LABEL=LEARNER_GENERATED_UNVALIDATED\n'

if [ ! -d src/main/java ] || [ ! -d src/test/java ]; then
    echo "run this command from the repository root" >&2
    exit 1
fi

rm -rf build/classes
mkdir -p build/classes

find src/main/java src/test/java -type f -name '*.java' -print \
    | LC_ALL=C sort > build/sources.list

if [ ! -s build/sources.list ]; then
    echo "no Java sources found" >&2
    exit 1
fi

javac -d build/classes @build/sources.list
java -cp build/classes edu.learningfactory.relational.RelationalPipelineTest
SH
printf 'COMMAND_EXIT_STATUS=%s\n' "$test_status" >> test-output.txt
cat test-output.txt
exit "$test_status"
```

No Maven, Gradle, downloaded dependency, network access, or shell-specific `pipefail` behavior is
assumed. `build/classes` and `build/sources.list` are scratch products; the source trees and submitted
documents are not removed by the clean step.

The output file records the exact local build/test attempt. Its presence is not evidence that tests
passed or that an evaluator validated the unit; interpret it together with the exit status and final
`SUMMARY` line, which appears only when the test main ran to completion.
