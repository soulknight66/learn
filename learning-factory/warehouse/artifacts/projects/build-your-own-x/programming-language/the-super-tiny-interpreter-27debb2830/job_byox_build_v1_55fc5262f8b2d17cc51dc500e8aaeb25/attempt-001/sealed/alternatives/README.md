# Sealed alternatives

The main implementation compiles every expression literally. `constant-folding.js` demonstrates an
optional immutable AST pass that folds only operations which can be proven successful. It is kept
separate because optimization is not required and must never change the timing of language errors or
short-circuit evaluation.

Other viable designs include a Pratt parser, lexical-address resolution before evaluation, a register
VM, or tagged instruction arrays. Each would need the same observable contract and untrusted-input
limits.
