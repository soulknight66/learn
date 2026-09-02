# Independent validation evidence

Observed on 2026-09-02 in the allocated review workspace. `CANDIDATE/` was treated as immutable. All
review build directories were created beside it with guarded cleanup and were removed. Builder prose
and scripts were inspected but were not treated as proof; the commands below are fresh reviewer
observations. Exit codes are stated explicitly.

The shell printed the following non-fatal environment warning before many commands:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
```

It came from shell startup, not from the checked programs, and did not alter their exit codes.

## Toolchain identity

Commands:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -version
/usr/bin/timeout --version | /usr/bin/head -n 1
```

Observed, all exit 0:

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
javac 21.0.5
timeout (GNU coreutils) 8.30
```

These exact absolute Python and JDK paths were used for the checks below.

## Candidate integrity and packaging

Before any execution, this read-only digest command was run from the review workspace root:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import hashlib,pathlib; root=pathlib.Path("CANDIDATE"); h=hashlib.sha256(); files=sorted(p for p in root.rglob("*") if p.is_file()); [(h.update(p.relative_to(root).as_posix().encode()+b"\0"),h.update(p.read_bytes())) for p in files]; print(f"candidate_files={len(files)} tree_sha256={h.hexdigest()}")'
```

Observed, exit 0:

```text
candidate_files=64 tree_sha256=168b49a03a68644f49b46e3767d219746d0c3a852541b552e5d9cfa73b739ad5
```

The same command after all validation produced the same count and digest. The digest covers each
regular file's relative path and bytes. No candidate file was edited.

Metadata commands:

```bash
/usr/bin/sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml CANDIDATE/LICENSE_BOUNDARY.md
(cd CANDIDATE && /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m json.tool PROVENANCE.json >/dev/null)
(cd CANDIDATE && /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m json.tool MANIFEST.yaml >/dev/null)
```

Observed: both JSON parses exited 0. Hashes, which match the candidate's historical validation record:

```text
e0e8c428ed45d321642af47fdb9537ac0cef6a7a4032dc3c89feaca85074b69b  CANDIDATE/PROVENANCE.json
1e60d1422c4c26fb753dcf853ddc720278fa67db3165de1e755d3c41c766eadd  CANDIDATE/MANIFEST.yaml
79edd7f308d73d9b891b0ee77db01322c28011d09329b6d266a386aeb7b42ca3  CANDIDATE/LICENSE_BOUNDARY.md
```

An independent Python inventory using `Path.rglob`, `Path.is_file`, and `Path.is_symlink` observed:

```text
independent inventory: files=64 symlinks=0 special=0
learner-root solution-path leaks=0
```

The leak check looked for path components named `reference`, `reference_tests`, `hidden_tests`,
`solution`, `solutions`, `answers`, or `sealed` beneath `starter/`, `public_tests/`, and `environment/`.
This checks the canonical roots only; it is not a substitute for validating an exported learner view.

## Candidate audit

The audit source was read before execution. It uses the standard library, traverses fixed candidate
roots, and performs no network or external process operation.

Command, from `CANDIDATE/`:

```bash
/usr/bin/timeout --signal=TERM --kill-after=5s 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
```

Observed, exit 0:

```text
required regular files: PASS (23/23)
forbidden paths absent: PASS (21/21)
manifest exact object and provenance linkage: PASS
generated path types: PASS (64 regular files; no symlinks/special files)
credential signature scan: PASS (64 files, 5 patterns, 0 hits)
```

The five-pattern result is a bounded signature scan, not proof that arbitrary credentials are absent.

## Starter compilation

Command, from `CANDIDATE/` (the guarded trap removed the temporary directory):

```bash
review_build_dir=$(/usr/bin/mktemp -d "$PWD/../.review-starter.XXXXXX")
cleanup_review_build() {
  case "$review_build_dir" in
    "$PWD"/../.review-starter.*) /bin/rm -r -- "$review_build_dir" ;;
    *) /bin/echo "refusing cleanup: $review_build_dir" >&2 ;;
  esac
}
trap cleanup_review_build EXIT HUP INT TERM
/usr/bin/timeout --signal=TERM --kill-after=5s 60s \
  /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac \
  -Xlint:all -Werror -d "$review_build_dir" \
  starter/src/main/java/org/learningfactory/mica/*.java
```

Observed: exit 0 with no compiler output. This establishes only that the intentionally unfinished
scaffold compiles; its five core methods still deliberately throw `UnsupportedOperationException`.

