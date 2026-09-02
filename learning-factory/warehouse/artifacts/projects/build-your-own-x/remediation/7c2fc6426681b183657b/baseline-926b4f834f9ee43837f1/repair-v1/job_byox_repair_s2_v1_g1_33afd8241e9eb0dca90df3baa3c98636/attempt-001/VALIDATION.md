# Repair validation evidence

## Label boundary

This is worker-local evidence for repair generation 1. The authoritative manifest remains
`GENERATED` with only `GENERATED` and `PARTIAL`; `productionized` remains false and independent
validation remains required. Nothing below claims `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

The shell launcher prepended `/usr/bin/id: cannot find name for user ID 532319` and the analogous
group warning to commands. Those ambient account-mapping lines were not emitted by pack programs.

## Repair coverage

- `environment/build.py` now gives the linker the stable relative input `cinder.o` while using a
  private scratch directory beside the requested output. It checks each supplied source/tool path
  with `lstat` before resolution. Because `/usr/bin/ld` is itself an alternatives symlink on this
  host, the honest regular-file default is `/usr/bin/ld.bfd`.
- `environment/audit.py` requires all 37 checked-in files, including implementation, test, build,
  audit, benchmark, reference, and evaluator files. Its canonical digest covers the complete
  provenance object and is named separately from the source-snapshot identifier.
- `environment/test_tooling.py` checks two-build byte identity, absence of scratch/workspace path
  strings, source/assembler/linker symlink rejection separately, each functional-file omission,
  and provenance changes in license, upstream-reference, and source-commit fields.
- `REQUIREMENTS.md` now rejects integer-shaped definition names explicitly. `README.md` calls the
  immediate scaffold operation a build command rather than a nonexistent public sanity test. The
  sealed dictionary-name cases now include an out-of-range integer-shaped name.

## Tool observations

Commands, all from the pack root:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/as --version | /usr/bin/sed -n '1p'
/usr/bin/ld.bfd --version | /usr/bin/sed -n '1p'
env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 --version
/usr/bin/uname -s -m
```

Observed, in order:

```text
Python 3.11.5
GNU assembler version 2.30-123.el8
GNU ld version 2.30-123.el8
qemu-x86_64 version 9.1.1
Copyright (c) 2003-2024 Fabrice Bellard and the QEMU Project developers
Linux x86_64
```

Pinned Python and configured QEMU were useful binaries invoked by their exact toolchain-root paths.
No configured x86-64 binutils root was supplied, so the build used the exact regular host paths
shown above. The configured Java and Arm toolchains were not applicable and were not used.

## Focused repair-test development

The focused command was:

```text
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s environment -p 'test_*.py' -v
```

The first run reported two audit tests `ok` and skipped the build-test class because the then-test
path `/usr/bin/ld` was a symlink. After selecting `/usr/bin/ld.bfd`, the next run passed the two audit
and three symlink tests but failed repeated building: pinned Python reported `FileNotFoundError: [Errno
2] No usable temporary directory found`. That evidence caused scratch placement to move beside the
requested output. The final run returned 0:

```text
Ran 6 tests in 2.113s

OK
```

All six named methods reported `ok`; none was skipped.

## Reproducible builds and ELF inspection

