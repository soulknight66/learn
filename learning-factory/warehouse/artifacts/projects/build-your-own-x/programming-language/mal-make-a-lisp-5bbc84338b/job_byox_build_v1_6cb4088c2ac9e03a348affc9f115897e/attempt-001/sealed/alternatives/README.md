# Alternative designs considered

These alternatives are evaluator-only because they disclose solution structure.

- **Iterative reader:** maintain an explicit stack of list builders and quote markers. It avoids host
  recursion entirely but makes quote expansion and error ownership more stateful.
- **Tagged universal value:** represent every value as `(tag, payload)`. Equality and serialization
  become uniform, at the cost of wrapping integers/booleans and obscuring ordinary Python debugging.
- **Immutable environments:** return a new environment after each definition. This simplifies sharing
  but makes recursive `def` and observable `set!` require cells or a store-passing evaluator.
- **Continuation machine:** express evaluation as states and continuations. Tail calls and deterministic
  limits become natural; the initial interpreter milestone becomes substantially less transparent.
- **AST-to-AST lowering:** desugar `let`, `and`, and `or` into a small core before evaluation. It reduces
  evaluator cases but must preserve evaluation order, hygiene, and good diagnostics.
- **Closure-capable bytecode:** add local slots, `MAKE_CLOSURE`, captured cells, call frames, and
  tail-call instructions. This is the preferred extension when moving beyond the specified compiler
  subset.
