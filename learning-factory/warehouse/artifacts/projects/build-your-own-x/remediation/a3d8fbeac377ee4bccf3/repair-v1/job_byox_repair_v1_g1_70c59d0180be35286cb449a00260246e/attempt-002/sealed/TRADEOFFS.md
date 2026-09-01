# Sealed tradeoff analysis

## Direct emission versus an AST

Direct emission minimizes types and allocations and makes the stack discipline
visible to a learner. The cost is tight coupling between grammar and backend.
Mica's reference chooses direct emission because the language has one value type,
one backend, and no optimization promise. An AST is the preferred next change if
functions, source-to-source tooling, type checking, or optimization are added.

## Flat slots versus environments

Compile-time integer slots make loads deterministic and cheap. A linear name
search is acceptable for this bounded teaching language and avoids hash-table
iteration concerns. It scales poorly to large programs and cannot represent
shadowing. Production work would use scoped symbol tables and impose explicit
limits on names and slots.

## Token arrays versus streaming tokens

Keeping all tokens enables simple lookahead and debug output and cleanly
separates lexer errors from parser state. It costs memory proportional to the
source and duplicates lexemes. A streaming lexer plus a small lookahead buffer is
more memory-efficient but complicates `--tokens` and error recovery.

## Source points versus spans

One line/column pair per instruction is compact and meets the diagnostic
contract. It cannot highlight complete subexpressions or distinguish generated
control-flow instructions. Full byte offsets and a line index would improve
diagnostics and allow excerpts without changing VM values.

## Narrow arithmetic domain

The ±1,000,000,000 domain makes all intermediate calculations safe inside Int64,
so checks do not depend on host overflow behavior. This is more restrictive than
an ordinary 64-bit language. A full Int64 design needs checked addition,
subtraction, multiplication, and the `MinInt64 div -1` case before performing an
operation that the host compiler might overflow.

## Instruction budget

A semantic step cap guarantees bounded evaluation and makes infinite loops
testable. The exact limit can surprise normal programs and is not a substitute
for a harness wall-clock timeout: one instruction could become expensive after
future extensions. Both controls are appropriate at an untrusted-code boundary.

## Error recovery

The reference stops after the first error. This keeps bytecode from being emitted
from a corrupted parser state and gives stable CLI behavior. An editor-oriented
compiler should synchronize at semicolons/braces, retain multiple diagnostics,
and suppress cascades; that requires a richer result type than exceptions.
