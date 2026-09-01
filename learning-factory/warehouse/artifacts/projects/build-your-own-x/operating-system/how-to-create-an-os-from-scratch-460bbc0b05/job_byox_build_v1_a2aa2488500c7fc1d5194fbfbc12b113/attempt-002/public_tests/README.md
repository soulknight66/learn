# Public tests

`test_public.c` is a small deterministic, hosted C test program. It checks
public argument validation and one representative lifecycle for each subsystem.
Run it from the repository root with:

```sh
make -C starter test
```

The starter is deliberately incomplete: validation tests pass while the three
functional lifecycle tests fail at marked `TODO` paths. Consequently the
initial `make test` exits nonzero. As you implement the lab, the same executable
should progress to `7 passed, 0 failed`.

These checks are examples, not a complete specification. Also test table
capacity, PID and frame reuse rules, every state transition, boundary offsets,
single-fault error categories, and the requirement that failures do not mutate
state or outputs. The contract intentionally does not prioritize error codes
for calls containing several simultaneous faults.
