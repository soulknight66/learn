# Sealed reference implementation

This directory contains the complete deterministic host implementation and an independently written
ARMv7 cooperative demonstration. It is validator/instructor material, not a learner input.

The host implementation uses only fixed arrays and C11 library memory routines. Build from the
repository root with `make -C sealed/reference clean all`. The ARM subdirectory is a distinct
freestanding adapter and is expected to remain unbuilt when its external toolchain is unavailable.
