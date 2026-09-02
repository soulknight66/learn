# Sealed alternative designs

These are maintainers’ solution-bearing alternatives, not starter guidance.

1. Build an arena-owned AST, run a resolver that annotates identifier nodes with slots, then emit bytecode. This separates concerns and enables constant folding, at the cost of node ownership and another traversal.
2. Use Pratt parsing. Prefix and infix parselets make new operators easier to add, but function-pointer tables and binding powers are less transparent to a first C parser project.
3. Interpret the AST directly. That highlights environments and evaluation but omits the compiler transformation required by this challenge.
4. Emit a register-based IR with virtual registers. Instructions become easier to analyze while register allocation and operand encoding expand the project considerably.
5. Compile to portable C and invoke a system compiler. This demonstrates source translation but adds temporary-file, subprocess, timeout, toolchain, and diagnostic-remapping concerns.

The chosen direct stack-bytecode compiler is the smallest design that still distinguishes parsing, compilation, and interpretation.
