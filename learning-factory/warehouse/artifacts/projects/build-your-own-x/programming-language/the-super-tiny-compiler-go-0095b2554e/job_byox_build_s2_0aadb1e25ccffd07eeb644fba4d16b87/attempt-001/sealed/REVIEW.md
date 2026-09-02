# Reference implementation review

## Scope reviewed

The review covers phase separation, deterministic diagnostics, integer edges,
lazy effects, stack accounting, untrusted bytecode, resource bounds, CLI input,
and test isolation. No production-readiness claim is made.

## Positive properties

- Lexing rejects oversized and invalid UTF-8 input before scanning and retains
  half-open byte spans through EOF.
- Parser, checker, compiler, evaluator, verifier, and VM all use explicit bounds
  or operate on already bounded structures.
- Type checking happens before emission/evaluation, while division and overflow
  remain runtime concerns.
- Conditional compilation gives every join one value at a consistent stack
  depth; the verifier independently checks this invariant.
- VM preflight covers reachable stack types and globally checks every opcode and
  jump target. Runtime execution still checks operands and stack growth.
- Output failures propagate as phase errors, and nil writers have documented
  suppression behavior.
- Test inputs include malformed token streams, depth and size boundaries,
  arithmetic edges, lazy errors/effects, joins, loops, writer failures,
  deterministic generation, and fuzz seeds.

## Residual concerns

- Validation could not be executed on this host because no Go command or
  formatter was exposed. Syntax, formatting, and behavior require independent
  confirmation.
- Abstract verification records one stack signature per instruction. That is
  appropriate for this typed stack machine, but new polymorphic or local-variable
  opcodes would require a richer lattice.
- There is no serialized bytecode format, compatibility version, source-file
  identity, structured diagnostic code, or cancellation API.
- Source and instruction limits are fixed exported constants rather than
  caller-specific budgets.
- The CLI emits Go's JSON representation of AST interfaces. It is stable for the
  current structs but not a promised interchange schema.
- String concatenation has no separate output-size budget. Source limits bound
  this variable-free language, but future variables or loops would change that.

## Review disposition

Suitable as sealed educational reference material after toolchain validation.
Not reviewed, transfer-verified, fuzz-campaigned, benchmarked, or productionized
by an independent harness. Manifest status correctly remains `GENERATED` and
`PARTIAL`.
