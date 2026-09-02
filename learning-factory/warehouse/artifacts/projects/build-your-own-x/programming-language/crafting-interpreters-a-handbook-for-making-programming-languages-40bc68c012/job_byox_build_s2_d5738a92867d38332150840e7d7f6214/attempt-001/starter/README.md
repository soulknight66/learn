# Starter workspace

The package under `src/main/java/org/learningfactory/mica` defines the required public surface and AST.
It intentionally compiles with unfinished core methods. Search for `TODO(student)`; implement in this
order:

1. `Lexer.scanTokens`
2. `Parser.parse`
3. `Interpreter.execute`
4. `BytecodeCompiler.compile`
5. `VirtualMachine.execute`

Supporting records and enums may be extended without changing their existing constructors/accessors.
Do not change observable language behavior or make one execution engine invoke the other. The public
suite is run with `../public_tests/run.sh` from this directory or `public_tests/run.sh` from the root.