## Supplied-runner constraint

After inspecting `public_tests/run.sh`, direct invocation was attempted from the immutable candidate:

```bash
/usr/bin/timeout --signal=TERM --kill-after=5s 60s \
  /usr/bin/env \
  JDK_ROOT=/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 \
  SOURCE_ROOT=sealed/reference ./public_tests/run.sh
```

Observed, exit 1 before compilation:

```text
mktemp: failed to create directory via template '.mica-public.XXXXXX': Read-only file system
```

Both supplied runners use a relative `.mica-*` template and therefore require a writable repository
root. Their compilation/execution steps were reproduced below in reviewer-owned directories. The
failed direct invocation is not counted as test evidence.

## Public suite against the sealed reference

The inspected runner's `javac` and `java` argv were reproduced from the review workspace root:

```bash
review_build_dir=$(/usr/bin/mktemp -d "$PWD/.review-public.XXXXXX")
trap 'case "$review_build_dir" in "$PWD"/.review-public.*) /bin/rm -r -- "$review_build_dir" ;; esac' EXIT HUP INT TERM
/usr/bin/timeout --signal=TERM --kill-after=5s 60s \
  /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac \
  -Xlint:all -Werror -d "$review_build_dir" \
  CANDIDATE/sealed/reference/src/main/java/org/learningfactory/mica/*.java \
  CANDIDATE/public_tests/src/test/java/org/learningfactory/mica/MicaPublicTest.java
/usr/bin/timeout --signal=TERM --kill-after=5s 60s \
  /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java \
  -ea -cp "$review_build_dir" org.learningfactory.mica.MicaPublicTest
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

## Sealed reference suite

Command shape was identical to the public check, using a fresh `.review-reference.*` directory and:

```bash
/usr/bin/timeout --signal=TERM --kill-after=5s 60s \
  /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac \
  -Xlint:all -Werror -d "$review_build_dir" \
  CANDIDATE/sealed/reference/src/main/java/org/learningfactory/mica/*.java \
  CANDIDATE/sealed/reference_tests/src/test/java/org/learningfactory/mica/MicaReferenceTest.java
/usr/bin/timeout --signal=TERM --kill-after=5s 120s \
  /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java \
  -ea -cp "$review_build_dir" org.learningfactory.mica.MicaReferenceTest
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

These are fresh observations of candidate-authored tests; they do not alone confer a validation label.

## Reviewer-authored source-language probes

The reference was compiled cleanly into a fresh directory. A bounded Python 3.11.5 harness invoked
each engine in a separate Java process with this exact argv and a 15-second per-process timeout:

```python
[java, "-cp", review_build_dir, "org.learningfactory.mica.Main",
 f"--engine={engine}", "-e", source]
```

The complete reviewer case table was:

| Case | Source/condition | Expected |
|---|---|---|
| empty program | empty string | success, no output |
| scope and initializer ordering | `let x = 10; { let x = x + 1; print x; } print x;` | `11`, `10` |
| nearest dangling else | `if (true) if (false) print 1; else print 2; else print 3;` | `2` |
| short-circuit side effect | `let x = false; print x or (x = true); print x;` | `true`, `true` |
| exact budget | loop body executes 99,997 times, then prints | success at exactly 100,000 statements |
| over budget | loop body executes 99,998 times, then tries to print | `LIMIT` on statement 100,001 |
| logical type | `print 1 and true;` | `RUNTIME` |
| signed-zero division | `print 1 / -0;` | `RUNTIME` |
| ASCII identifier boundary | `let é = 1;` | `LEX` |
| invalid escape | `print "x\q";` | `LEX` |

The harness required identical output for successes and identical kind/line/column for failures.
Observed, outer command exit 0:

```text
PASS empty program: engine parity and expected output
PASS scope and initializer ordering: engine parity and expected output
PASS nearest dangling else: engine parity and expected output
PASS short-circuit side effect: engine parity and expected output
PASS exact 100000-statement budget: engine parity and expected output
PASS budget rejects statement 100001: LIMIT at 1:41 on both engines
PASS logical operands require booleans: RUNTIME at 1:9 on both engines
PASS negative-zero divisor: RUNTIME at 1:9 on both engines
PASS non-ASCII identifier rejected: LEX at 1:5 on both engines
PASS invalid string escape rejected: LEX at 1:9 on both engines
reviewer semantic probes: 10 passed, 0 failed
```

## Reviewer-authored malformed-bytecode probes

A temporary `ReviewerBytecodeProbe.java` was created outside `CANDIDATE/`, compiled with the reference,
executed, and deleted. It constructed only public `BytecodeProgram`/`Instruction` values and asserted
the following exact outcomes:

| Program defect | Required result |
|---|---|
| `HALT` followed by unreachable `CONSTANT 9` with one constant | `RUNTIME` at `7:8` |
| `HALT` followed by an unreachable null instruction | `RUNTIME` at `1:1` |
| valid `HALT` with an unreferenced boolean constant | `RUNTIME` at `1:1` |
| single `JUMP 1` in a one-instruction program | `RUNTIME` at `3:4` |
| single `JUMP 0` without `TICK` | `LIMIT` at `5:6` |

Commands:

```bash
/usr/bin/timeout --signal=TERM --kill-after=5s 60s \
  /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac \
  -Xlint:all -Werror -d "$review_build_dir" \
  CANDIDATE/sealed/reference/src/main/java/org/learningfactory/mica/*.java \
  ReviewerBytecodeProbe.java
/usr/bin/timeout --signal=TERM --kill-after=5s 30s \
  /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java \
  -ea -cp "$review_build_dir" ReviewerBytecodeProbe
```

Observed, exit 0:

```text
PASS unreachable invalid constant index: RUNTIME at 7:8
PASS unreachable null instruction: RUNTIME at 1:1
PASS unreferenced invalid constant: RUNTIME at 1:1
PASS jump target equals code size: RUNTIME at 3:4
PASS tick-free bytecode cycle: LIMIT at 5:6
reviewer bytecode probes: 5 passed, 0 failed
```

## Clean-build reproducibility

The reference plus both test classes were compiled twice into two independent empty directories with
the exact configured `javac -Xlint:all -Werror`. A Python 3.11.5 script sorted each relative `.class`
path and hashed the path, a NUL separator, and the class bytes.

Observed, exit 0:

```text
compile A: class_files=47 sha256=d92d928ded6e400d572133dfe5382c8a8a181d90ae7bbac073b49ead96d39c9a
compile B: class_files=47 sha256=d92d928ded6e400d572133dfe5382c8a8a181d90ae7bbac073b49ead96d39c9a
byte-for-byte reproducible=True
```

This is reproducibility on the configured JDK and host; it is not a cross-JDK reproducibility claim.

## Static review observations

- All 64 files were read or inspected, including both runners, the audit, both suites, starter sources,
  reference sources, requirements, design/review material, manifest, and provenance record.
- The only source-level filesystem access found was `Files.readString(Path.of(input), UTF_8)` in the
  CLI in both starter and reference. No Mica language operation exposes it. This boundary is disclosed.
- No `ProcessBuilder`, `Runtime.getRuntime`, reflection, or Java network API use was found. The only URL
  text outside historical validation was the provenance citation.
- Ten `TODO(student)` occurrences resolve to comments and deliberate throws in exactly the five core
  files named by `starter/README.md`.
- Public material contains examples and test expectations, while complete implementation and extended
  tests remain under the physically separate sealed tree.
- The validation labels are exactly `GENERATED` and `PARTIAL`; `productionized` is false and independent
  validation is required. No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
  `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is present.

## Limitations and inconclusive checks

- The immutable upstream source snapshot, network, `PRIOR_BUILD`, and external license evidence were
  unavailable. Present-file hashes and cross-field consistency do not prove historical provenance,
  no-copy assertions, upstream license terms, or byte identity to the prior build.
- No exported learner view was provided. The full candidate physically includes `sealed/`, so only an
  orchestrator-controlled export/transfer check can establish learner isolation.
- No fuzzing, benchmark, mutation test, profiler, production deployment, or acceptance-label validator
  was run. Candidate documents explicitly avoid those claims.
- Deep recursion and allocation exhaustion were not stress-tested. Candidate review material already
  identifies those host-resource boundaries and does not claim production safety.
- `rg` and `git` were not available on this workspace's restricted `PATH`; bounded `find`, `grep`, and
  Python traversal were used instead.
- A JShell probe using its default execution engine was inconclusive because sandbox policy prohibited
  its loopback socket. A local JShell fallback could not load the temporary classpath. Neither attempt
  is counted as evidence; the same malformed-bytecode cases were subsequently compiled and run as the
  temporary Java probe above. JShell's generated preference-only directory was inspected and removed.
