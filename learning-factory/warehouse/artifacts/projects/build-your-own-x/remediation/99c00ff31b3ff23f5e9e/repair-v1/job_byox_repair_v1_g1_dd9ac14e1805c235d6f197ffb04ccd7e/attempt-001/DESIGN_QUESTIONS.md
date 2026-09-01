# Design questions

Record your answers before implementation and revisit them after differential
testing.

1. What invariant will each parser function guarantee about the current token
   on success and on failure?
2. Will AST nodes own copied identifier text or refer to a source buffer? Which
   object outlives which?
3. How will you enforce node and nesting limits without partially initialized
   nodes leaking?
4. What representation makes every 64-bit Mica bit pattern safe to manipulate
   in C?
5. Where will declared-before-use validation live so that both backends share
   it?
6. How will variable names map to storage slots, and what makes that mapping
   deterministic?
7. State the stack-alignment invariant immediately before every emitted `call`.
8. Which labels are needed for an `if` without `else`, an `if` with `else`, and
   a `while`?
9. How will interpreted and compiled division agree on zero and on
   `INT64_MIN / -1`?
10. What data should a failing differential test preserve so the mismatch can
    be reproduced without randomness?
