# Repair-generation 2 validation evidence

These are fresh local observations from repair generation 2 on 2026-09-02
(America/Chicago). They are builder-owned evidence, not independent promotion
evidence. `MANIFEST.yaml` remains `GENERATED` + `PARTIAL`, `productionized`
remains false, and independent validation remains required.

All commands ran from the challenge-pack root. The configured toolchain roots
were invoked by absolute path and were not added to `PATH`. Repeated
`/usr/bin/id: cannot find name for user/group ID` messages were environment
noise and did not change the command exit codes recorded below.

## Exact toolchains

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -version
```

Each command exited `0`. Observed versions were:

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
javac 21.0.5
```

## Progressive starter and codec checkpoint

A diagnostic invocation with Python isolated mode was attempted first:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B environment/run_public_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

It exited `1` before compilation with `ModuleNotFoundError: No module named
'process_runner'`: `-I` intentionally removes the runner's sibling import path.
The documented non-isolated runner command was then run exactly:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/run_public_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

The wrapper exited `1` after `javac` exited `0`, which is the transparent
baseline for the deliberately incomplete starter:

```text
PASS record defensive copies
FAIL codec round trip and boundary -> UnsupportedOperationException: TODO milestone 2: encode a checked frame
FAIL segmented log round trip -> UnsupportedOperationException: TODO milestone 3: open and recover segments
FAIL election term and freshness -> UnsupportedOperationException: TODO milestone 4: implement voting rules
FAIL majority high watermark -> UnsupportedOperationException: TODO milestone 5: initialize replica state
FAIL partition read isolation -> UnsupportedOperationException: TODO milestone 3: open and recover segments
RESULT 1/6 passed
```

The new codec case therefore supplies direct milestone-2 feedback without
requiring the segmented-log milestone. This expected non-passing run is not a
passing-suite claim. Its scratch root was removed by the runner.

## Sealed reference and atomicity regression

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B sealed/run_reference_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

Observed exit code: `0`. The configured `javac` exited `0`; the manual
benchmark source compiled but the benchmark was not run. The Java mains ended
with:

```text
PublicTestMain:    RESULT 6/6 passed
ReferenceTestMain: RESULT 15/15 passed
```

The final sealed case printed `PASS partition ownership and validation are
atomic`. It constructs a misaligned log/tracker pair and compares both end
offsets and segment bytes after constructor rejection. It then constructs an
aligned partition, attempts direct mutations through retained log and tracker
aliases, and again compares both end offsets and segment bytes before testing
term and payload rejection. This specifically covers the independently
reported durable partial-mutation path.

## Learner-view boundary and harness regressions

The non-materializing projection check was run as follows:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B environment/project_learner_view.py . --check-source
```

Observed exit code: `0`:

```text
PASS learner-view source and policy: 9 included top-level entries, 8 excluded top-level entries, 23 regular files
```

No learner workspace was created from this evaluator pack, as required by the
production-builder boundary. The full projector remains available for the
acceptance harness, which must expose only its output and independently prove
that the source pack is unreadable before awarding `TRANSFER_VERIFIED`.

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B -m unittest discover -s sealed/harness_tests -v
```

Observed exit code: `0`; `Ran 4 tests` and `OK`. Two learner-view tests checked
that the real source inventory contains only allowlisted roots and that a
synthetic projection omits every evaluator-only root and marker. The synthetic
fixture contained no pack solution material. The two existing process tests
also passed, including the intentional timeout code `124` and descendant
cleanup.

## Structure, metadata, and credential-pattern scan

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B sealed/validate_layout.py
```

Observed exit code: `0`:

```text
PASS required regular files: 23
PASS forbidden paths absent: 21
PASS generated paths are regular files/directories: 108 paths
PASS strict JSON and GENERATED+PARTIAL manifest: 4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa
PASS provenance linkage and strict JSON: 7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2
PASS learner-view policy: 9 included, 8 excluded top-level entries
PASS credential-pattern scan: 56 files
```

The validator traverses only canonical generated roots, rejects symlinks and
special files there, checks every required and forbidden path, parses JSON with
duplicate-key rejection, compares the manifest with the authoritative object,
checks provenance linkage, validates the exact learner allowlist, and scans
all generated regular files for private-key and common assigned-credential
patterns.

```text
sha256sum MANIFEST.yaml PROVENANCE.json
```

Observed exit code: `0`:

```text
4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa  MANIFEST.yaml
7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2  PROVENANCE.json
```

The archived top-level contract was checked with:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B -c 'from pathlib import Path; root=Path("."); prior={p.name for p in (root/"PRIOR_BUILD").iterdir()}; canonical={"README.md","AGENTS.md","MANIFEST.yaml","PROVENANCE.json","LICENSE_BOUNDARY.md","REQUIREMENTS.md","CONCEPTS.md","DESIGN_QUESTIONS.md","VALIDATION.md","starter","public_tests","environment","sealed","adversarial","debugging","review_exercises","benchmarks"}; current={p.name for p in root.iterdir()}; assert prior == canonical; assert prior <= current; print(f"PASS preserved prior canonical top-level entries: {len(prior)}")'
```

It exited `0` and printed `PASS preserved prior canonical top-level entries:
17`.

Final file-type and scratch-residue commands were:

```text
find README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed adversarial debugging review_exercises benchmarks \( -type l -o \( -not -type f -a -not -type d \) \) -print
find starter public_tests environment sealed adversarial debugging review_exercises benchmarks \( -name '__pycache__' -o -name '*.pyc' -o -name '*.class' -o -name '*.log' -o -name '.minilog-runner-tmp' \) -print
```

The combined command exited `0`; both `find` invocations produced no output.

## Explicitly not validated

- The provenance URL was not accessed and no upstream content was copied.
- No actual learner transfer or runtime sandbox was created or tested.
- No benchmark, fuzzing, profiler, process-crash campaign, filesystem fault
  injection, network test, security audit, deployment, or alternate-JDK run
  occurred.
- Passing builder-owned checks does not confer `BUILDS`, `TESTED`, `FUZZED`,
  `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.
