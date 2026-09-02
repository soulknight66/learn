# Debugging exercise: the disappearing overflow

A candidate backend emits the expression `a + (b + c)` using the sequence in
`candidate.s`. When `b + c` overflows, some programs continue instead of taking
the shared error branch.

Identify the instruction that destroys the relevant flags, state the invariant
the expression emitter violated, and propose the smallest correct reordering.
The answer for this exercise is kept in its own `sealed/` subdirectory.
