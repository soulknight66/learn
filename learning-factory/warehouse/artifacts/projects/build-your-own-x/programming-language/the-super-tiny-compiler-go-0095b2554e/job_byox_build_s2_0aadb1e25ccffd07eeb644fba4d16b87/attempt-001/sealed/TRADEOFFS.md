# Trade-offs and alternatives considered

## Typed instruction structs versus encoded bytes

An instruction struct makes stack effects and adversarial mutation easy to
teach and test. A packed binary format would better model serialization and
cache locality, but would add decoding, versioning, and endian concerns before
the language semantics are stable. The public `Bytecode` is therefore explicitly
an in-memory format.

## Recursive descent versus an explicit parser stack

The grammar maps cleanly to recursive descent and a strict nesting cap bounds Go
call depth. An iterative parser could support much deeper inputs, but complexity
would obscure the call-tree invariant. Total source size provides a separate
bound on node count.

## Preflight verification versus runtime-only checks

Runtime checks alone would miss malformed untaken branches and could perform
output before discovering structural corruption. Abstract stack propagation
front-loads those failures. Runtime checks remain as defense in depth and make
the executor robust if verification evolves.

## Shared arithmetic versus maximally independent interpreters

Sharing checked integer helpers prevents subtle policy drift between evaluator
and VM, but a defect in those helpers will agree in differential tests. Boundary
tests therefore assert overflow behavior independently. A higher-assurance
version could use `math/big` as a separate test oracle.

## Eager static checking of lazy branches

Both branches of `if` and the right side of `and`/`or` must type-check even when
runtime control flow skips them. This keeps expression types independent of
values and permits bytecode verification. Runtime errors and effects remain
lazy.

## Byte columns versus rune columns

Byte offsets slice source without conversion and align with Go strings. Byte
columns are less friendly for humans reading non-ASCII text, so the choice is
made explicit. A production diagnostic layer could report both byte offsets and
display columns.
