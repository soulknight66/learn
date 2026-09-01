# Validation record

Validation date: 2026-08-31
Working directory: allocated attempt workspace
Status retained: GENERATED + PARTIAL
Independent validation: REQUIRED

## Toolchain observation

Command:

    sh environment/check.sh

Observed exit status: 0.

Observed relevant output:

    /usr/bin/as
    /usr/bin/ld
    /usr/bin/make
    /usr/bin/python3
    GNU assembler version 2.30-123.el8
    GNU ld version 2.30-123.el8
    Python 3.6.8

The command wrapper also printed identity-lookup warnings for the sandbox numeric user and group.
Those warnings were environmental and did not change the command status.

## Starter build and expected challenge baseline

Commands:

    make -C starter clean all
    python3 -m unittest discover -s public_tests -v

The build exited 0 and produced starter/stackvm. The public suite exited 1 with:

    Ran 10 tests in 0.054s
    FAILED (failures=8)

Two tests passed: empty/separator-only input and atomic compile rejection. Eight feature tests failed
because the intentionally incomplete starter returns status 2 for non-empty source. This is the
documented learner baseline, not a passing implementation claim.

## Informative failed reference attempt

The first assembled reference passed successful-program cases but five public error-path cases timed
out. Disassembly showed instructions such as a load from absolute address 0x10 for a message length.
In GNU as Intel syntax, the bare equate operand had been encoded as a memory operand. The source was
corrected to use OFFSET FLAT for each diagnostic length. A focused rerun then observed status 3,
empty standard output, and exactly stack underflow plus newline on standard error. The failed attempt
is retained here as debugging evidence; it is also generalized into a sealed exercise.

## Final reference build inspection

Commands:

    make -C sealed/reference clean all
    file sealed/reference/stackvm
    readelf -h sealed/reference/stackvm

Observed build exit status: 0.

Observed file classification:

    ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, not stripped

readelf reported ELF64, little-endian, type EXEC, machine Advanced Micro Devices X86-64, and entry
point 0x4000e8.

## Public contract against sealed reference

Command:

    STACKVM_TARGET="$PWD/sealed/reference" python3 -m unittest discover -s public_tests -v

Observed exit status: 0.

Observed summary:

    Ran 10 tests in 0.045s
    OK

## Sealed boundary suite

Command:

    python3 -m unittest discover -s sealed/reference_tests -v

Observed exit status: 0.

Observed summary:

    Ran 11 tests in 0.082s
    OK

The sealed cases exercised numeric extrema and malformed values, checked-arithmetic failures,
division signs, underflow for every stack word, stack capacity, compile and runtime error timing,
4095/4096-byte input boundaries, all control-byte separators, and short-read accumulation.

## Labels not claimed

No network retrieval, upstream checkout, fuzzing campaign, benchmark run, profiler run, sanitizer
run, transfer verification, external review, or production-hardening validation was performed.
The benchmark file is an unexecuted harness and contains no measurement. These local observations do
not award BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED.

## Final structure and hygiene

An inline Python checker used pathlib and strict json.loads hooks that reject duplicate keys and
non-JSON constants. It compared MANIFEST.yaml to the authoritative object, checked provenance
bindings, enumerated all 23 required files and every forbidden path, and rejected symlinks or
special files. Observed results were:

    required_files=23 missing=0
    forbidden_paths_present=0
    symlinks_or_special_files=0
    manifest_exact=true
    provenance_strict_json=true snapshot_binding=true

A recursive grep for AWS access-key shapes, private-key headers, password/key/secret assignments,
and bearer credentials returned no matches. make -C starter clean and
make -C sealed/reference clean removed scratch objects and executables after testing; Python bytecode
caches and the two focused-run capture files were also removed explicitly.
