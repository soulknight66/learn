# VM-safety review answer

An empty program, fallthrough past the slice, invalid jump, ADD with fewer than
two operands, and HALT with an empty stack panic. Unknown opcodes never advance
and hang. Untyped values let ADD silently combine the wrong kinds. A backward
jump can run forever, and unbounded pushes (once added) can exhaust memory.

Preflight every opcode and target, then propagate an abstract typed stack from
entry across fallthrough and jump edges. Reject underflow, wrong kinds, paths
leaving the slice, bad halt shapes, and unequal stack signatures at joins.
Runtime must still enforce a step budget and hard stack depth because valid
loops and data-dependent paths cannot be made safe by slice bounds alone.
