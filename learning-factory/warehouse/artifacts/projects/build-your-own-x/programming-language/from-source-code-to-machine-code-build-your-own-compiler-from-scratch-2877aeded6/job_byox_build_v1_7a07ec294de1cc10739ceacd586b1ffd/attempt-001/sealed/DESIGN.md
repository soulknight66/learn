# Reference design answers

## Front end

The lexer owns a character index plus one-based line and column counters. Trivia consumption treats CR,
LF, and CRLF as one logical line ending; token consumption never receives a newline. Identifiers and
digits use explicit ASCII comparisons so Python's broader Unicode character classes cannot silently
expand the language. Keyword classification happens after the complete identifier is scanned, and
integer range checking happens when the literal token is formed.

The parser is recursive descent. Each precedence row parses one tighter expression and then loops over
operators at its own level. Unary parsing recurses into itself. Statement lookahead distinguishes the
only identifier-led statement—assignment—from all keyword-led forms. AST leaves retain tokens so later
semantic errors have stable source locations.

## Resolution and emission

Resolution and emission share a traversal. A stack of dictionaries maps source names to numeric slots.
An initializer is emitted before its declaration is inserted, which implements the specified outer-name
self-initializer behavior. Assignment searches dictionaries from inner to outer. Allocation is
monotonic: it can use more slots than lifetime-aware allocation, but every declaration has one identity
across loops and branches.

Expression emission is postorder and leaves one stack value. Statements consume that value. Forward
jumps reserve four bytes and remember the operand byte position; patching writes a big-endian absolute
code offset. A loop records its condition's byte offset before emission and branches back to it.

## Verification and execution

Verification has two passes. The decoder establishes instruction boundaries and validates immediate
widths and slots. A work-list then propagates abstract stack depth over branch and fall-through edges.
It rejects invalid destinations, underflow, disagreeing merge depths, excess depth, early/nonempty
HALTs, and unreachable instructions before the VM receives a program.

The VM dispatches decoded instructions by address rather than decoding bytes again. It counts an
instruction immediately before execution, including `HALT`. Signed division uses absolute integer
division and reapplies the sign, avoiding floats and Python's floor-division rule. Every potentially
growing arithmetic operation passes through an explicit signed-64 range check.

## Interface

The Python API validates host types at its boundary. The CLI uses strict UTF-8 and converts expected
failures to exit status 2 without a traceback. Compilation reads and validates the complete source
before creating a temporary output; a flushed temporary in the destination directory is atomically
replaced into place, and failures clean it up.
