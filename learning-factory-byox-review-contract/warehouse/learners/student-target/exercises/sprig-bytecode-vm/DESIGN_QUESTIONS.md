# Design questions

1. Which layer owns source locations, and how would locations survive into bytecode errors?
2. State a stack-height invariant for every opcode and control-flow join.
3. Should `let` inside a branch create a global? What migration supports lexical scope later?
4. Can a compiler reject all undefined names without rejecting valid control-flow programs?
5. Which work should consume the resource budget: AST visits, opcodes, allocation, output?
6. How would closures change environment ownership and instruction representation?
7. Which differential tests have an independent semantic oracle rather than mere agreement?
