# Instructor answer

`run` accepts a chunk directly, so compiler correctness does not establish operand safety. Missing
checks can yield `undefined` constants, arbitrary property access patterns, program-counter escape,
stack underflow values, global-scope removal, or nontermination through backward jumps. Keep checked
execution, or introduce a separate verifier that returns an opaque branded/encapsulated verified
chunk accepted by an internal fast loop. A JavaScript object property alone is not an unforgeable
brand; the boundary still needs encapsulation or repeated validation.
