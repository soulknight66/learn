# Productionization assessment

This artifact is **not productionized**. The sealed implementation is a deterministic teaching
reference and has only local example-based validation.

Before production use, an owner would need at least:

- explicit input byte, token, AST-depth, output, heap, and execution-fuel limits;
- iterative or depth-guarded parsing/evaluation for hostile nesting;
- full bytecode control-flow and stack-effect verification before execution;
- structured multi-error diagnostics with stable versioning and redaction rules;
- fuzzing of lexer, parser, compiler, and malformed chunks, plus regression corpus retention;
- compatibility matrices across supported Node releases and operating systems;
- performance thresholds measured on declared hardware with warmup and variance handling;
- package metadata, an explicit generated-code license decision, dependency and release policy,
  changelog, provenance attestations, and rollback procedures;
- threat modeling that clearly states whether source and bytecode are trusted.

None of those items is claimed complete. The manifest correctly keeps `productionized` false and
contains no `PRODUCTIONIZED` label.
