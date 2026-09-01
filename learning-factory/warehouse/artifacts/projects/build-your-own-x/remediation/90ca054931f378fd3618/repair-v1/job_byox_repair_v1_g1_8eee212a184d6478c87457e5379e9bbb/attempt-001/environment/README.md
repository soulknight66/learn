# Environment

The artifact targets a hosted C11 compiler, `make`, a POSIX-like process environment with process
groups and resource limits, and Python 3 for black-box test orchestration. It has no third-party
dependencies and requires no network.

Observed during generation:

```text
cc: /usr/bin/cc
gcc: /usr/bin/gcc
make: /usr/bin/make
python3: Python 3.6.8
```

Reproducible learner commands from the repository root:

```sh
make -C starter clean all
python3 public_tests/run_tests.py starter/build/minic
```

The compiler flags in the supplied makefiles request C11 and common warnings. Sanitizers are not
assumed available. See `VALIDATION.md` for commands and outputs actually observed rather than
expected results.

The runners require Python's POSIX `resource` module and `start_new_session` support. They constrain
test processes but are not a general sandbox; `sealed/production/PRODUCTIONIZATION.md` records the
remaining isolation boundary.
