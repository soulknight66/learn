# Validation record

## Outcome

Status remains `GENERATED` + `PARTIAL`. The artifact has a complete starter, public contract suite,
sealed reference implementation, sealed reference suite, and deterministic structural verifier.
Compilation and test execution were attempted on the generation host but could not start because no
Java runtime or compiler is installed. No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is claimed; independent validators control those
labels.

Validation was performed from the repository root on 2026-08-31.

## Java toolchain discovery

Command:

```sh
java -version
```

Observed exit code: `127`

```text
bash: java: command not found
```

Command:

```sh
javac -version
```

Observed exit code: `127`

```text
bash: javac: command not found
```

Additional discovery command:

```sh
for candidate in /usr/lib/jvm/*/bin/javac /opt/java/*/bin/javac /opt/jdk*/bin/javac; do
    if [ -x "$candidate" ]; then printf '%s\n' "$candidate"; fi
done
```

Observed exit code: `0`; observed output: empty. Standard installation locations under
`/usr/lib/jvm` and `/opt` therefore exposed no executable `javac`. No compiler was downloaded and no
network or unrecorded dependency was used.

## Build and test attempts

Public starter contract command:

```sh
sh public_tests/run.sh
```

Observed exit code: `127`

```text
public_tests/run.sh: line 13: javac: command not found
```

Sealed reference-suite command:

```sh
sh sealed/reference_tests/run.sh
```

Observed exit code: `127`

```text
sealed/reference_tests/run.sh: line 13: javac: command not found
```

Both runners create a unique temporary build directory and register cleanup before invoking `javac`;
their failed attempts left no class files in the artifact.

## Checks supported by this host

Shell parsing:

```sh
sh -n public_tests/run.sh
sh -n sealed/reference_tests/run.sh
```

Each command exited `0` with no output.

Artifact structure, strict JSON fingerprints, labels, entry types, credential signatures, forbidden
generated paths, and archived Java build products are checked with:

```sh
python3 sealed/validation/verify_artifact.py
```

Observed exit code: `0`

```text
PASS required regular files: 23
PASS forbidden generated artifact paths: 0
PASS artifact entry types: regular files/directories only
PASS strict manifest/provenance object fingerprints
PASS status and labels: GENERATED + PARTIAL
PASS high-confidence credential scan: 0 hits
PASS archived Java build products: 0
PASS Java lexical structure: 8 source files
NOTE pre-existing read-only factory control .git excluded from artifact scan
```

## Static review performed

- Starter and sealed classes expose matching Java package, class, required constructor, and required
  method signatures.
- Public and sealed test sources were inspected for Java 17 syntax, overload resolution, method
  references, expected exception types, and contract consistency.
- Reference transitions were traced for successful/rejected append, repeated follower and leader
  loss, all-down recovery, stale-first recovery, catch-up, and deterministic election.
- Learner-facing source contains only API skeletons and contract examples; implementation and answer
  material is confined to the designated sealed locations.
- Java imports are standard-library-only. No JAR, class file, native binary, dependency cache,
  benchmark number, profiler output, or production-readiness claim was generated.

These are static inspections, not substitutes for compilation or executed tests.

## Required independent validation

On a host with JDK 17 or newer, run the structural verifier, the public command, and the sealed
reference command shown above. A validator should additionally exercise defensive-copy attacks,
invalid-operation atomicity, long state-machine traces, stale-first recovery, integer/offset
boundaries, and any concurrency guarantee it elects to assess. Preserve raw output and let the
orchestrator assign any earned labels.

The allocated workspace contains a pre-existing read-only `.git` factory-control directory (as well
as other control entries). It was not created or modified by this job and is excluded from the
generated artifact/forbidden-path scan; no generated `.git` path exists in the archive payload.
