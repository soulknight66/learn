# Adversarial exercise notes

The private suite covers the requested arithmetic, identifier, local-slot,
heap, jump, malformed operand, stack-underflow, and budget boundaries.  A
complete answer should additionally inject every opcode at each possible stack
height and generate grammar-aware token mutations.

Key oracles:

- `9223372036854775807` lexes; the next decimal integer does not.
- `-9223372036854775807 - 1` can construct `INT64_MIN` without overflowing;
  dividing or taking its remainder by `-1` must fail before host evaluation.
- `0 && load(4096)` and `1 || load(4096)` succeed without touching the heap.
- local slot 255 is valid only when the program metadata allocates 256 locals;
  slot 256 is never valid.
- a jump target equal to `code.count` is outside the code array.
- budget accounting charges opcodes, not operand words.

Bytecode mutation is tested directly through the VM API rather than by adding
a loader to the learner-facing CLI.
