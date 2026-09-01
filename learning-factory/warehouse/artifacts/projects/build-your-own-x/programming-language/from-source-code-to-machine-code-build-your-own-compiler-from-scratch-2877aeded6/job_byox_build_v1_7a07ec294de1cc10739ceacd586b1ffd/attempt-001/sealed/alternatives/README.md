# Alternative designs considered

## Pratt parser

A binding-power table would reduce expression parsing repetition and make future operators easier to
add. It was not selected because one function per published precedence row is easier to inspect in a
first compiler and needs no table conventions.

## Tree-walk interpreter first

Interpreting the AST before bytecode emission gives an excellent semantic oracle and isolates front-end
bugs. It was omitted from the shipped reference to avoid maintaining two execution semantics. A solver
can profitably build one as a temporary differential oracle.

## Register machine or SSA IR

A register target reduces stack shuffling and opens conventional data-flow optimization. It also needs
register naming, liveness, and a richer verifier. Minnow instead chooses a stack invariant that can be
checked with one abstract integer per program point.

## Native x86-64 output

Native emission would engage calling conventions, executable formats, relocations, and platform tools.
Those are valuable extensions, but they make deterministic cross-host validation and safe execution
substantially harder. The MNO1 format isolates compiler fundamentals before that step.

## Lifetime-based slot reuse

Scopes could return slots to a free list on exit. This reduces header counts, especially across sibling
blocks, but requires a proof that no emitted access outlives the declaration. Monotonic allocation was
chosen as the simpler reference invariant.