Commands:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py sealed/reference/forth.S -o sealed/reference/build/repro-a
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py sealed/reference/forth.S -o sealed/reference/build/repro-b
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py starter/forth.S -o starter/build/cinder
```

Each returned 0 with no helper diagnostic. Comparison and inspection commands:

```text
/usr/bin/sha256sum sealed/reference/build/repro-a sealed/reference/build/repro-b
/usr/bin/cmp -s sealed/reference/build/repro-a sealed/reference/build/repro-b
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'from pathlib import Path; a=Path("sealed/reference/build/repro-a").read_bytes(); b=Path("sealed/reference/build/repro-b").read_bytes(); prefix=b".cinder-build-"; print("byte_identical=%s workspace_path_embedded=%s random_scratch_prefix_embedded=%s" % (a == b, str(Path.cwd()).encode() in a, prefix in a))'
/usr/bin/file sealed/reference/build/repro-a
/usr/bin/readelf -W -l sealed/reference/build/repro-a | /usr/bin/grep GNU_STACK
/usr/bin/readelf -W -s sealed/reference/build/repro-a | /usr/bin/grep '_start$'
/usr/bin/readelf -p .strtab sealed/reference/build/repro-a
```

`cmp` returned 0. Observed hashes and relevant output:

```text
5b73caee22ee3e317b10049367130fcfb23a4973bff821c38f928cf2b9218e98  sealed/reference/build/repro-a
5b73caee22ee3e317b10049367130fcfb23a4973bff821c38f928cf2b9218e98  sealed/reference/build/repro-b
byte_identical=True workspace_path_embedded=False random_scratch_prefix_embedded=False
sealed/reference/build/repro-a: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, not stripped
GNU_STACK ... RW  0x10
276: 00000000004000e8    73 FUNC    GLOBAL DEFAULT    1 _start
```

The `.strtab` dump began with `cinder.o`; it contained neither a `.cinder-build-*` path nor the
workspace path. An earlier presentation-only Python one-liner used a backslash inside an f-string
expression and returned 1 with `SyntaxError: f-string expression part cannot include a backslash`.
The corrected command and its output are recorded above; the failed formatter did not run or alter a
build.

## Native, QEMU, and starter behavior

Bounded smoke commands:

```text
/usr/bin/printf ': square dup * ; 12 square .\n' | /usr/bin/timeout --signal=KILL 3s sealed/reference/build/repro-a
/usr/bin/printf ': square dup * ; 12 square .\n' | /usr/bin/timeout --signal=KILL 3s env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 sealed/reference/build/repro-a
```

Both returned 0 and each wrote exactly `144` followed by a newline. The QEMU result is one smoke
case, not transfer verification.

The starter was invoked through pinned Python using `subprocess.Popen(["starter/build/cinder"],
stdin=PIPE, stdout=PIPE, stderr=PIPE, start_new_session=True)` and `communicate(b"", timeout=3)`;
the timeout branch used `os.killpg(..., SIGKILL)`. Observed:

```text
returncode=2
stdout=b''
stderr=b'error: interpreter not implemented\n'
```

This deliberate stub is why the learner artifact remains `PARTIAL`.

## Behavioral and regression suites

Commands:

```text
env CINDER_BIN=sealed/reference/build/repro-a PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
env REFERENCE_BIN=sealed/reference/build/repro-a PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s environment -p 'test_*.py' -v
```

Observed final summaries:

```text
Ran 10 tests in 0.025s
OK
Ran 13 tests in 0.047s
OK
Ran 6 tests in 2.113s
OK
```

All named tests reported `ok`; no final run skipped a test.

## Benchmark harness smoke

Command:

```text
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 benchmarks/run.py sealed/reference/build/repro-a --iterations 3 --terms 10 --timeout 3
```

It returned 0. The emitted JSON reported `iterations: 3`, `terms_per_process: 10`, `minimum_ns:
1063190`, `median_ns: 1413808`, `maximum_ns: 1435270`, and `validation_label:
UNVALIDATED_MEASUREMENT`. These three samples are only a harness smoke check and support no
performance or benchmark label.

## Parsing, hashes, preservation, and final audit

An in-memory `compile()` pass over the explicit Python roots, followed by `json.loads()` of both JSON
documents, returned 0 and reported:

```text
compiled_python_files=6
json_documents_parsed=2
python_files=benchmarks/run.py,environment/audit.py,environment/build.py,environment/test_tooling.py,public_tests/test_cinder.py,sealed/reference_tests/test_reference.py
```

Commands and observed hashes:

```text
/usr/bin/sha256sum MANIFEST.yaml PROVENANCE.json
c22f0d3691104fb2f03556eb89753678280c3ee082ee91b6daa9ecd39e6c8858  MANIFEST.yaml
a07dc4005276491142d98b5a1b764a7aa11342f525027ef38be2a9d01565ed87  PROVENANCE.json

/usr/bin/sha256sum README.md REQUIREMENTS.md environment/README.md environment/build.py environment/audit.py environment/test_tooling.py sealed/reference_tests/test_reference.py
cb1960318c8a3d8943f6656e3d3fe1f5b2aa223580cdc3057bbe41d99be61650  README.md
82ea2dcc3aa790d84ef3db743fe318295e208f838fab9baf61da3767ca316def  REQUIREMENTS.md
3ea6af54dc117d5161931c5cf3f2d3a32243e89c3686f7df69ef7711dda2152e  environment/README.md
61fb08f25dca72e19d4ae18d774a3958bf76a9beb3eca07adc0d4afcff0edac9  environment/build.py
ea24b313e1e4424782a586f79e4ea0ae7f1779a86127eeaa963c2c2682401828  environment/audit.py
629bc16f9425cae00d940b1cb3b849293ef00215ee5f7afaad81bc849cb49282  environment/test_tooling.py
a96feba06979c97dfa51628ccbfbfa0a04d996dae7f59446312d5da6823b564e  sealed/reference_tests/test_reference.py
```

A pinned-Python top-level comparison against `PRIOR_BUILD/` reported:

```text
prior_top_level_entries=17
missing_prior_top_level_entries=[]
top_level_LICENSE_exists=False
artifact_inventory_exists=False
```

The first formatting attempt for that comparison also used escaped quotes inside an f-string and
returned 1 with the same Python `SyntaxError`; the corrected percent-formatting command produced the
result above. Neither comparison modified a file.

Final command, run after this validation record and scratch cleanup:

```text
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
```

Observed exit status 0 and output:

```json
{"credential_patterns": 4, "files_scanned": 37, "forbidden_absent": 21, "manifest_exact": true, "provenance_object_exact": true, "required_regular": 37, "special_entries_absent": true}
```

The audit requires every final regular file, checks all 21 forbidden paths, walks entry types without
following links, compares the exact manifest, verifies the complete canonical provenance-object
digest, and scans the pack roots for four narrowly defined credential patterns.

## Cleanup and limitations

After all executable-dependent checks, these exact scratch targets were inspected and removed:

```text
/usr/bin/rm starter/build/cinder sealed/reference/build/repro-a sealed/reference/build/repro-b
/usr/bin/rmdir starter/build sealed/reference/build
```

Both commands returned 0. No build executable, object, temporary fixture, symlink, or bytecode cache
is retained in the final pack.

The immutable upstream catalog snapshot and linked resource were not available for independent
license, similarity, or clean-room authentication. Learner-view exclusion of `sealed/` is an
external control-plane property and was not transfer-verified here. No fuzzing or production review
was performed, and the benchmark smoke supports no performance conclusion. Fresh independent
validation remains mandatory.
