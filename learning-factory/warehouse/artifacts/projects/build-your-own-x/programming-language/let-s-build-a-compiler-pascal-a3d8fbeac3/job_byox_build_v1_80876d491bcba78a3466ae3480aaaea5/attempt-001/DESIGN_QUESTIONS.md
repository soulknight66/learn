# Design questions

Answer these before comparing against any sealed discussion.

1. Direct bytecode emission is compact, but what information would an AST retain
   for diagnostics, optimization, formatting, or alternative backends?
2. Mica uses one global scope. What data structure and compiler events would be
   needed for lexical block scope and shadowing?
3. Should `let x = expression;` make `x` visible inside its initializer? Compare
   the effects on recursion, accidental self-reference, and definite assignment.
4. Why must a conditional jump pop its condition? What stack-growth bug appears
   in a long loop if it only peeks?
5. How can jump backpatching remain correct when an optimization pass inserts or
   removes instructions?
6. Mica defines truthiness for all integers. What changes if conditions must have
   a distinct Boolean type?
7. Where should overflow be detected: source parsing, compilation, VM execution,
   or Pascal compiler flags? Which cases belong to each phase?
8. How would you prove that every emitted instruction has enough stack operands?
9. What additional metadata would let runtime errors show an expression span
   rather than one operator location?
10. If functions are added, which values belong in an activation record, and how
    would `call` and `return` affect the instruction budget?
11. Is deterministic bytecode output part of a language specification or only a
    tooling contract? What tests benefit from it?
12. How would you fuzz parser termination without mistaking the intentional VM
    instruction limit for a compiler timeout?
