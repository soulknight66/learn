# Design questions

Write down your decisions before reading any sealed material.

1. Which layer owns source locations, and how do locations survive compilation?
2. What stack effect does each opcode have? How will the VM detect underflow?
3. For `a or b`, which jumps and pops are required on the true and false paths?
4. Should `let x = x;` inside a shadowing block read the outer `x` or fail? Which rule in the contract
   determines that answer?
5. How will both engines enforce the execution limit without producing off-by-one differences?
6. What is the equality result for `1 == "1"`, `nil == nil`, and `-0 == 0`?
7. At which token should a division-by-zero error point?
8. How should the compiler patch a forward jump without exposing a mutable instruction object?
9. What invalid bytecode states can be constructed through the public records, and where are they
   rejected?
10. Which tests distinguish dynamic scope from lexical scope even though Mica has no functions?
