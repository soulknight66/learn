# Reference design answers

## Pipeline

The reference uses four deterministic phases:

1. Read at most 1 MiB into an owned, NUL-terminated byte buffer while retaining the explicit
   length.
2. Lex into a fixed-capacity token table. Each token stores a source offset, byte length, line,
   kind, and (for literals) value.
3. Parse with one function per precedence level and emit stack bytecode directly. Record symbolic
   call patches, then resolve all calls after every definition has been compiled.
4. Start `main` in a bounded VM. Each instruction is budgeted before dispatch and carries its
   originating line for runtime diagnostics.

No generated phase trusts prose as state: token counts, code positions, symbols, patch targets,
stack depth, and frame count are represented in data structures and checked at mutation points.

## Answers to the design questions

1. A value-producing expression leaves exactly one value. Stores, condition jumps, pop, print,
   and return consume one. Binary operators consume right then left and publish one result. Calls
   replace their argument sequence with one return value.
2. A frame records the caller's next instruction and the operand-stack index below its arguments.
   Return reads its result, restores that stack index, removes the frame, pushes the result, and
   resumes at the saved address.
3. Tokens retain lines; every emitted instruction copies the operator or statement line. Compile
   errors use tokens and runtime errors use the current instruction.
4. Every call emits `OP_CALL -1` and a patch containing the copied name, argument count, line, and
   instruction index. A final pass requires one matching function and exact arity before replacing
   `-1`.
5. Capacity checks precede every token, opcode, symbol, patch, stack, and frame insertion. The
   loader rejects oversized source before allocation.
6. Loader failures return 66 before compiler allocation. Lexical, grammar, and resolution failures
   return 65. VM faults return 70.
7. Addition/subtraction compare operands against adjusted bounds. Multiplication divides a bound
   by one operand before multiplying. Negation catches `INT64_MIN`; division and remainder catch
   zero and the `INT64_MIN/-1` pair.
8. A step is one bytecode dispatch. The VM compares `steps >= max_steps` before fetching the next
   semantic action, then increments exactly once.
9. `if`, `else`, `while`, `&&`, and `||` patch numeric jump targets. Calls patch symbolic function
   targets. All instruction emission is bounded, so a recorded index remains in the fixed table.
10. `&&` emits a pop-and-jump-on-zero before its right operand; `||` similarly jumps on nonzero.
    Each branch emits a literal or `BOOL`, so its merge point always sees zero or one.
11. `sealed/reference/examples/meta_vm.mc` implements fetch, dispatch, stack state, faults, and halt
    in ordinary Mini-C. Running it through the host prints its guest result, `42`. The claim stops
    at staged nested interpretation.
12. Native calls would most directly expand the trusted surface because they can bypass every
    language resource and isolation rule. Pointers are close behind. Arrays and strings can remain
    bounded if designed as checked values rather than exposed host addresses.

## Bytecode table

`CONST`, `LOAD`, and `STORE` manage values and local slots. Arithmetic/comparison opcodes consume
their operands. `JZ`, `JNZ`, and `JMP` express control flow. `CALL` and `RET` manage frames. `POP`
balances expression statements, and `PRINT` is the sole observable language I/O operation.

The compiler is trusted to produce balanced code, but the VM still detects underflow, invalid
targets, invalid local indices, and capacity exhaustion. That duplication is intentional defense
against implementation mistakes.

## Namespace and scope

Each function has one namespace. Parameters occupy initial local slots and declarations append
slots. Nested braces affect control-flow grouping but do not create a new scope. Rejecting
shadowing makes a reverse lookup sufficient and matches the normative language contract.
