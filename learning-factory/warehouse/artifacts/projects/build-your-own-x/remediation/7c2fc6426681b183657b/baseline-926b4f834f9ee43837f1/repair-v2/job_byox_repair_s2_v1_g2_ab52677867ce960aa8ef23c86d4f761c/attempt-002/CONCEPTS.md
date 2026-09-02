# Concepts

## One token, two modes

A Forth front end can use the same tokenizer while switching between interpretation and
compilation. In interpretation mode a number is pushed and a known word runs now. In compilation
mode each token emits an instruction or operand into a bounded arena. Keeping this mode transition
explicit prevents punctuation such as `;` from acquiring ambiguous behavior.

## Dictionary design

A dictionary maps token bytes to either a primitive operation or a user-word body. A compact
educational implementation can linearly scan fixed tables. The important details are storing the
length separately, comparing exact byte sequences, rejecting duplicates, and publishing a new word
only when compilation is complete.

## Threaded virtual machine

Compiled bodies may be represented as cells. Some cells select operations; others are operands such
as literals, dictionary indexes, or branch targets. A VM instruction pointer walks those cells. A
separate return stack holds continuation addresses for user-word calls, leaving the CPU stack for
assembly subroutines.

## Backpatching structured control flow

When the compiler encounters `if`, the branch destination is not known. It emits a conditional
branch plus a placeholder and remembers the placeholder location. `else` and `then` resolve pending
locations. A typed patch stack makes nesting deterministic and detects mismatched control words.

## Boundaries are semantics

Assembly removes many automatic safety rails. Input size, token length, stack depth, code capacity,
return depth, arithmetic traps, partial writes, and execution fuel all need deliberate policies.
Checking a limit after a store is too late: every pointer-producing transition should establish the
valid range before memory access.
