# Supported environment

The project has no third-party dependencies. It expects:

- a C11 compiler with `<stdint.h>` and 64-bit `int64_t`;
- POSIX-like `make` for supplied build recipes;
- Python 3.6 or newer for test and audit helpers;
- process-group support for test timeout cleanup.

The tested build flags are `-std=c11 -Wall -Wextra -Wpedantic -Werror -O2`. The implementation does not depend on two’s-complement wraparound and requests no network access.

Run the non-shelling environment probe from the repository root:

```sh
python3 environment/check_environment.py
```

The probe compiles and runs a temporary C11 program with bounded subprocess timeouts. It reports observed tool versions; it does not install or modify dependencies.

Absolute tool paths and extra compiler driver options can be supplied without changing `PATH`, for example:

```sh
python3 environment/check_environment.py \
  --cc /path/to/gcc --cc-option=-B/path/to/binutils/ \
  --make /path/to/make
```

The archive-boundary audit is separately replayable and carries the complete path lists and credential patterns used by validation:

```sh
python3 environment/audit_pack.py
```

It skips factory-owned marker and staged prior-build roots, rejects unknown generated roots and special files, and scans non-build generated files for common credential signatures.
