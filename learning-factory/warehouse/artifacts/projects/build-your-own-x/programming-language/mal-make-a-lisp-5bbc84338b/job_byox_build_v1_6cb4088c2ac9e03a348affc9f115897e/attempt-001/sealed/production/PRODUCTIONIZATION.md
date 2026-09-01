# Productionization assessment

`productionized` is deliberately `false`. The artifact demonstrates language mechanics; it has not
earned production claims.

Before deployment, at minimum:

1. replace recursive reader/evaluator control flow with explicit stacks or enforce validated hard
   ceilings independent of host recursion settings;
2. attach source spans to syntax and preserve stack traces of Sprig calls in structured diagnostics;
3. define bytecode versioning, verification, serialization rules, maximum program/constants sizes,
   and compatibility policy;
4. isolate execution in an operating-system sandbox with memory, CPU, output, filesystem, and process
   limits—the semantic step counter is not a security boundary;
5. add property-based and coverage-guided fuzzing for UTF-8 input, malformed bytecode, and differential
   evaluator/VM behavior;
6. measure coverage and performance on a declared Python/OS matrix, with retained raw artifacts and
   regression thresholds;
7. add packaging, dependency scanning, static analysis, release signing, support ownership, monitoring,
   and incident procedures;
8. commission an independent security and correctness review.

No item above was silently assumed complete. No benchmark, profiler, fuzzing, transfer verification,
or production deployment was performed during generation.
