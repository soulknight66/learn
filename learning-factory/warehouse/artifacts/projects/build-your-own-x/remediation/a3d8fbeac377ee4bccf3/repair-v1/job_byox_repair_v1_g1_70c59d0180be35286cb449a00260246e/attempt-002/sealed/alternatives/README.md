# Sealed alternative designs

## AST interpreter

Parse into nodes such as `TBinaryExpr`, `TIfStmt`, and `TWhileStmt`, then evaluate
them with an environment mapping strings to values. This removes jump
backpatching and makes source-level diagnostics natural. It teaches interpreters
well but does not exercise a compiler/VM interface, and recursive evaluation can
consume the Pascal call stack for deeply nested input.

## AST then bytecode

Use the same AST but add a separate resolver and emitter. This is the strongest
extension path: resolution can annotate each variable node with a slot, and
optimization can happen before lowering. It roughly doubles the reference's data
types and tests, so it was not selected for the core challenge.

## Pratt parser

A Pratt parser replaces one routine per precedence level with prefix/infix parse
functions and binding powers. Adding operators becomes table-driven, but the
control flow is less immediately recognizable to learners encountering parsing
for the first time. It produces the same bytecode for the current grammar.

## Register bytecode

Instructions could name destination and operand registers. This reduces VM stack
traffic and makes data flow explicit, but requires temporary allocation and a
more complex encoding. Stack bytecode better exposes expression evaluation and
keeps instructions compact for Mica.

## Native assembly backend

Native code would introduce calling conventions, executable-memory policy,
platform-specific assemblers, and process isolation. It adds little value to the
specified integer language and would make deterministic validation dependent on
host architecture. It is deliberately outside this artifact.
