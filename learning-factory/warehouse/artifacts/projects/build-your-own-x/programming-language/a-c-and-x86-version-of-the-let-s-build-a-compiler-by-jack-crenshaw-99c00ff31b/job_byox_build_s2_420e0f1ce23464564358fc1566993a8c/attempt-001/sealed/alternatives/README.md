# Sealed implementation alternatives

Three reasonable architectures were considered:

1. Compile to a compact bytecode and interpret a virtual stack. This makes
   control flow and differential checking simple, but postpones the x86/ABI
   objective.
2. Lower the AST into basic blocks with three-address values, then select x86
   instructions. This is the best route toward optimization and multiple
   targets, at the cost of substantially more infrastructure.
3. Emit Intel-syntax NASM source. It may be more familiar to some learners, but
   adds a tool dependency not present on every Linux C environment.

The reference chooses direct GNU/AT&T assembly because it can be linked through
the host C compiler and exposes the correspondence between an AST node and its
machine operations. A useful extension is a bytecode backend used as a third
semantic oracle, not as a replacement for the interpreter tests.
