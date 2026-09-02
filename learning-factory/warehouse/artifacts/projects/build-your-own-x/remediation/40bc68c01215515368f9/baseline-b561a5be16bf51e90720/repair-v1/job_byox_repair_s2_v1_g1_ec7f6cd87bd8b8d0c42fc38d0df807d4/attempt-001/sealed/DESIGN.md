# Reference design answers

Mica carries location on every token and copies the relevant token location into each instruction.
Thus scanner/parser errors point directly into source, while VM runtime errors use the operator or name
that emitted the current opcode.

Each opcode has a checked stack contract. Constants push one value; unary operators replace one;
binary operators replace two with one; `DEFINE` and `PRINT` consume one; `GET` pushes; `SET` preserves
the assigned expression value. Conditional jumps inspect without consuming, letting the compiler emit
an explicit `POP` on each resolved control-flow path.

`let x = initializer` evaluates first and defines second. In a nested block, `let x = x;` therefore
reads an existing outer `x`; at top level it fails. Redeclaration is checked only after evaluation.

Both engines charge one unit per executed statement and fail before unit 100,001. The compiler emits a
located `TICK` before every statement, including blocks, so loops and branches charge at exactly the
same semantic points. The VM separately caps instructions dispatched since the most recent `TICK` to
contain cyclic malformed bytecode. The cap is at least the bytecode length, so it cannot preempt an
acyclic compiler-produced path; each successful `TICK` resets it and the shared semantic budget remains
the governing limit for compiler-produced loops.

Forward jumps are patched by replacing an immutable `Instruction` record at its list index. Before
execution, the VM validates every instruction and constant, including unreachable entries, for opcode,
operand shape, jump/constant range, and location. Dynamic checks enforce stack availability and scope
balance on the executed path and require a structurally balanced state when `HALT` is reached.

Equality is total across Mica values: mixed kinds are unequal, `nil` equals itself, and numeric equality
uses primitive `double ==`, so negative zero equals positive zero. Division errors point at `/`.
