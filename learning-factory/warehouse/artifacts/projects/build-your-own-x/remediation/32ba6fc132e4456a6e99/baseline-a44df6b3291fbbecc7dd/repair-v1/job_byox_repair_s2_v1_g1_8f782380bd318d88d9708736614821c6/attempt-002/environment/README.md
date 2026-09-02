# Reproducible environment

The project requires Java 21 and Python 3 only for the convenience test runner.
It has no network, package-manager, database, or service dependency.

Validated toolchain locations for this generated artifact:

- Java home: `/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11`
- Python: `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`

`run_public_tests.py` invokes `javac` and `java` with argument arrays, captures
their output, applies 60-second timeouts, and compiles into an automatically
removed scratch directory. Each child starts in a new process group; a timeout
terminates that group, including descendants. Override `--java-home` to use
another Java 21 JDK.

The runner does not rely on Python's host-default temporary directory. By
default it tries `.minilog-runner-tmp` first in the repository and then in the
repository's parent, removing what it creates. Use
`--temp-root <writable-directory>` to choose the scratch parent explicitly.

No toolchain root is placed on `PATH`. See `VALIDATION.md` for exact observed
versions and results from artifact generation.
