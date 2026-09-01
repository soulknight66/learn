# Design questions

Write down your decisions before implementing. These prompts have no learner-
visible answer key.

1. Which phase owns each required diagnostic, and how will later phases avoid
   reporting cascades based on invalid earlier state?
2. What invariant does every expression emitter promise about operand-stack
   depth? How will branches preserve it?
3. How will you represent source locations without retaining the entire token
   stream after parsing?
4. Will local slots be assigned during semantic analysis or emission? What makes
   allocation deterministic?
5. How will return analysis distinguish a terminating `if` from a conservative
   `while`?
6. How will forward labels and signed branch offsets be patched, and when will
   you detect overflow?
7. Which constant-pool entries must be interned? What order makes class bytes
   repeatable?
8. How will comparison code turn a conditional branch into canonical `0`/`1`
   without leaving mismatched stack heights at the join?
9. Where will nesting and size limits be checked so hostile input fails with
   `E_LIMIT` rather than a VM or host exception?
10. What tests distinguish true short-circuiting from a coincidentally correct
    boolean result?
11. Which pieces would change if Sprig gained block scope, user functions, or
    64-bit integers?
12. What trust boundary exists between compiler output and the class loader?

