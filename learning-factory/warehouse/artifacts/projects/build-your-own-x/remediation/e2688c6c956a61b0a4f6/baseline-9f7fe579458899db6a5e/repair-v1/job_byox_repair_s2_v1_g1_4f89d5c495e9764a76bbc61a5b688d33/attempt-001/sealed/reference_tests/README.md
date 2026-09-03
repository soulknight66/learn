# Sealed reference tests

`test_reference.c` covers exact capacities, pointer errors, legal and illegal
process transitions, PID exhaustion, mapping alignment and permissions,
filesystem name limits, sparse gaps, full-file I/O, and error atomicity.

`test_adversarial.c` applies fixed-seed operation sequences to every subsystem.
It checks invariants after each operation and byte-compares state around
rejected mutations. The sequence lengths and seed are constants, so a failure
is reproducible without saving random input.

These are implementation-bearing evaluator tests. They belong in the sealed
view and must never be copied beside learner code or public tests.
