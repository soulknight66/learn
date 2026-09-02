# Validation record

Date: 2026-09-02 (America/Chicago)

Scope: local builder evidence only. These commands do not constitute the
independent validation required by `MANIFEST.yaml`. The upstream URL was not
accessed, and no upstream checkout or dependency download was attempted.

## Observed toolchain

Command:

```bash
python3 environment/check_toolchain.py
```

Observed exit status: 0.

```text
cc: /usr/bin/cc
  cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
make: /usr/bin/make
  GNU Make 4.2.1
python3: /usr/bin/python3
  Python 3.6.8
machine: x86_64
```

## Builds

Commands:

```bash
make -C starter clean all
make -C sealed/reference clean all
```

Observed exit status: 0 for both. The starter compiled three translation units
and linked `starter/pebble`; the reference compiled `main.c` and `pebble.c` and
linked `sealed/reference/pebble`. Both builds used
`-std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror`; the reference additionally
defined `_POSIX_C_SOURCE=200809L` while compiling.

## Executed tests

Public suite against the sealed reference:

```bash
PEBBLE_BIN="$PWD/sealed/reference/pebble" python3 public_tests/run_tests.py
```

Observed exit status: 0. Six tests ran in 0.185 seconds; all were `ok`, and
`unittest` reported `OK`. The suite included an assembly generation,
`cc` link, and native execution round trip.

Sealed reference suite:

```bash
PEBBLE_BIN="$PWD/sealed/reference/pebble" python3 sealed/reference_tests/run_tests.py
```

Observed exit status: 0. Ten tests ran in 1.071 seconds; all were `ok`, and
`unittest` reported `OK`. The cases covered exact statuses/diagnostics, name
resolution, arithmetic failures, step boundaries, depth/variable limits,
atomic output preservation, and interpreter/compiler differential behavior.

Adversarial suite:

```bash
PEBBLE_BIN="$PWD/sealed/reference/pebble" python3 adversarial/run_tests.py
```

Observed exit status: 0. Seven tests ran in 0.156 seconds; all were `ok`, and
`unittest` reported `OK`. The cases covered the exact 1 MiB boundary, an
over-limit source, invalid raw bytes, deep syntax/AST inputs, declaration
placement, and failed-publication cleanup.

All test drivers used argv arrays, captured streams, bounded timeouts, and
fresh temporary directories.

## Informative unavailable check

Command attempted:

```bash
make -C sealed/reference clean all CFLAGS='-std=c11 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer'
```

Instrumented objects compiled, but the link failed with the observed messages:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
```

Therefore no ASan/UBSan execution is claimed. No fuzzer, profiler,
cross-architecture runner, or benchmark was executed. The optional benchmark
harness contains no pre-recorded numbers.

## Final structure and hygiene

Commands:

```bash
make -C starter clean
make -C sealed/reference clean
python3 sealed/reference_tests/verify_artifact.py
```

Observed build-product cleanup succeeded. The verification command exited 0
and printed:

```text
required regular files: 23/23
forbidden paths present: 0
symlinks or special files: 0
credential scan: 49 text files, 0 high-confidence hits
metadata: strict JSON, exact manifest, immutable file hashes verified
artifact verification: OK
```

`MANIFEST.yaml` remains exactly `GENERATED` + `PARTIAL`, with
`productionized: false` and independent validation required.
