# Reference design

## Phase boundaries

`Tokenize` owns encoding, character, comment, escape, and source-size errors. It
walks bytes deliberately: the language permits UTF-8 inside strings but defines
positions in byte columns. A token retains both original `Lexeme` and decoded
`Literal`, so later phases never need to re-scan escape sequences.

`Parse` first validates the token-stream protocol: one final EOF and nothing
after it. Recursive descent mirrors the small grammar. The `depth` argument
counts open calls, allowing a literal inside the 256th call while rejecting a
257th call. Numeric range belongs here because tokens describe spelling while
the AST promises an `int64` value.

`Check` is a pure walk returning one type per top-level expression. The handful
of polymorphic rules are expressed explicitly. This is clearer than introducing
type variables for a language with no user-defined functions: `eq` requires two
equal argument types, `if` requires equal branch types, and `print` returns its
argument type.

## Code generation

Ordinary calls compile in post-order. Binary operations replace two operands
with one result, unary operations preserve depth, and top-level `POP` discards
all but the final expression. The compiler tracks current and peak operand-stack
depth alongside emission and records the peak in `Bytecode.MaxStack`.

Lazy forms have explicit control flow. In schematic bytecode, `if` is:

```text
condition
JUMP_IF_FALSE else     ; consumes condition
then-expression
JUMP end
else: else-expression
end:
```

Both branches begin at the same base depth and finish with exactly one value.
`and` and `or` use the same shape, with a constant on the short-circuited path.
Targets are absolute instruction indexes and are patched only after their
destination index is known.

## Verification and execution

The verifier first rejects globally invalid opcodes and jump destinations. It
then propagates abstract stacks of `ValueType` through reachable control flow.
Each instruction's stack effect is checked, and states joining at an instruction
must match exactly. A visited state is processed once; an equal revisit denotes
a loop, while an unequal revisit is malformed bytecode.

The VM retains runtime checks even after verification. This makes local
invariants explicit and avoids turning verifier mistakes into panics. It bounds
instructions, operand stack, and steps. A cyclic but type-correct program passes
structural verification and deterministically fails at the step limit.

The direct evaluator traverses the AST and implements lazy forms directly. It
shares value formatting and checked arithmetic helpers with the VM, but not
control flow. Differential tests compare returned values, emitted output, and
whether runtime failure occurred.

## Diagnostics

Every phase creates `StageError` at the node or instruction most closely tied to
the failure. Compile invokes checking rather than emitting partial code from an
invalid tree. VM verification happens before effects, so structurally malformed
bytecode cannot print before a bad alternative path is discovered.
