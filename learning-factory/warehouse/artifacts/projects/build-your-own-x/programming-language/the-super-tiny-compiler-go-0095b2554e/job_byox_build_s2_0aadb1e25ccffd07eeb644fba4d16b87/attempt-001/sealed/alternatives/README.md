# Sealed implementation alternatives

Three reasonable extensions were deliberately left out of the reference:

1. A tree-walking-only milestone could omit bytecode and focus on lexical scope
   and closures. It teaches interpretation well but provides no control-flow
   join or hostile-bytecode exercise.
2. A transpiler could emit Go expressions. That produces compact code but moves
   overflow, output, and diagnostics into a host compiler and makes sandboxing
   generated programs a separate security problem.
3. A register IR could assign every AST node a temporary and represent branches
   with basic blocks. It scales better toward optimization and SSA, at the cost
   of substantially more machinery for this expression-only language.

If variables are added, the preferred next step is lexical environments in the
interpreter plus `LOAD_LOCAL` instructions and verifier-tracked local types.
Persisted bytecode should wait for explicit magic bytes, schema versioning,
constant-pool limits, and compatibility tests.
