# Reference tradeoffs

- **Portable bytecode versus native code:** a custom VM exposes binary layout and safety on every host,
  but does not teach object files, relocation, ABI rules, register allocation, or executable memory.
- **Recursive descent versus parser generation:** hand-written functions make precedence and diagnostics
  visible with no dependencies; grammar growth would increase repetition and recursion-depth risk.
- **AST before emission versus direct parsing to code:** the AST cleanly separates syntax from scope
  decisions. It costs memory and walks source structure more than once conceptually.
- **Integrated resolution/emission versus a resolved IR:** the reference is compact, but semantic errors
  can leave a discarded partial buffer and optimizations have no convenient intermediate form.
- **Monotonic slots versus reuse:** unique slots make shadowing and loop behavior obvious. Programs with
  many sequential blocks can hit the slot limit despite low simultaneous liveness.
- **Whole-file verification versus streaming:** global control-flow and stack proofs are straightforward,
  while memory use scales with both bytes and decoded instructions.
- **Absolute byte offsets versus labels in the file:** absolute offsets simplify VM dispatch and make
  corruption exercises concrete, but inserting instructions requires repatching downstream branches.
- **Checked arithmetic versus host arithmetic:** deterministic faults match the language on every Python
  build, at the cost of a range branch after arithmetic.
- **Step count versus wall-clock timeout:** instruction counts are deterministic and testable. They do
  not bound memory used during validation or time spent in output callbacks.
