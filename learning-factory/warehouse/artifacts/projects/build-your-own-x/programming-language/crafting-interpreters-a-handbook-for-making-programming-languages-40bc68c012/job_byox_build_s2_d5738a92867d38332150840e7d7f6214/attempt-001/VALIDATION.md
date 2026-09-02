# Validation evidence

Observed locally on 2026-09-02 in the allocated workspace. These are worker observations, not
independent validation. `MANIFEST.yaml` remains `GENERATED` + `PARTIAL`; no `BUILDS`, `TESTED`,
`FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is claimed.

## Toolchain identity

Commands:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -version
```

Observed:

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
javac 21.0.5
```

## Starter compilation

Command (the trap limits cleanup to the freshly created build directory):

```bash
build_dir=$(mktemp -d .mica-starter.XXXXXX); cleanup() { case "$build_dir" in .mica-starter.*) rm -r -- "$build_dir" ;; esac; }; trap cleanup EXIT HUP INT TERM; /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -Xlint:all -Werror -d "$build_dir" starter/src/main/java/org/learningfactory/mica/*.java
```

Observed: exit 0, no compiler output. This verifies that the intentionally incomplete scaffold
compiles; it does not claim that its TODOs pass tests.

## Public suite against the sealed reference

Command:

```bash
SOURCE_ROOT=sealed/reference JDK_ROOT=/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 public_tests/run.sh
```

Observed (exit 0):

```text
PASS scanner locations and escapes
PASS operator precedence on both engines
PASS lexical shadowing
PASS loop, assignment, and branch
PASS short circuit
PASS phase and source diagnostics
PASS bytecode is substantive
PASS malformed bytecode is controlled
PASS returned output is immutable
public tests: 9 passed, 0 failed
```

## Sealed reference suite

Command:

```bash
JDK_ROOT=/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 sealed/reference_tests/run.sh
```

Observed (exit 0):

```text
PASS all punctuation and keyword tokens
PASS comments, newlines, and EOF location
PASS strings and lexical failures
PASS AST precedence shape
PASS right-associative assignment
PASS initializer and redeclaration scope rules
PASS value semantics and rendering
PASS dangling else and nearest assignment
PASS runtime diagnostic parity
PASS semantic execution limit parity
PASS compiler jump and tick invariants
PASS malformed bytecode matrix
PASS cyclic malformed bytecode limit
PASS reusable components reset state
PASS returned structures are immutable
PASS deterministic differential corpus
reference tests: 16 passed, 0 failed
```

The differential corpus is deterministic enumeration, not fuzzing. No benchmark or profiler was run.

## Packaging, JSON, and credential audit

Command:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
```

Observed (exit 0 before this evidence-only edit; file count unchanged):

```text
required regular files: PASS (23/23)
forbidden paths absent: PASS (21/21)
manifest exact object and provenance linkage: PASS
generated path types: PASS (64 regular files; no symlinks/special files)
credential signature scan: PASS (64 files, 5 patterns, 0 hits)
```

The credential scan covers generated files only and looks for private-key headers and common AWS,
OpenAI-style, GitHub, and bearer-token signatures. It intentionally does not traverse factory-owned
hidden metadata.

## Informative failed attempt

The first public-suite launch used `/tmp/mica-public.XXXXXX`; `mktemp` reported `No such file or
directory` before compilation. Both runners were changed to validated temporary directories beneath
the repository root. The passing runs above used the revised runners, and their cleanup left no
`.mica-*` directory in the workspace.
