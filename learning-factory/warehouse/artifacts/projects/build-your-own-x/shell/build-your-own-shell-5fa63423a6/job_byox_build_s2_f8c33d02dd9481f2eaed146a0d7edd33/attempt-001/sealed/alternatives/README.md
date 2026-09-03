# Alternative implementation sketches

Two defensible extensions were considered but not implemented:

1. A recursive-descent grammar could add lists, logical operators, and subshells. It would introduce AST node variants and precedence while leaving word expansion as a separate phase.
2. A `posix_spawnp` executor could describe pipe duplication and closure through file actions. This is attractive in a future multi-threaded host but less direct for teaching post-fork descriptor inheritance.

Neither alternative should be mixed piecemeal into the reference. In particular, adding syntax without a distinct expansion model tends to blur whether a byte is data or an operator, while mixing `fork` and spawn ownership rules multiplies cleanup states.
