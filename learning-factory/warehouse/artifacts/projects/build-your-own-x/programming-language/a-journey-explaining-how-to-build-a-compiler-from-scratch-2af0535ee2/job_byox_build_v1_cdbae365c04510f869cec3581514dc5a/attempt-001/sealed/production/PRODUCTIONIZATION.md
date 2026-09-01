# Productionization assessment

This artifact is not productionized. Before exposing Pebble to untrusted inputs, a production owner
would need at least:

1. An iterative or explicitly depth-bounded parser, with tests at and beyond every nesting limit.
2. A nonblocking, bounded input policy based on an already-open descriptor, not just a path and fread.
3. Consistent propagation of diagnostic and output stream errors.
4. Allocation-failure injection, corpus fuzzing under memory/undefined-behavior sanitizers, and
   coverage review.
5. A bytecode verifier separated from execution if programs can ever come from outside this compiler.
6. Versioned serialization with fixed endianness and widths if bytecode becomes an artifact.
7. Structured diagnostics with stable codes in addition to human text.
8. Cancellation/deadline integration; an instruction count is deterministic but not a wall-clock
   service guarantee.
9. Concurrency tests documenting whether shared compiled programs are safe across simultaneous runs.
10. Release engineering: supported compiler matrix, reproducible builds, dependency inventory,
    signed artifacts, security reporting, and operational telemetry that contains no source text.

No load, fuzz, transfer, concurrency, or external security validation was performed here. The benchmark
harness is only a reproducible starting point and contains no recorded claims.
