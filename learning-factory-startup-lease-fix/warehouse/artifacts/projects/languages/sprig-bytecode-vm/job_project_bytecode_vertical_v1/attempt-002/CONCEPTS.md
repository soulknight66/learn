# Concepts to extract

- A lexer turns characters into located tokens; a parser turns tokens into an AST according
  to precedence and associativity contracts.
- Compilation linearizes structured control flow. Forward branches require patching while
  stack-height invariants must agree at every control-flow join.
- An interpreter's dispatch architecture is independent from source-language semantics.
  Differential testing is useful because the tree-walk and bytecode paths fail differently.
- Host-language behavior is not automatically guest-language behavior. Integer bounds,
  negative division, errors, short circuit, and budgets need explicit definitions.
- A step limit is a deterministic availability boundary, not a security sandbox.
