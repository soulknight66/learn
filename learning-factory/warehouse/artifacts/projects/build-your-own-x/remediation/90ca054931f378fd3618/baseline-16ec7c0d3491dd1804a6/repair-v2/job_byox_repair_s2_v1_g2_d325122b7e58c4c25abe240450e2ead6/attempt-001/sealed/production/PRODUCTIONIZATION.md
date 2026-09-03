# Productionization assessment

`MANIFEST.yaml` correctly states `productionized: false`.  The reference is an
educational implementation and has not earned production, security, fuzzing,
benchmark, or transfer-validation labels.

Before deployment, at minimum:

- define threat models for source, bytecode, arguments, and output sinks;
- split parsing, verification, and execution into separately testable modules;
- add an authenticated, versioned bytecode container or forbid bytecode input;
- use configurable memory/CPU budgets enforced outside the interpreter process;
- add cancellation and output-byte quotas, not only instruction limits;
- test allocator and I/O failures through injected interfaces;
- run coverage-guided lexer, parser, verifier, and VM fuzzers with sanitizers;
- validate integer behavior across every supported compiler and architecture;
- decide whether diagnostics and emitted bytecode are stable compatibility APIs;
- add deterministic build provenance and dependency/SBOM generation;
- add concurrency, reentrancy, and repeated-execution tests;
- commission an independent security and undefined-behavior review.

The current guest has no filesystem, network, dynamic allocation, or native
call capability, which limits impact, but in-process denial of service remains
possible without an external wall-clock and output quota.
