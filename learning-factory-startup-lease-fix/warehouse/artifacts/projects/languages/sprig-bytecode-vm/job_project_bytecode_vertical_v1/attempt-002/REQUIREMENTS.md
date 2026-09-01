# Observable contract

Export `parse_source(str)` and `run_source(str, *, max_steps=10000)` from `tinyvm`.
`run_source` returns immutable output values, a snapshot of global variables, a non-negative
semantic step count, and an engine name. Both supplied architectures obey this API. A step is
one source AST statement or expression visit in both engines; the same `max_steps` therefore
has the same success/failure boundary. Bytecode dispatch has a separate internal safety bound.

Values are signed 64-bit integers; booleans are canonical integers 0 and 1. Arithmetic
overflow, division by zero, an undefined name, a duplicate `let`, malformed input, and
exhausted step budgets are typed language errors. Division truncates toward zero and the
remainder has the dividend's sign. `&&` and `||` short-circuit and return 0 or 1.

Declarations are global in this intentionally small language. A block controls sequencing,
not lexical scope. Output is captured rather than printed by the library. The implementation
may not use Python `eval`, `exec`, or AST compilation as its language engine.

Suggested milestones: literals/print; precedence and variables; checked operations; branches;
loops; bytecode validation and resource limits; diagnostics and adversarial tests.
