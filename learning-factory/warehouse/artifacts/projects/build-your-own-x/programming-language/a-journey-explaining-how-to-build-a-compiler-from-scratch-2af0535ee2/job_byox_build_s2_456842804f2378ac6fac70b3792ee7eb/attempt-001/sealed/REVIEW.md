# Sealed implementation review

The reference is suitable as a compact correctness oracle for this bounded challenge, subject to independent validation. Local tests cover ordinary semantics, exact modes, numeric boundaries, declared limits, output channels, and direct malformed-bytecode calls.

Strengths:

- byte-oriented lexer with checked literal/name bounds and source positions;
- parser structure matches precedence and latches the first error;
- bindings enter scope after their initializer;
- VM checks metadata, slots, initialization, stack effects, opcode validity, and arithmetic before evaluating C expressions;
- file reads and test subprocesses are bounded;
- learner inputs contain no reference implementation or answer key.

Known limitations and review findings:

- recursive parentheses/unary parsing is guarded by a 512-level budget, but that fixed policy may be too strict or still too large for unusual target stacks;
- fixed capacities are educational constraints rather than production scaling behavior;
- disassembly/token output does not convert late standard-output write failures into exit 74;
- diagnostics stop after one error and carry points rather than source spans;
- there is no bytecode serialization, verifier pass, optimizer, debugger, or compatibility version;
- compilation and execution share one process, so the VM has no sandbox boundary;
- the test suite is deterministic but not exhaustive, fuzzed, benchmark-certified, or transfer-verified.

Accordingly `productionized` remains false and the artifact labels remain only `GENERATED` and `PARTIAL`.
