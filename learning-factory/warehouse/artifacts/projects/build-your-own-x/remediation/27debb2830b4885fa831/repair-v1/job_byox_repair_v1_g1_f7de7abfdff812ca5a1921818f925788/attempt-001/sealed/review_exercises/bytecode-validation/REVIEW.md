# Bytecode validator review answer

The candidate recognizes opcode spelling and a final halt, but does not establish safety.

Critical counterexamples include `ADD, HALT` (stack underflow), `JUMP -1, HALT` (invalid target),
`CONSTANT 99, HALT` with no constants (invalid index), an early `HALT` followed by dead instructions,
and code whose two branch paths reach a join with different heights. Constants may be objects or
non-finite numbers. Instructions may omit arguments, carry irrelevant arguments, or use invalid
locations. There are no input-size, stack, scope, or dispatch bounds. If execution began while checks
were still being performed, `PRINT` could also expose partial effects before a later defect appeared.

A correction should perform two complete phases: strict structural/argument validation over every
record, followed by work-list abstract interpretation of all reachable control flow. Execution starts
only after both succeed. The reference implementation in `sealed/reference/src/vm.js` is the proposed
replacement and its malformed-program tests live in `sealed/reference_tests/compiler_vm.test.js`.
