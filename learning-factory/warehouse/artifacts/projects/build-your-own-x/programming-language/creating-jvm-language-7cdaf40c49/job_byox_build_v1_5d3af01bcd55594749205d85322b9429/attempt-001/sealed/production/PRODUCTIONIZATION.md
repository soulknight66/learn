# Productionization assessment

`productionized` remains `false`. The implementation is intentionally an
educational compiler and has not passed independent build, test, fuzz,
benchmark, transfer, security, or production review gates.

Before production use:

1. Compile and test on every supported JDK/vendor and verify generated classes in
   fresh JVM processes with bounded memory and time.
2. Add coverage-guided lexer/parser fuzzing, grammar-based well-typed generation,
   malformed class inspection, and differential execution against an independent
   interpreter.
3. Replace recursive walks or prove stack budgets for the deployment runtime;
   add an explicit maximum source-byte size and allocation budget.
4. Decide whether version 49 is acceptable. Otherwise emit modern class versions
   with correct stack-map frames and test them against multiple verifiers.
5. Add `goto_w` rewriting or specify smaller source/code limits before emission
   so late branch failure cannot waste significant work.
6. Define a sandbox. Generated code must never be loaded into a privileged,
   long-lived service process merely because the compiler accepted it.
7. Add structured telemetry that excludes source text by default, stable public
   error documentation, release signing, an SBOM, and reproducible build records.
8. Perform concurrency, memory-pressure, security, and abuse-case reviews. The
   current facade has no mutable global state, but this has not been stress-tested.

No production readiness or performance number is asserted by this file.

