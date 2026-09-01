# Sealed reference implementation

This directory contains the complete reference compiler and is not learner-
visible. It uses a hand-written scanner and recursive-descent parser, a separate
path-sensitive semantic pass, and a direct JVM class-file writer targeting major
version 49. It has no third-party dependencies.

Run the sealed suite from the repository root with
`./sealed/run-reference-tests.sh` on a Java 17+ JDK. Generation could not execute
that command because this host has no Java toolchain; see `VALIDATION.md`.

