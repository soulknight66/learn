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
