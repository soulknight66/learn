# Sealed reference implementation

This directory contains one complete implementation of the four documented subsystem contracts.
It is evaluation material, not learner guidance. The implementation intentionally favors explicit
fixed-size scans over cleverness so invariants can be audited.

Build commands from the repository root:

```sh
make -C sealed/reference host-check
make -C sealed/reference kernel
make -C public_tests SOURCE_DIR=../sealed/reference test
```

The public API wrapper includes the authoritative starter header, preventing the reference from
silently changing the learner's contract.
