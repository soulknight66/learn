# Repair validation evidence

Observed locally on 2026-09-02 in the allocated repair-generation-1 workspace. These are fresh
builder-controlled observations, not copied prior results and not independent validation.
`MANIFEST.yaml` remains `GENERATED` + `PARTIAL`; no `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is claimed.

The workspace shell printed non-fatal numeric user/group name lookup warnings before commands. They
did not come from the checked programs and did not change the recorded exit statuses.

## Toolchain identity

Commands:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -version
/usr/bin/timeout --version | /usr/bin/head -n 1
```

Observed, with all commands exiting 0:

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
javac 21.0.5
timeout (GNU coreutils) 8.30
```

## Starter compilation

Command:

```bash
build_dir=$(mktemp -d "$PWD/.mica-starter-check.XXXXXX"); cleanup() { case "$build_dir" in "$PWD"/.mica-starter-check.*) rm -r -- "$build_dir" ;; esac; }; trap cleanup EXIT HUP INT TERM; /usr/bin/timeout --signal=TERM --kill-after=5s 60s /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -Xlint:all -Werror -d "$build_dir" starter/src/main/java/org/learningfactory/mica/*.java
```

Observed: exit 0 with no `javac` output. The guarded trap removed the temporary directory. This only
shows that the intentionally unfinished learner scaffold compiles.

## Public suite against repaired sealed reference

Command:

```bash
/usr/bin/timeout --signal=TERM --kill-after=5s 60s env JDK_ROOT=/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 SOURCE_ROOT=sealed/reference ./public_tests/run.sh
```

Observed, exit 0:

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

## Repaired sealed reference suite

Command:

```bash
/usr/bin/timeout --signal=TERM --kill-after=5s 120s env JDK_ROOT=/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 ./sealed/reference_tests/run.sh
```

Observed, exit 0:

```text
PASS all punctuation and keyword tokens
PASS comments, newlines, and EOF location
PASS strings and lexical failures
PASS numeric underflow boundaries
PASS AST precedence shape
PASS right-associative assignment
PASS initializer and redeclaration scope rules
PASS value semantics and rendering
PASS dangling else and nearest assignment
PASS runtime diagnostic parity
PASS semantic execution limit parity
PASS dense bytecode execution limit parity
PASS compiler jump and tick invariants
PASS malformed bytecode matrix
PASS cyclic malformed bytecode limit
PASS reusable components reset state
PASS returned structures are immutable
PASS deterministic differential corpus
reference tests: 18 passed, 0 failed
```

The new deterministic regressions exercise both sides of the smallest-positive-`double` rounding
boundary, the independently reported 400-zero nonzero literal, a finite 6,000-iteration program whose
compiled execution exceeds one million total raw dispatches, a dense infinite loop requiring semantic
limit kind/location parity, and invalid unreachable opcode, operand, constant-index, jump-target, and
null entries. The differential corpus is deterministic enumeration, not fuzzing.

## Immutable metadata checks

Commands:

```bash
sha256sum PROVENANCE.json MANIFEST.yaml LICENSE_BOUNDARY.md
cmp -s PROVENANCE.json PRIOR_BUILD/PROVENANCE.json
cmp -s MANIFEST.yaml PRIOR_BUILD/MANIFEST.yaml
```

Observed hashes and comparison exits:

```text
e0e8c428ed45d321642af47fdb9537ac0cef6a7a4032dc3c89feaca85074b69b  PROVENANCE.json
1e60d1422c4c26fb753dcf853ddc720278fa67db3165de1e755d3c41c766eadd  MANIFEST.yaml
79edd7f308d73d9b891b0ee77db01322c28011d09329b6d266a386aeb7b42ca3  LICENSE_BOUNDARY.md
PROVENANCE.json comparison exit: 0
MANIFEST.yaml comparison exit: 0
```

The comparisons establish that the staged immutable metadata files were carried forward byte for
byte. They do not independently verify the unavailable external source snapshot or license evidence.

## Packaging, JSON, and credential audit

Commands, run after this validation record was finalized:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m json.tool PROVENANCE.json >/dev/null
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m json.tool MANIFEST.yaml >/dev/null
/usr/bin/timeout --signal=TERM --kill-after=5s 30s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
```

Observed: both JSON parse commands exited 0. The bounded audit exited 0 and printed:

```text
required regular files: PASS (23/23)
forbidden paths absent: PASS (21/21)
manifest exact object and provenance linkage: PASS
generated path types: PASS (64 regular files; no symlinks/special files)
credential signature scan: PASS (64 files, 5 patterns, 0 hits)
```

The credential scan covers canonical generated entries for private-key headers and common AWS,
OpenAI-style, GitHub, and bearer credential forms. The audit deliberately excludes factory metadata
and the read-only staged roots.

## Remaining gates and limitations

- No learner workspace or exported learner view was created: that is prohibited for this builder.
  Although the canonical learner-visible directories pass the local path audit, the full production
  pack physically contains `sealed/`. An orchestrator-controlled export validator must still prove
  sealed and review material are inaccessible before publication; `TRANSFER_VERIFIED` is not claimed.
- No network, upstream snapshot, or linked resource was available. Provenance and licensing statements
  were checked only for byte preservation and internal consistency.
- No fuzzing, benchmark, profiler, production, or independent acceptance validator was run.
