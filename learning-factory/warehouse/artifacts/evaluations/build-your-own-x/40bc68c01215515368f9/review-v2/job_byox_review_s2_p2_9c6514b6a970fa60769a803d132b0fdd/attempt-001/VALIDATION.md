# Independent validation record

Date: 2026-09-02  
Workspace: /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_s2_p2_9c6514b6a970fa60769a803d132b0fdd/attempt-001  
Advisory result: **REVISE**

These are reviewer observations. They do not edit the candidate manifest, award REVIEWED, or promote
any BUILDS, TESTED, FUZZED, BENCHMARKED, TRANSFER_VERIFIED, or PRODUCTIONIZED label.

## Candidate immutability and inventory

The candidate contained 64 regular files. It was mounted read-only. Before and after all checks:

~~~bash
find CANDIDATE -type f -print0 |
  LC_ALL=C sort -z |
  xargs -0 sha256sum |
  sha256sum
~~~

Observed both times:

~~~text
d4df8869e21fb0eb2568acbb5a88ca610f4544afa2c2defa5bcb44abb4a82faa  -
~~~

The supplied runners create temporary build directories below their current directory. They were
therefore run under external timeouts in a scratch replica outside CANDIDATE. The first replica
preserved the submitted read-only modes and failed at mktemp with Permission denied; it was removed.
Only the subsequent scratch replica was made writable. No submitted file changed.

## Toolchains

Commands:

~~~bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -version
/usr/bin/timeout --version | head -n 1
~~~

Observed:

~~~text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
javac 21.0.5
timeout (GNU coreutils) 8.30
~~~

Both configured toolchains were available. ripgrep was unavailable, so inventory and text searches
used find, grep, and standard utilities.

## Structure, JSON, provenance linkage, and credential audit

Commands:

~~~bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m json.tool \
  CANDIDATE/PROVENANCE.json >/dev/null
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m json.tool \
  CANDIDATE/MANIFEST.yaml >/dev/null
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/audit.py
sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml \
  CANDIDATE/LICENSE_BOUNDARY.md
~~~

The two parse commands exited 0. Audit output:

~~~text
required regular files: PASS (23/23)
forbidden paths absent: PASS (21/21)
manifest exact object and provenance linkage: PASS
generated path types: PASS (64 regular files; no symlinks/special files)
credential signature scan: PASS (64 files, 5 patterns, 0 hits)
~~~

File hashes:

~~~text
e0e8c428ed45d321642af47fdb9537ac0cef6a7a4032dc3c89feaca85074b69b  CANDIDATE/PROVENANCE.json
1e60d1422c4c26fb753dcf853ddc720278fa67db3165de1e755d3c41c766eadd  CANDIDATE/MANIFEST.yaml
79edd7f308d73d9b891b0ee77db01322c28011d09329b6d266a386aeb7b42ca3  CANDIDATE/LICENSE_BOUNDARY.md
~~~

The audit proves its stated local checks. Its manifest object and expected identifiers are embedded in
the same builder-authored script, and the immutable source snapshot was unavailable; this is internal
consistency evidence, not independent upstream provenance proof.

## Compilation and supplied suites

Core scratch-replica commands:

~~~bash
review_run_dir=$(mktemp -d "$PWD/.review-run.XXXXXX")
cp -R -- CANDIDATE "$review_run_dir/candidate"
chmod -R u+w "$review_run_dir/candidate"
cd "$review_run_dir/candidate"

