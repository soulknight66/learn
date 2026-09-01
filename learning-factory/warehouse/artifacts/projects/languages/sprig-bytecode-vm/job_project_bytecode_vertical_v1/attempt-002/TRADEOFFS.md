# Architecture comparison

Both implementations use identical model, lexer, parser, and integer-semantics source files
and expose the same API. The tree walker maps source structure directly onto Python calls, so
it is compact and easy to instrument with AST locations. Its recursive dispatch and repeated
tree traversal leave fewer optimization opportunities. The bytecode compiler pays an up-front
translation cost, makes control flow and stack state explicit, and can cache programs or add
peephole optimization. Its failure modes include bad patch targets and stack imbalance.

The benchmark stores raw timings rather than declaring a universal winner. These Python
implementations compare architecture, not C-vs-Python language performance. The supplied
smoke benchmark measures the complete public `run_source` path: lexing and parsing for both
engines, plus compilation for the bytecode engine. It does not isolate dispatch cost.
