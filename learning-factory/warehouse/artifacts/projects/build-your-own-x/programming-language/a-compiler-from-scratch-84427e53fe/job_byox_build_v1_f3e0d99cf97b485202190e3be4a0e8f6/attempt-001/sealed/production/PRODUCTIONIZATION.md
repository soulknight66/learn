# Productionization assessment

`MANIFEST.yaml` correctly records `productionized: false`. The reference is not ready to execute tenant-controlled programs in a service.

Before considering that use, add:

- explicit byte/token/nesting/AST/instruction/local/stack/output limits;
- a control-flow bytecode verifier with stack-height and abstract-type joins;
- immutable bytecode serialization with versioning and integrity checks;
- instruction-to-source span metadata and structured diagnostic codes;
- cancellation tied to wall-clock deadlines in the embedding process;
- output quotas and an isolated output sink;
- property and mutation tests for lexer/parser/compiler/VM agreement;
- subprocess isolation with resource limits if programs cross a trust boundary;
- compatibility tests across supported Ruby versions;
- telemetry that excludes source text by default and never records sensitive inputs;
- independent security, correctness, and operational review.

The current deterministic instruction budget is useful defense in depth, not a substitute for memory, recursion, wall-time, or output controls. No throughput, latency, fuzzing, or reliability claims were measured during generation.
