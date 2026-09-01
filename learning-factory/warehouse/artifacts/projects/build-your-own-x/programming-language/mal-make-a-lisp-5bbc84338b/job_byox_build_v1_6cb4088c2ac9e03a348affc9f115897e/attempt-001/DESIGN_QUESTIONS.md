# Design questions

Write down your choices before implementing a milestone, then revisit them after its tests pass.

1. Which token owns the location for an unclosed list: the opening delimiter or end of input? Why?
2. How will parsing depth be bounded before Python raises its own recursion exception?
3. How will you keep the empty list distinct from `nil`, especially in `head`, `tail`, and truthiness?
4. Where should special-form shape validation live, and can malformed forms have side effects before
   failing?
5. What environment does a recursive function capture when `def` installs the function after creating
   it?
6. How will `set!` find the nearest binding without silently creating a new one?
7. What operations consume evaluator budget? Does your choice permit an unbounded builtin call?
8. How will call depth be restored when a function body raises an error?
9. Which equality cases need explicit type checks because Python considers booleans integers?
10. For truncating division, how can you avoid a float conversion for arbitrarily large integers?
11. What stack shape does each bytecode instruction require and guarantee?
12. During compiler backpatching, what invariant prevents a branch from landing outside the program?
13. Where will malformed bytecode be detected so that `IndexError` and `TypeError` never escape?
14. How can the CLI share one environment across forms without sharing execution budgets accidentally?
15. Which evaluator/VM differential cases give the most confidence without merely duplicating tests?
