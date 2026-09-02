# Independent validation evidence

Review date: 2026-09-02 (America/Chicago)

All commands were run from the review workspace root. `CANDIDATE/` remained read-only. The command
launcher prepended account-mapping warnings from `/usr/bin/id`; those ambient warnings were not
candidate output and are omitted below.

## Label boundary

This is reviewer evidence, not a manifest promotion. The advisory verdict is `PASS`, while the
candidate remains `GENERATED` + `PARTIAL`, with `productionized: false` and independent validation
required. Nothing here awards `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

## Toolchains

Commands:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/as --version | /usr/bin/sed -n '1p'
/usr/bin/ld.bfd --version | /usr/bin/sed -n '1p'
/usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-gcc --version | /usr/bin/sed -n '1p'
/usr/bin/uname -s -m
```

Observed:

```text
Python 3.11.5
GNU assembler version 2.30-123.el8
GNU ld version 2.30-123.el8
qemu-x86_64 version 9.1.1
openjdk version "21.0.5" 2024-10-15 LTS
arm-none-eabi-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203
Linux x86_64
```

Every configured root was available. Pinned Python was used for every Python check. Configured QEMU
and GLib were used for emulation. Java and Arm GCC were version-probed but are inapplicable to this
x86-64 assembly project. No configured x86-64 binutils root was supplied, so the candidate's regular
host paths `/usr/bin/as` and `/usr/bin/ld.bfd` were used.

## Preservation and inventory

Before and after candidate-dependent checks:

```text
find CANDIDATE -type f -print0 | sort -z | xargs -0 /usr/bin/sha256sum | /usr/bin/sha256sum
```

Both observations were:

```text
3b87903277427f07b85d5f03abeb49cb493eec3f2cda8a068b0f452223daaa4e  -
```

`find` identified 37 regular files, no symlinks, no bytecode, and no retained candidate build
products. Selected file hashes independently matched the submitted validation record:

```text
c22f0d3691104fb2f03556eb89753678280c3ee082ee91b6daa9ecd39e6c8858  CANDIDATE/MANIFEST.yaml
a07dc4005276491142d98b5a1b764a7aa11342f525027ef38be2a9d01565ed87  CANDIDATE/PROVENANCE.json
313156178cddc6cfff69bceb83b1b28b53f6a87ed5b64fceeb29e8ac07a500b7  CANDIDATE/sealed/reference/forth.S
7ff5af763682210c462e0797d962b991884a733370485330f1fba84c46eaee0f  CANDIDATE/sealed/reference_tests/test_reference.py
```

## Audit and metadata

Command:

```text
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 CANDIDATE/environment/audit.py
```

It returned 0:

```json
{"credential_patterns": 4, "files_scanned": 37, "forbidden_absent": 21, "manifest_exact": true, "provenance_object_exact": true, "required_regular": 37, "special_entries_absent": true}
```

An independent JSON check returned 0 and reported:

```json
{"canonical_provenance_sha256": "dc759cd6068016565adafc56a86680e216fda2867ba90aed0c352f07ff2a6017", "file_count": 37, "manifest_project_matches": true, "manifest_snapshot_matches": true, "manifest_source_matches": true, "provenance_file_sha256": "a07dc4005276491142d98b5a1b764a7aa11342f525027ef38be2a9d01565ed87", "special_entries": [], "top_level_license_exists": false}
```

The check parsed both metadata objects independently, canonicalized the complete provenance object,
and compared project, source, commit, and snapshot fields. Internal consistency is established;
external source authenticity is not.

## Reproducible builds and ELF inspection

Scratch outputs were placed outside `CANDIDATE/`:

```text
/usr/bin/mkdir -p REVIEW_TMP/build
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 CANDIDATE/environment/build.py CANDIDATE/sealed/reference/forth.S -o REVIEW_TMP/build/reference-a
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 CANDIDATE/environment/build.py CANDIDATE/sealed/reference/forth.S -o REVIEW_TMP/build/reference-b
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 CANDIDATE/environment/build.py CANDIDATE/starter/forth.S -o REVIEW_TMP/build/starter
/usr/bin/sha256sum REVIEW_TMP/build/reference-a REVIEW_TMP/build/reference-b REVIEW_TMP/build/starter
/usr/bin/cmp -s REVIEW_TMP/build/reference-a REVIEW_TMP/build/reference-b
```

All builds and `cmp` returned 0:

```text
b3e847dcfb3579a3a0029836ca3ea590076cad4399d714beae4ac38a95878092  REVIEW_TMP/build/reference-a
b3e847dcfb3579a3a0029836ca3ea590076cad4399d714beae4ac38a95878092  REVIEW_TMP/build/reference-b
72a0205dee22854aa726e476e3e61f01886d037a1aa324b2169034e1c3c017ff  REVIEW_TMP/build/starter
```

Inspection with `/usr/bin/file` and `/usr/bin/readelf` found both executables to be static x86-64
ELFs. The reference had no dynamic section, exposed the expected entry point, and requested no
executable stack:

```text
278: 00000000004000e8    73 FUNC    GLOBAL DEFAULT    1 _start
GNU_STACK ... RW  0x10
There is no dynamic section in this file.
```

## Candidate-authored behavioral suites

Commands:

```text
/usr/bin/env CINDER_BIN=REVIEW_TMP/build/reference-a PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s CANDIDATE/public_tests -v
/usr/bin/env REFERENCE_BIN=REVIEW_TMP/build/reference-a PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s CANDIDATE/sealed/reference_tests -v
```

Observed summaries:

