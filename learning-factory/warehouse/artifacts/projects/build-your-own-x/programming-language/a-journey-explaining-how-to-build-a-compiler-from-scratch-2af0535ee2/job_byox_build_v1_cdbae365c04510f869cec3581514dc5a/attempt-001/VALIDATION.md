# Validation record

Status remains GENERATED + PARTIAL. These are observations from the generation host on 2026-08-31,
not independent validation and not a promotion to any validation label.

## Observed tools

- cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
- GNU Make 4.2.1
- Python 3.6.8
- clang and valgrind were not found on PATH.
- The shell printed account-name lookup warnings for the sandbox's numeric user and group IDs before
  commands; these did not change command exit statuses.

No network or upstream repository was accessed. The linked tutorial remained provenance only.

## Successful commands

    make -C starter clean all

Exit 0. The starter compiled with C11, Wall, Wextra, Wpedantic, and Werror. Its compiler body is an
intentional placeholder; this build is not a semantic pass.

    make -C sealed/reference clean all test

Exit 0. The ordinary reference build completed with the same warning policy. The public Python suite
reported 11 tests passed; the sealed boundary suite reported 18 tests passed; the direct C API harness
reported 16 checks passed.

    PEBBLE_BIN="$PWD/sealed/reference/build/pebble" python3 adversarial/test_adversarial.py

Exit 0. Seven deterministic adversarial cases passed. This fixed corpus is not fuzzing.

    python3 environment/audit_repository.py

Exit 0 at final audit. It found all 23 required regular files, all 21 forbidden paths absent, only
regular files/directories in generated paths, exact manifest/provenance objects, and no
credential-like text patterns.

## Informative failed attempts

The first public-test invocation failed before running compiler behavior because Python 3.6 rejects
the subprocess.run keyword text. The driver was changed to the equivalent universal_newlines keyword,
after which all public tests passed.

The first direct API harness used tmpfile. All three calls returned null in this sandbox, so the
harness was changed to deterministic named scratch files beneath sealed/reference_tests/build and
removes them after use. The revised harness passed.

The optional sanitizer command was attempted:

    make -C sealed/reference clean all \
      CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=address,undefined'

Compilation succeeded but linking failed with exit 2 because the host linker could not find
/usr/lib64/libasan.so.5.0.0 or /usr/lib64/libubsan.so.1.0.0. The ordinary build was then restored and
retested. Sanitizer validation is unavailable, not passed.

After the successful runs, the three Makefile clean targets removed reproducible object files and
executables from their local build directories. Source, tests, commands, and observed results remain.

## Explicitly not claimed

The benchmark harness was not run and contains no checked-in results. No random or coverage-guided
fuzzing, profiler, transfer validation, external code review, production deployment, or independent
validator ran during generation. Known production gaps are recorded under sealed/production and the
sealed review. Accordingly MANIFEST.yaml intentionally remains status GENERATED with labels GENERATED
and PARTIAL and productionized false.
