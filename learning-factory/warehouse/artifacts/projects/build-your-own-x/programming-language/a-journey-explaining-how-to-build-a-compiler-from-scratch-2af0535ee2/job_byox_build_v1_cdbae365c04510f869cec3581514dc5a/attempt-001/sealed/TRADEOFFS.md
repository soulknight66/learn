# Reference tradeoffs

## Instruction array versus packed bytes

Fixed-size instruction records make source mapping, patching, and validation obvious. They consume
substantially more memory than a byte opcode plus variable-width operands and are not a portable file
format. A production compiler would likely lower this IR into a versioned packed format after
validation.

## Stable slots versus slot reuse

Never recycling slots means shadowing and block exit have no runtime bookkeeping. It also means a
program with many sequential blocks can hit the symbol limit even though few locals are live at once.
Liveness-based reuse would reduce memory, but complicate name-resolution proofs and diagnostics.

## Direct parser emission versus an AST

Direct bytecode emission keeps allocation and cleanup small and teaches backpatching. It makes
multi-error recovery, source-to-source tooling, type checking, and optimization harder because syntax
structure disappears immediately. The alternative note describes an AST route.

## First diagnostic versus recovery

The compiler returns the first deterministic error. This avoids cascades and keeps output stable.
Interactive tooling would benefit from synchronization at semicolons and braces, with a bounded error
count, but recovery state adds substantial surface area to this exercise.

## Borrowed token names

Borrowing source slices eliminates per-token allocation and is safe because names are needed only
during compilation. Retaining debug symbol names in the program would require owned copies or an owned
source buffer.

## Absolute jumps

Absolute instruction indexes are simple and prevent signed relative-offset arithmetic. Inserting or
removing instructions after patching becomes expensive. Relative offsets work better for relocation
and compact serialization but need careful overflow checks.
