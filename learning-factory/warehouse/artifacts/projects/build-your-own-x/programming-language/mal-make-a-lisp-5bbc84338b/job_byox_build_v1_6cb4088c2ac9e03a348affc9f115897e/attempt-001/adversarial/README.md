# Adversarial validation inventory

This evaluator-only area records the threat model rather than exposing hidden cases to learners.
Executable boundary cases live under `sealed/reference_tests/` and cover:

- unmatched delimiters, quote-at-EOF, unsupported escapes, multiline strings, and nesting limits;
- falsey-value confusion, bool-as-int confusion, huge integer division, malformed forms with potential
  side effects, recursive closures, and resettable budgets;
- invalid opcodes, operand shapes, indexes, jumps, stack underflow/overflow, infinite bytecode loops,
  and non-builtin VM callees;
- CLI argument conflicts, missing files, expected failures without tracebacks, and REPL state.

The corpus is finite and deterministic. It was not described as fuzzing, and passing it would not
establish safety against arbitrary hostile programs or resource exhaustion.
