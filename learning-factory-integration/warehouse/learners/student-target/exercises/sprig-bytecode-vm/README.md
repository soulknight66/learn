# Sprig: a bounded language and bytecode VM

Implement a small imperative language end to end: tokenize text, parse an AST, compile it
to documented stack bytecode, then execute it under a deterministic instruction budget.
The exercise is deliberately small enough to understand completely but includes contracts
that toy interpreters often omit: source locations, short-circuit control flow, checked
64-bit arithmetic, typed failures, undefined-name handling, and nontermination bounds.

## Progressive path

1. Read `REQUIREMENTS.md`, `GRAMMAR.md`, and `BYTECODE.md` without opening withheld material.
2. Complete the learner package in `starter` one stage at a time and run `public_tests`.
3. Write down bytecode and stack-height invariants before implementing jumps.
4. Run your own malformed-input and resource-budget experiments.
5. Intentionally reveal the reference and withheld tests, then compare the bytecode engine
   with the independent tree-walk alternative through their common API.
6. Reproduce the parser debugging incident, review the optimizer proposal, and benchmark
   both architectures on your own host.

The withheld tree is a progressive-disclosure boundary, not a hardened hostile-user
sandbox. Make a learner view by copying only the six learner documents, `starter`, and
`public_tests`. Generated code is educational and explicitly not production-ready.
