# Deterministic model workload

`model_randomized.c` uses a fixed xorshift seed (`0x20260830`) to allocate, free, and resize
independent slots in a deliberately constrained arena. A byte-tag model verifies non-overlap,
alignment, arena bounds, prefix preservation, and failed-resize atomicity, while the
implementation invariant checker runs after each operation. The fixture fails unless ordinary
out-of-capacity resize failures occur. This is reproducible randomized model checking, not
exhaustive proof and not a general-purpose fuzzer.
