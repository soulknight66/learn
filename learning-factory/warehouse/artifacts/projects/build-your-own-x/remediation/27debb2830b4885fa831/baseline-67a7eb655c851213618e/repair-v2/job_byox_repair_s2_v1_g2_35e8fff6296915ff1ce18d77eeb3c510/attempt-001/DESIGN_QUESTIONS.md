# Design questions

Record your answers before reading instructor-only material.

1. Why does the token API retain both `lexeme` and `literal`? Which later stage owns escape decoding?
2. What invariant should hold between a parser function's entry and exit token index?
3. Why is `a = b = 4` parsed differently from `a - b - 4`?
4. Where should parentheses affect spans even though they do not require a dedicated AST node?
5. How will an environment distinguish an absent binding from a binding whose value is `nil`?
6. Should `let x = x;` see a previous outer `x`, the new uninitialized `x`, or fail? Relate your
   answer to the specified initialization order.
7. Which runtime rules should be shared conceptually between the tree evaluator and VM, and which
   code should remain independent so differential testing stays meaningful?
8. Write the stack effect of every opcode. Which effects differ across taken and untaken branches?
9. When compiling an `if` without `else`, where does the branch's `nil` value come from?
10. How can the compiler patch forward jumps without exposing mutable instruction objects in its
    returned result?
11. What must the VM validate before executing `LOAD`, `CONSTANT`, or `JUMP` from an untrusted chunk?
12. Which parity properties can public examples establish, and which require adversarial or
    generative tests?
13. If functions were added later, which current choices about scope storage and bytecode operands
    would become limiting?
14. What information would a production diagnostic need beyond a stable code and one span?
