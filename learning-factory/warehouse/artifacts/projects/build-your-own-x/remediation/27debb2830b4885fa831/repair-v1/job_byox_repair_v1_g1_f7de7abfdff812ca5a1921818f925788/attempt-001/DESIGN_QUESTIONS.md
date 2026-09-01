# Design questions

Answer these before reading evaluator-only design notes.

1. Which token owns the location of a compound AST node, and why will that policy stay stable after
   grammar changes?
2. How will the parser count recursive depth without confusing it with ordinary expression length?
3. What stack invariant holds immediately after compiling any statement?
4. At a VM branch join, which abstract state must match besides stack height?
5. How can `and` and `or` return operands and still avoid evaluating the right side?
6. How will a compiled loop retain its last body value without growing the stack per iteration?
7. Should redeclaration check the full environment chain or only the current map? What observable
   language rule follows?
8. Which bytecode checks must happen before the first instruction can produce output?
9. How do tree steps and VM instruction steps differ, and what parity guarantee is realistic for
   limit failures?
10. What properties would you generate for differential testing while guaranteeing termination?
