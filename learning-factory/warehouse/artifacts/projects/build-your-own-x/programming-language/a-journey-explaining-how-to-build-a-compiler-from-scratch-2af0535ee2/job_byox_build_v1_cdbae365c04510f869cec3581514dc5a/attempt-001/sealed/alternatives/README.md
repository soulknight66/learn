# Alternative designs

The included reference emits bytecode while parsing. Two useful independent routes are:

- Build an owned AST first, then resolve names and emit code in separate passes. This costs more
  allocation and cleanup but supports better recovery, tree inspection, and later optimization.
- Use a tree-walk interpreter as the first executable milestone. It avoids jumps and bytecode
  validation, making language semantics easy to test, then acts as a differential oracle for a later
  VM.

Another bytecode variant stores signed relative branch offsets and reuses local slots after lexical
scope exit. It is denser and can reduce VM local storage, but its compiler must prove offset arithmetic
and liveness. None of these representations should change black-box behavior in REQUIREMENTS.md.

An AST implementation should keep three ownership layers explicit: the source buffer, owned nodes, and
the environment used for one execution. A differential test can generate bounded valid expressions,
run both AST and bytecode engines, and compare result class, output, and diagnostic location.
