# Reference tradeoffs

## Plain-object AST

Plain objects are easy to inspect and serialize, and make public tests readable. They offer little
structural protection, so the interpreter and compiler validate the `Program` boundary and fail
closed on unknown node types. A larger language would benefit from a schema validator or typed
construction layer.

## String names in bytecode

`LOAD`, `DEFINE`, and `STORE` carry names directly. This keeps the compiler small and makes emitted
code teachable, but every access searches a scope stack. A resolver could replace names with lexical
depth and slot indexes, improving speed while adding a distinct analysis phase.

## Runtime scopes instead of compile-time slots

Explicit `ENTER_SCOPE` and `EXIT_SCOPE` preserve the tree evaluator's model and make scope bugs
observable. They are more dynamic than necessary for a language without closures. Static slots
would reduce maps and checks but complicate shadowing instruction examples.

## Shared semantic helpers

The reference evaluator and VM share pure operator, truthiness, and formatting helpers. That gives
strong consistency but can conceal a shared semantic bug from differential tests. Direct expected
value tests counter that risk. A production differential oracle might intentionally use fully
independent implementations.

## No parser recovery

The parser reports the first syntax error. This makes cursor invariants and diagnostics
deterministic for the challenge. An editor-facing parser should synchronize at statement boundaries
and return multiple diagnostics, which requires representing incomplete nodes safely.

## Bounded hostile bytecode

Mica source has no loops, but an externally supplied chunk could jump backward forever. The VM uses
a deterministic instruction budget. This guarantees termination but is not a general sandbox: a
future language with loops would need configurable fuel or a trusted-bytecode boundary.
