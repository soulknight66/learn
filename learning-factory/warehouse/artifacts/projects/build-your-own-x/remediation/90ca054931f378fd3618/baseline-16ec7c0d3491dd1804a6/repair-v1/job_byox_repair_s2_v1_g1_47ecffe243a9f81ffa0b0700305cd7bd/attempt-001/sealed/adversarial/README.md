# Adversarial exercise notes

The private suite has durable cases for every checked arithmetic failure,
identifier and local-slot boundaries, both heap endpoints, malformed operands,
invalid jumps, stack underflow and overflow, zero/exhausted budgets, retained
output before a fault, runtime prefixes, and the syntax-depth boundary for
grouping, calls, unary chains, blocks, `if`, and `while`.  It is still a finite
suite: it does not inject every opcode at every possible stack height or
perform grammar-aware mutation.

Key oracles:

- `9223372036854775807` lexes; the next decimal integer does not.
- `-9223372036854775807 - 1` can construct `INT64_MIN` without overflowing;
  dividing or taking its remainder by `-1` must fail before host evaluation.
- `0 && load(4096)` and `1 || load(4096)` succeed without touching the heap.
- local slot 255 is valid only when the program metadata allocates 256 locals;
  slot 256 is never valid.
- a jump target equal to `code.count` is outside the code array.
- budget accounting charges opcodes, not operand words.
- a zero budget is valid configuration and fails before the first dispatch.

Bytecode mutation is tested directly through the VM API rather than by adding
a loader to the learner-facing CLI.
