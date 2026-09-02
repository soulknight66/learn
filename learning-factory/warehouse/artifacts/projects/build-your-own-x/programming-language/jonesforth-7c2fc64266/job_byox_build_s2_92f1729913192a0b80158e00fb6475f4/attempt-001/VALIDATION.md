# Local validation evidence

## Label boundary

The authoritative status is still `GENERATED` with validation labels `GENERATED` and `PARTIAL`.
Everything below is worker-local evidence only. No independent validator ran, and no `BUILDS`,
`TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is
claimed. A useful failing development attempt is retained under
`sealed/reference_tests/DEVELOPMENT_LOG.md`.

The job launcher emitted `/usr/bin/id: cannot find name for user ID 532319` and the analogous group
warning before shell commands. Those ambient account-mapping lines were not assembler, linker,
interpreter, or unittest diagnostics.

## Toolchain observations

Commands (all invoked by absolute path):

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/as --version
/usr/bin/ld --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/usr/bin/uname -s -m
```

Observed:

```text
Python 3.11.5
GNU assembler version 2.30-123.el8
GNU ld version 2.30-123.el8
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
Linux x86_64
```

Python was the useful pinned toolchain-root binary used to drive every build and test. The configured
JDK was version-checked but was not used because this artifact has no Java component.

## Reference build and binary inspection

Command:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py sealed/reference/forth.S -o sealed/reference/build/cinder-reference
```

Observed exit status: 0. The helper emitted no build diagnostic.

Commands:

```text
/usr/bin/file sealed/reference/build/cinder-reference
/usr/bin/readelf -h sealed/reference/build/cinder-reference
```

Relevant observed output:

```text
sealed/reference/build/cinder-reference: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, not stripped
Class:                             ELF64
Type:                              EXEC (Executable file)
Machine:                           Advanced Micro Devices X86-64
Entry point address:               0x4000e8
```

Smoke command:

```text
/usr/bin/printf ': square dup * ; 12 square .\n' | sealed/reference/build/cinder-reference
```

Observed exit status 0 and stdout exactly:

```text
144
```

## Test runs

Public command:

```text
CINDER_BIN=sealed/reference/build/cinder-reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed: all 10 named tests reported `ok`; final output was:

```text
Ran 10 tests in 0.019s

OK
```

Sealed command:

```text
REFERENCE_BIN=sealed/reference/build/cinder-reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
```

Observed: all 13 named tests reported `ok`; final output was:

```text
Ran 13 tests in 0.060s

OK
```

The public suite covers the normal language surface. The sealed suite covers exact and one-past
input, data, dictionary, code, patch, and return boundaries plus malformed source and arithmetic
edges. These are deterministic unittests, not fuzzing.

## Deliberately incomplete starter

Command:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py starter/forth.S -o starter/build/cinder
```

Observed exit status: 0. An argv-based, three-second invocation on empty input then observed:

```text
returncode=2
stdout=b''
stderr=b'error: interpreter not implemented\n'
```

This expected stub result is why the overall artifact remains `PARTIAL`; learner behavioral tests do
not pass until the challenge is implemented.

## Content hashes

Command:

```text
/usr/bin/sha256sum MANIFEST.yaml PROVENANCE.json sealed/reference/forth.S public_tests/test_cinder.py sealed/reference_tests/test_reference.py environment/build.py environment/audit.py
```

Observed:

```text
c22f0d3691104fb2f03556eb89753678280c3ee082ee91b6daa9ecd39e6c8858  MANIFEST.yaml
a07dc4005276491142d98b5a1b764a7aa11342f525027ef38be2a9d01565ed87  PROVENANCE.json
670afd00dc6b252e07498bf92d30250da931b255ac494cd1e3c81be363dca64e  sealed/reference/forth.S
a117ef205f04ff0c1f2202f04ec027ffefdf69ef3bc133c655d299e8c45f08cc  public_tests/test_cinder.py
ef7d2334dd89656c80e9453e5f6f7219bf9331404ad4df7b6e547d3b3a4e2eeb  sealed/reference_tests/test_reference.py
af783bedf227193b552b840a714d34c38cc7b7d4e3ffb60b940230210d4185f9  environment/build.py
504290279af3287f9047d12f7746958ab26b3a1330fb53d43bb54be1e37ebde1  environment/audit.py
```

## Final structure and credential audit

Command:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
```

Observed exit status 0 and output:

```json
{"credential_patterns": 4, "files_scanned": 36, "forbidden_absent": 21, "manifest_exact": true, "provenance_binding": true, "required_regular": 23, "special_entries_absent": true}
```

The removed scratch artifacts were `starter/build/cinder`, its two captured stub streams,
`sealed/reference/build/cinder-reference`, and unittest bytecode caches. They are reproducible from
the commands above and are not part of the archived challenge.
