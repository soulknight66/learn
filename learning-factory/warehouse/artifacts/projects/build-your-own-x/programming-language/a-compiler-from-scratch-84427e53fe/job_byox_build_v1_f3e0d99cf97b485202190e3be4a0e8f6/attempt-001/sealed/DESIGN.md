# Design answers

1. **Resolution in compilation.** The parser should encode syntax without needing symbol-table state, while the VM should execute compact locations without repeated string lookup. Compilation is the stage that has both lexical structure and the need to choose slots.

2. **Stack effects.** `CONST` and `LOAD` are `+1`; `STORE`, `PRINT`, and `JUMP_IF_FALSE` are `-1`; binary operators are `-1` overall; unary operators, `JUMP`, and `HALT` are `0`. Every compiled statement has net effect zero, including both a loop back-edge and either arm of a branch.

3. **Declaration timing.** Deferring insertion lets an initializer resolve an outer binding of the same name and makes `let x = x;` fail when there is no outer `x`. Inserting first would permit an uninitialized self-read or silently change which declaration is referenced.

4. **Static versus dynamic verification.** Opcode, arity, constant domain, local bounds, jump bounds, presence of `HALT`, and—with a control-flow data-flow pass—stack depth/type consistency can be checked before execution. A division by a value that happens to be zero, overflow dependent on inputs, an uninitialized local along a feasible path, I/O failure, and budget exhaustion can remain dynamic.

5. **Short-circuit operators.** Add grammar levels between equality and the top expression rule. Compile the left operand followed by a conditional jump, while preserving or reconstructing the selected boolean result. Eager binary opcodes would be observably wrong once expressions gain effects or runtime failures.

6. **Functions.** Add declarations and calls, arity checks, call frames with an instruction return address, per-frame locals, and a value-return convention. Recursion needs independent frames. Lexical capture needs an environment/upvalue representation because a captured slot can outlive its declaring frame.

7. **Slot reuse.** Reuse reduces local storage but needs lifetime analysis and makes disassembly/debug state less direct. Monotonic slots are deterministic and easy to audit at this scale. A production compiler could deterministically reuse slots after scope exit if its verifier reasons about initialization at each program point.

8. **Source spans.** Keep a parallel instruction-index-to-span table on `Program`. That preserves the public instruction arrays and lets the VM attach a source location to dynamic errors. Branch patching must not desynchronize the table.

9. **Division tests.** Positive operands do not distinguish truncation from flooring. `-7 / 3 == -2`, `7 / -3 == -2`, and the corresponding remainders `-1` and `1` do. Checking `a == q*b + r` catches inconsistent quotient/remainder implementations.

10. **Hostile-input bounds.** Enforce source bytes before lexing, token count while scanning, parser nesting depth, AST/instruction/local limits during compilation, VM stack depth during verification/execution, and a positive step budget. A service should also bound wall time and output bytes outside the language engine.