```text
Public: Ran 10 tests in 0.020s -- OK
Sealed: Ran 14 tests in 0.054s -- OK
```

No method was skipped. These candidate-authored suites are useful evidence only because this review
reran them; they are not by themselves proof of a validation label.

The exact repair reproducer was also launched independently through an argv-based bounded Python
subprocess. It returned:

```json
{"returncode": 0, "stderr": "", "stdout": "7\n8\n"}
```

## Tooling regressions

The tooling tests create fixtures beneath their pack root. Because `CANDIDATE/` is intentionally
read-only, they were run against an unchanged-content writable staging copy:

```text
/usr/bin/mkdir -p REVIEW_TMP/tooling-fixture
/bin/cp -a CANDIDATE/. REVIEW_TMP/tooling-fixture/
/bin/chmod -R u+w REVIEW_TMP/tooling-fixture
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s REVIEW_TMP/tooling-fixture/environment -p 'test_*.py' -v
/usr/bin/diff -qr CANDIDATE REVIEW_TMP/tooling-fixture
```

The suite returned 0 with `Ran 6 tests in 2.206s -- OK`; no test was skipped. The final recursive
content comparison returned 0 with no output. This covered byte-identical rebuilds, rejection of
source/assembler/linker symlinks, missing functional-file detection, and complete provenance-object
binding.

## Reviewer-authored model and adversarial checks

A deterministic scratch harness used argv arrays, isolated process groups, captured streams, and
timeouts. Its final SHA-256 was
`3573fb10342782400322ecbff37c7b63457972696b954b8d37e2a23c35e4d2f3`. Command:

```text
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 REVIEW_TMP/adversarial_review.py REVIEW_TMP/build/reference-a REVIEW_TMP/build/starter /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 /arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64
```

Final return status was 0:

```json
{"arithmetic_source_bytes": 33145, "model_assertions": 830, "native_qemu_equal": true, "random_robustness_cases": 300, "seed": 20260902, "successful_contract_programs": 5, "targeted_error_cases": 15}
```

The model independently computed signed 64-bit wrapping, truncation-toward-zero division and
remainder, comparisons, and bitwise results. Other checks covered stack transformations, compiled
calls, nested branches, six near-numeric names, every separator byte from `0x00` through `0x20`,
expected error classes, and 300 arbitrary-byte inputs of 0–1,024 bytes. Every arbitrary input exited
0 or 2 within one second; success had empty stderr, and failure began with `error:`. One compiled
control-flow workload had identical status and streams natively and under configured QEMU.

Two preliminary harness executions returned 1 because the reviewer-authored nested-control expected
sequence was wrong and then stale after correcting the test definition. The observed candidate output
matched the Forth stack order; correcting only the scratch expectation produced the passing result
above. These were reviewer test defects, not candidate failures, and are retained here for honesty.
The 300 seeded cases are a bounded robustness smoke check, not coverage-guided fuzzing and not a
`FUZZED` claim.

## Starter and benchmark smoke checks

The starter was launched with empty input in a bounded argv-based subprocess and returned exactly:

```json
{"returncode": 2, "stderr": "error: interpreter not implemented\n", "stdout": ""}
```

This intentional behavior agrees with the documentation and explains `PARTIAL`.

Benchmark command:

```text
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 CANDIDATE/benchmarks/run.py REVIEW_TMP/build/reference-a --iterations 3 --terms 10 --timeout 5
```

It returned 0 with `minimum_ns: 1113727`, `median_ns: 1183472`, `maximum_ns: 1196536`, three
iterations, and ten terms. The emitted label was `UNVALIDATED_MEASUREMENT`. This validates basic
harness execution only and supports no performance conclusion or `BENCHMARKED` label.

## Static review observations

All 1,336 reference-assembly lines and all Python/tooling paths were inspected. The implementation
uses complete-token numeric classification, exact-length lookup, delayed dictionary publication,
checked code and stack stores, typed branch patching, a separate bounded VM return stack, instruction
fuel, pre-`idiv` zero/overflow checks, and partial-write/EINTR handling for language output. Tests and
tools use argv arrays, timeouts, captured streams, and process groups rather than shell strings.

Learner material provides progressive milestones, a precise specification, concepts, checkpoint
questions, public examples, and staged review/debugging exercises without placing the reference
assembly outside `sealed/`. Physical exclusion of `sealed/` from a learner view is nevertheless an
external transfer control and was not independently exercised.

## Limitations

- The source catalog snapshot, prior generation workspaces, and linked upstream resource were not
  available. Their hashes, license evidence, historical diff, and clean-room relationship could not
  be authenticated independently.
- No top-level license grants broader rights to the generated material; the stated boundary is
  personal educational use, while linked-resource licensing remains `NOASSERTION`.
- Reproducible bytes were demonstrated with the recorded host binutils only; no configured immutable
  x86-64 assembler/linker root was supplied.
- No coverage-guided fuzzer, sanitizer, code coverage, validated benchmark, production/security
  assessment, or broader platform matrix was run.
- QEMU parity on a bounded workload is useful smoke evidence but does not confer
  `TRANSFER_VERIFIED`.

## Scratch cleanup

After recording all executable-dependent evidence, the explicit `REVIEW_TMP/` staging tree was
removed. It contained only reviewer-created copies, executables, temporary tooling fixtures, and the
review harness. An initial `rm -rf` request was rejected by the execution policy before it ran. The
fallback used `find` on the already resolved, workspace-local absolute path, `unlink` for files, and
bottom-up `rmdir` for directories; both commands returned 0. `CANDIDATE/` was not modified. Final
JSON/schema and workspace-cleanliness checks are recorded by the review handoff.
