# Sealed design notes

## Pipeline

The reference facade validates the output class name, then runs four strict
stages: `Lexer`, `Parser`, `Analyzer`, and `ClassEmitter`. Expected input errors
cross the internal boundary as one `CompileFailure`; the facade turns that into
an immutable `CompilationResult`. Internal invariant failures remain exceptions
because converting compiler bugs into user diagnostics would hide defects.

## Front end

The lexer owns character, integer-range, token-count, and physical line/column
rules. In particular its `advance` operation consumes CRLF atomically. The
parser mirrors the precedence grammar with one loop per left-associative level.
It attaches each node’s leading position and stores an O(1) expression depth so
long flat input cannot quietly create an unbounded recursive AST.

The parser accepts exactly one fixed entry point. This keeps function tables,
descriptors, invocation, and linkage out of the core exercise while still
producing a real JVM artifact.

## Semantic analysis

The analyzer keeps a deterministic function-wide symbol table. A separate set
describes names visible on the current path. Each `if` analyzes independent
copies and intersects continuing paths; if one side returns, only the other side
reaches the join. Loop-body declarations do not escape. This policy both defines
the language and ensures the bytecode verifier never observes a load from an
uninitialized local.

Every local receives its slot at declaration analysis in source traversal order.
Both source types use one JVM integer slot. The analyzer checks expression types,
duplicate names, declaration visibility, local limits, unreachable statements,
and whole-function return behavior before emission.

## Backend

The backend builds a minimal public final class containing only
`public static int run()`. Version 49 avoids mandatory stack-map frames, but the
emitter still maintains type-compatible control-flow joins. It interns constant-
pool entries in insertion order, emits big-endian class structures, and computes
`max_stack` from recursive expression contracts.

Forward labels retain opcode positions for later patching. JVM conditional and
unconditional branch offsets are relative to the opcode address. Comparison
sequences branch to an `iconst_1` path and otherwise produce `iconst_0`.
Short-circuit sequences branch after the left operand and therefore never
evaluate a needless right operand.

The semantic pass guarantees a terminating top-level path, which lets the
emitter avoid dead synthetic returns. It also uses termination information to
avoid placing a dangling join after two returning `if` branches.

## Determinism and errors

There are no timestamps, source filenames, debug attributes, random identifiers,
or unordered constant-pool traversals. Equal inputs produce equal bytes. Size
checks cover tokens, syntax nesting, locals, constant-pool entries, branch
offsets, and method code. Class bytes are copied both into and out of the result.

