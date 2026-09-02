# Reference design answers

## Representation

The reference is a freestanding ET_EXEC binary with `_start` and direct `read`, `write`, and `exit`
system calls. Source is read once into a 65,537-byte buffer so the implementation can distinguish an
accepted 65,536-byte stream from one byte too many. The scanner stores an index rather than a raw
cursor that can escape the input object.

Data cells, opcodes, and operands are 64-bit values. User names occupy fixed 32-byte slots with
separate lengths; completed-word body pointers occupy a parallel table. A linear scan is appropriate
for the specified maximum of 64 entries and makes exact byte comparison easy to audit.

## Compiler and publication

The compiler emits these cell sequences:

```text
RET                 [0]
LIT value           [1, value]
CALL dictionary-id  [2, id]
JMP target          [3, absolute-address]
JZ target           [4, absolute-address]
primitive           [opcode]
```

At `:`, the proposed name and starting body pointer are written into the currently unused dictionary
slot, but `user_count` is not incremented. Therefore normal lookup cannot see the incomplete word.
`recurse` emits the reserved current slot explicitly. At a valid `;`, `RET` is emitted first and only
then is the count incremented, which publishes the entry.

An `if` entry on the patch stack points to its JZ operand. `else` emits a JMP and placeholder, patches
the old JZ to the first else-body cell, and replaces the entry with the JMP operand. `then` patches
either accepted entry kind to the next cell and pops it. `;` requires an empty patch stack.

## Execution and internal convention

Small assembly helpers freely clobber `RAX`, `RCX`, `RDX`, and `R8`–`R11`. Compiler routines use
`R12`–`R14` as explicit temporaries across `emit_cell`; printing uses `R12`–`R13` for the `.s` loop
because its formatter does not modify them. This is a private convention, not the SysV function ABI;
there are no external function calls.

The VM instruction pointer, return depth, and remaining fuel live in dedicated storage. A CALL saves
the continuation in a 256-cell return stack, then loads a body pointer. This stack is independent of
both the language data stack and the CPU's `call`/`ret` stack. A top-level VM invocation resets return
depth and fuel; a compiled RET with no saved continuation returns to the interpreter.

## Failure discipline

Every store into input, data, name, code, patch, and return storage is preceded by a capacity check.
The decimal parser reports three states so a valid number, a word-shaped token, and an overflowing
digit string cannot be confused. Division checks zero and the `INT64_MIN / -1` trap before `idiv`.
Fatal paths perform a best-effort direct diagnostic write and exit 2; output helpers retry `EINTR` and
complete partial writes.
