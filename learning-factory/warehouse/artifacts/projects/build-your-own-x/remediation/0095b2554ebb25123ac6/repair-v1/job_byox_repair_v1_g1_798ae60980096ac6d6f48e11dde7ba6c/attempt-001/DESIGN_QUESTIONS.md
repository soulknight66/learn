# Design questions

Write down your answers before or alongside implementation. These are intentionally unanswered in learner-visible material.

1. Which invariants belong to `Scan`, and which token-stream invariants must `Parse` recheck because its input is exported?
2. How will your parser distinguish top-level special forms from binary expressions without consuming tokens it later needs?
3. What cursor helper API prevents out-of-bounds access on every truncated token sequence?
4. How will spans be assembled for composite nodes, including missing closing delimiters?
5. At what exact point does a `let` name enter the symbol table, and how does that choice determine self-reference behavior?
6. How can `Compile` prove that the supplied `Analysis` belongs to the supplied AST without mutating or repairing either value?
7. What stack invariant holds after compiling each expression and each statement?
8. Which bytecode properties are structural and can be validated ahead of time, versus dependent on runtime values?
9. How will you detect every signed 64-bit arithmetic overflow without relying on wrapped results as if they were valid?
10. How will `Run` ensure partial printed output is not returned after a later error?
11. What state is allocated per call so concurrent `Run` invocations cannot interfere?
12. Which tests demonstrate deterministic errors when more than one problem exists?
13. How would adding lexical scopes or jumps change analysis, slot lifetime, and bytecode validation?
14. What evidence would be required before calling this educational VM production-ready?
