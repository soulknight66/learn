# Alternative: a stack bytecode

`bytecode.js` lowers the same checked AST to a small instruction array and interprets that array. It demonstrates that parsing and analysis can be reused while the backend changes completely.

Compared with direct tree walking, bytecode pays an up-front lowering cost but centralizes dispatch and makes jumps explicit. Compared with JavaScript generation, it keeps execution under application control and can count instructions, but it must define its own stack validation, resource ceilings, and debugging metadata.

The alternative handles short-circuiting with `DUP`, conditional jump, and `POP`: the left operand stays on the stack when it determines the result; otherwise it is removed before evaluating the right operand.

Reference-only test coverage is in `sealed/reference_tests/bytecode.test.js`.
