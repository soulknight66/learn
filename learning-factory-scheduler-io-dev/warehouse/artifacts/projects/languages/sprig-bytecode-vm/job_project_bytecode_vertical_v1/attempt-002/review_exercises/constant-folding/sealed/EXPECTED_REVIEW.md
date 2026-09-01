# Expected review

**Blocker:** the pass recursively folds both operands before handling `&&` or `||`. It raises
division-by-zero for `false && (1/0)` although the language guarantees the RHS is unreachable.
Fold the left side first and fold the RHS only when source semantics would evaluate it.

**Major:** reconstructed AST nodes discard source provenance once locations are added, making
optimized-program diagnostics unstable. Define a location-preservation rule before landing.

**Major/design:** running guest arithmetic during compilation needs an explicit typed-error and
resource policy; it must not leak arbitrary host exceptions or permit unbounded compile work.
Add differential tests for every operator, overflow, errors, and short-circuit counterexamples.
