# Alternative architectures

1. Resolve every variable to `(scopeDepth, slot)` before execution, then use arrays instead of maps.
   This improves predictability but adds a semantic-analysis phase.
2. Compile directly from parser events without an AST. This lowers allocation but makes dual-engine
   parity and source-level teaching harder.
3. Use a register VM. It can reduce instruction count, while requiring register allocation and more
   complex bytecode validation.
4. Represent values with a tagged sealed hierarchy rather than Java objects/null. That removes null
   ambiguity and makes type checks exhaustive at the cost of more boilerplate.
5. Emit JVM bytecode. This offers host optimization but greatly expands verifier, class-loading, and
   isolation concerns and is intentionally out of scope.
