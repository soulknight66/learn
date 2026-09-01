# Sealed tradeoffs

- **Direct class files vs a library:** Direct output exposes JVM mechanics and
  avoids dependencies, but it requires careful constant-pool and branch code.
- **Class version 49 vs current version:** Version 49 is loadable on Java 17 and
  removes `StackMapTable` construction from the exercise. It does not teach the
  modern frame format and should not be mistaken for a production target.
- **Single function vs general calls:** A fixed `run()` keeps the challenge
  centered on parsing, types, locals, and control flow. Functions would require
  signatures, call resolution, descriptors, and recursion policies.
- **First diagnostic vs recovery:** Stopping at the first lexical/syntax error is
  deterministic and prevents cascades. A production IDE compiler would usually
  recover and report several errors.
- **Two types represented as int:** This matches JVM conditional instructions
  and keeps local categories uniform. It relies on the type checker to prevent
  source-level confusion.
- **Function-wide uniqueness with path visibility:** Slot allocation and verifier
  state stay simple, at the cost of forbidding useful shadowing and mutually
  exclusive declarations with the same name.
- **Signed 16-bit branches only:** Rejecting an oversized branch is considerably
  simpler than rewriting conditionals around `goto_w`. The explicit `E_LIMIT`
  is preferable to corrupt output.
- **Recursive AST passes:** Depth budgets make recursion bounded and readable.
  An iterative representation would tolerate larger programs with more code.