starter_build_dir=$(mktemp -d "$review_run_dir/.review-starter.XXXXXX")
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac \
  -Xlint:all -Werror -d "$starter_build_dir" \
  starter/src/main/java/org/learningfactory/mica/*.java

/usr/bin/timeout --signal=TERM --kill-after=5s 60s env \
  JDK_ROOT=/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 \
  SOURCE_ROOT=sealed/reference ./public_tests/run.sh

/usr/bin/timeout --signal=TERM --kill-after=5s 90s env \
  JDK_ROOT=/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 \
  ./sealed/reference_tests/run.sh

/usr/bin/timeout --signal=TERM --kill-after=5s 60s env \
  JDK_ROOT=/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 \
  SOURCE_ROOT=starter ./public_tests/run.sh
~~~

Observed:

- Starter compilation: exit 0, no compiler output.
- Public suite against sealed/reference: exit 0, 9 passed and 0 failed.
- Sealed reference suite: exit 0, 16 passed and 0 failed.
- Public suite against starter: exit 1, 0 passed and 9 failed; every failure was an explicit
  TODO(student) UnsupportedOperationException. This is the disclosed scaffold baseline, not a
  regression.
- Each runner cleaned its .mica-* build directory in the scratch replica.

The supplied suites are builder-authored. Their passing results reproduce the transcript but are not,
on their own, proof of the stronger labels excluded above.

## Independent contract probes

A temporary reviewer-authored Java harness had SHA-256
e114c05ab6ac18c5c778ed64975e56561661a5109001d93d416a87fa6e001ed3 and was removed after use.
It compiled the submitted sealed reference directly. Its essential inputs were:

~~~java
String tiny = "0." + "0".repeat(400) + "1";
String sum = String.join(" + ", Collections.nCopies(100, "1"));
String infinite = "let sentinel = 0;\nwhile (true) {\n" + sum + ";\n}";
String finite = "let i = 0;\nwhile (i < 6000) {\n" + sum
        + ";\ni = i + 1;\n}\nprint i;";
List<Instruction> malformed = new ArrayList<>();
malformed.add(new Instruction(OpCode.HALT, null, 7, 8));
malformed.add(null);
~~~

Compile/run commands:

~~~bash
probe_build_dir=$(mktemp -d "$PWD/.probe-build.XXXXXX")
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac \
  -Xlint:all -Werror -d "$probe_build_dir" \
  CANDIDATE/sealed/reference/src/main/java/org/learningfactory/mica/*.java \
  review_probe/IndependentMicaProbe.java
/usr/bin/timeout --signal=TERM --kill-after=5s 60s \
  /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java \
  -ea -cp "$probe_build_dir" org.learningfactory.mica.IndependentMicaProbe
~~~

Observed, exit 0:

~~~text
UNDERFLOW_LITERAL=ACCEPTED literal=0.0
BUDGET_TREE=ERROR LIMIT 2:14 execution limit of 100000 statements exceeded
BUDGET_VM=ERROR LIMIT 3:267 raw instruction limit of 1000000 exceeded
FINITE_RAW_GUARD_TREE=OK [6000]
FINITE_RAW_GUARD_VM=ERROR LIMIT 3:247 raw instruction limit of 1000000 exceeded
UNREACHABLE_NULL=ACCEPTED []
INDEPENDENT_PROBE_EXIT=0
~~~

The harness exit code means the probes completed within the bound; the ACCEPTED and engine-divergence
lines are negative correctness evidence.

## CLI spot checks

The sealed reference was compiled with the same javac flags, then each invocation was bounded by
/usr/bin/timeout 10s:

~~~text
Main --engine=tree -e 'print 1 + 2;'  -> stdout 3, exit 0
Main --engine=vm   -e 'print 1 + 2;'  -> stdout 3, exit 0
Main -e 'print ;'                     -> [PARSE 1:7] expected expression, exit 65
Main -e 'print 1 / 0;'                -> [RUNTIME 1:9] division by zero, exit 70
Main                                  -> usage diagnostic, exit 64
~~~

## Disclosure, dependencies, and unavailable checks

- Manual import inspection found only Java standard-library dependencies.
- Learner-facing documentation is ordered and useful, and solution-bearing material is grouped below
  sealed/. No independently materialized learner export was available, so actual exclusion of sealed/
  is inconclusive.
- The boundary consistently records the linked resource as NOASSERTION and declares that no linked
  content was copied. Network access, the immutable catalog baseline, and the upstream license evidence
  were unavailable, so those external assertions were not verified.
- No fuzzing, benchmark, profiler, transfer test, production test, or orchestrator-controlled
  acceptance validator was run. The candidate does not claim those results.
