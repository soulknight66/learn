# Design questions

Write down your choices before implementation. The public contract constrains behavior but deliberately
does not prescribe internal representation.

1. What fields does a token carry, and how will a token remain valid without allocating its spelling?
2. Which parser function owns each precedence level? Where is left associativity encoded?
3. How do you distinguish `=` from `==` and reject lone `&` without consuming useful recovery input?
4. When is a declaration added to the scope so `let x = x;` has the specified meaning?
5. What does a symbol-table entry own? How are shadowed bindings restored after `}`?
6. What is every opcode's stack effect? Which component verifies it?
7. What representation do jumps use, and what exact checks prevent an invalid patch or target?
8. Sketch bytecode for both `a && b` and `a || b`. Where does normalization to `0` or `1` happen?
9. Which arithmetic pairs need special checks before the C operation is evaluated?
10. Which limits apply during compilation and which during execution? What result code represents each?
11. How does the API avoid leaking a half-built program after failure?
12. Can one compiled program execute twice with different output streams? What state must be per-run?
13. How will error line/column positions stay stable at EOF and across `\r\n`?
14. What black-box tests would distinguish short-circuiting from eager evaluation?
15. Which fuzzing properties could be checked without treating crashes as the only failure signal?
