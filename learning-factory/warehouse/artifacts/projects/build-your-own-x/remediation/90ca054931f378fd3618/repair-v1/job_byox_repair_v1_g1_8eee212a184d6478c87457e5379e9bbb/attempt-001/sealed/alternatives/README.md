# Alternative: arena AST evaluator

An alternative reference could parse into an arena of nodes, then evaluate statements directly.
Each expression node would contain a kind, source line, child indices, and literal/symbol payload.
Statements would include block ranges, branch children, and loop children. Calls would map names to
function-node indices after a resolution pass.

Advantages:

- grammar structure remains inspectable after parsing;
- unit tests can separate parsing from evaluation;
- source-oriented debugging and future syntax transformations are easier.

Costs:

- another bounded arena and its exhaustion cases are required;
- a deterministic “step” needs a new definition, such as one node evaluation or loop edge;
- deeply nested unary syntax can also deepen host recursion unless parsing/evaluation is made
  iterative;
- control transfer (`return`) needs an explicit tagged result propagated through evaluators.

This alternative was documented but not implemented or validated in this artifact.
