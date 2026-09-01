# Sealed alternatives

Several valid architectures were considered but not selected:

1. **Direct AST interpreter.** It removes bytecode and is the shortest path to expression results. It does not exercise compiler lowering or a separately validated VM, so it cannot satisfy this challenge on its own. It is useful as a differential oracle if independently implemented.
2. **Visitor interfaces.** Node-specific Go types with visitor methods encode AST shape more strongly. They make caller-forged malformed nodes harder to express, reducing the explicit defensive-programming exercise.
3. **Infix surface syntax.** A Pratt parser would add precedence and associativity lessons. It increases parser complexity without changing analysis, lowering, or VM fundamentals.
4. **Register bytecode.** Explicit destination/source operands avoid operand-stack validation but require register allocation and wider instructions. For a small expression language, the stack representation is easier to inspect.
5. **Opaque validated bytecode.** `Validate` could return an unexported immutable wrapper accepted by `Run`. This avoids revalidation but complicates the required exported-value robustness tests and still needs a copying/ownership policy.
6. **Streaming output callback.** This reduces output memory, but a callback can observe values before a later runtime error, contradicting Pebble's transactional output contract.

An alternative is acceptable only if it preserves the exported API and every observable requirement. A direct evaluator hidden inside `Execute` is not acceptable because it would leave compiler and VM behavior untested by end-to-end cases.
