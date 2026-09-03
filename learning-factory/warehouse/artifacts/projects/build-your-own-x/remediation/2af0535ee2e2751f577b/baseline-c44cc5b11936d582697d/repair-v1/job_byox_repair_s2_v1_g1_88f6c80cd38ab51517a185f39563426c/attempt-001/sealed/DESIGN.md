# Reference design and question answers

This file is sealed solution material.

## Pipeline

The CLI reads at most 1 MiB, then chooses token inspection or compilation. Compilation owns a `Lexer`, one current `Token`, a fixed `Program`, and a 64-entry symbol table. The parser emits stack bytecode directly. Normal mode passes the finished program to the defensive VM; disassembly mode does not execute it.

## Parser invariants

On entry, each parser function’s `current` is its first unconsumed token. On success, `primary`/`unary`/`term`/`expression` leave the first token outside that construct unconsumed. `parse_statement` leaves the first token after its semicolon unconsumed. Any failure latches exactly one diagnostic, and subsequent helpers stop mutating the program.

Emitting a binary opcode after parsing the right operand works because the left operand’s value is already below the right operand’s value on the stack. The VM pops right first, then left. Loops in `term` and `expression` emit after each right operand, giving left associativity.

A `let` name is checked for capacity and duplication before its initializer, but enters the table only after the initializer and semicolon compile and `STORE` emits. Consequently `let x = x + 1;` cannot see the new `x`.

## VM invariants

At statement boundaries the compiler-generated value stack is empty. `CONST` and `LOAD` add one value; `STORE`, `PRINT`, and `HALT` require the appropriate empty/nonempty state; binary arithmetic changes depth by -1; `NEG` preserves depth. Slots are in range and written once before reads.

The compiler cannot emit an unknown opcode, out-of-range slot, second store, load-before-store, stack underflow, early halt, or missing halt. The VM still checks all of these because its public C function accepts a `Program`, future compiler bugs are possible, and defensive failures are cheaper to diagnose than memory corruption.

## Arithmetic boundaries

Checks occur before the C operation. Representative failures are `INT64_MAX + 1`, `INT64_MIN - 1`, `INT64_MAX * 2`, `-INT64_MIN`, division by zero, and `INT64_MIN / -1`. Multiplication partitions operands by sign and compares against an appropriate quotient. Only a proven-safe operation is evaluated.

## Answers to extension questions

Mutable variables need an assignment statement, a policy for assignment as expression or statement, and either reuse of `STORE` or a distinct `SET` opcode. Name resolution would require an existing binding rather than introducing one.

Dynamic arrays need explicit owners, checked growth arithmetic, allocation-failure diagnostics, and cleanup on every compile exit. Fixed arrays instead make exhaustion predictable and remove lifetime branches.

Sprig preserves earlier output on runtime failure. This supports streaming and keeps memory bounded; a transactional contract would buffer output, define a buffer limit, and publish only on `HALT`.

Spans could point from an operator through its operand or from `let` through `;`, producing better highlights. Two endpoints per instruction/token increase metadata and require the parser to propagate closing positions.

Block scope needs scope-depth tracking, shadowing rules, and removal or hiding of bindings when a block ends. Forward references need a declaration collection/linking pass or unresolved relocations, so the current one-pass “lookup then emit” design is insufficient.
