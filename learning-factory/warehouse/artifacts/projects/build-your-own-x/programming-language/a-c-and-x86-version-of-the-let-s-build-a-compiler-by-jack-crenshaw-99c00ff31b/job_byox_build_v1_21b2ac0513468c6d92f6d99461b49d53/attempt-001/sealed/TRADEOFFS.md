# Reference tradeoffs

## One translation unit

The reference is intentionally one C file, making phase order and ownership easy
to inspect. The cost is broad internal visibility and slower navigation as the
language grows. A maintained tool should split source loading, lexer, parser,
semantic analysis, interpreter, and emitter behind narrow interfaces.

## AST before both backends

A shared tree and validation pass prevent semantic drift and make the
interpreter a useful oracle. Direct source-to-assembly parsing would use less
memory, but diagnostics, forward control-flow generation, and differential
testing would be harder. A bytecode IR would scale better than repeated AST
walks but adds another contract.

## Fixed arena versus individual allocation

The fixed arena makes addresses stable, cleanup constant-time, and the node limit
unambiguous. It eagerly allocates several megabytes even for an empty program.
A chunked arena would retain stable ownership while reducing small-program cost.

## Linear symbol lookup

With a hard limit of 256 variables, a linear table is simple, collision-free,
and predictably bounded. Hashing would matter with larger scopes or strings but
would require collision policy, owned keys, and deterministic iteration rules.

## Stack-machine expression emission

Using machine pushes keeps the backend small and directly mirrors expression
trees. It performs unnecessary memory traffic and complicates future calls
inside expressions. Register allocation or an explicit virtual stack would
improve code quality at considerable implementation cost.

## Host C runtime

Calling `printf` and `fputs` avoids writing integer formatting and platform I/O
assembly. It means output is not freestanding and binds generated code to the
x86-64 System V ABI plus compatible C runtime symbols. That portability boundary
is deliberate and documented.
