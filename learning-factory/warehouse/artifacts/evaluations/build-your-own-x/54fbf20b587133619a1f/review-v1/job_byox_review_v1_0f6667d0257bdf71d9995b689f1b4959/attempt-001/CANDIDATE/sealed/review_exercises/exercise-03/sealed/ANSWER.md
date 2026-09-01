# Exercise 03 answer: trusting bytecode

The loop assumes every array entry has a known opcode and correctly typed
operand. Missing entries cause host exceptions, unknown opcodes can become
silent no-ops if there is no `default`, `ADD` underflows into JavaScript values,
and an invalid target can skip validation, terminate accidentally, or create an
unbudgeted cycle. These are malformed-bytecode errors, not normal Pebble source
errors.

If `execute` is public, either explicitly accept compiler-produced opaque
objects only or validate external bytecode. A validator should check a format
version; array and instruction shapes; the exact operand type/range for each
opcode; finite integer jump targets on instruction boundaries; variable and
constant indexes; reachable stack depth with equal merge heights; and a known
terminal condition. Dispatch should still contain defensive underflow, opcode,
instruction-pointer, and budget checks because validation and execution may
evolve independently.

Backward jumps must consume budget on every dispatch (or on a documented fuel
instruction that cannot be bypassed), including jumps to themselves. Tests
should mutate valid compiled output one field at a time and assert a stable
bytecode-validation error rather than a JavaScript exception. Trusted output
reduces the exploitability rating but does not remove the correctness value of
these checks; serialized or caller-supplied arrays make it a high-severity
availability and boundary issue.
