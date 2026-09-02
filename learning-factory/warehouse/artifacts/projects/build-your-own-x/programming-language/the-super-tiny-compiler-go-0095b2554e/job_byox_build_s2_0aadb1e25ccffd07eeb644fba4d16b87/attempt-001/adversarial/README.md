# Adversarial validation inventory

Independent validators should add cases beyond the public examples:

- invalid UTF-8 before, inside, and after a quoted string;
- every escape at EOF, semicolons inside strings, CRLF input, and byte columns
  following multi-byte string/comment content;
- empty streams, early/multiple EOF tokens, forged token kinds, integer bounds,
  and exactly `MaxNesting` versus one level beyond;
- unknown built-ins, each arity on either side of the expected count, mixed
  `eq` types, and mismatched nested `if` branches;
- inactive branches containing division by zero or `print`, including nested
  `and`/`or` combinations;
- each checked arithmetic boundary and left-to-right output ordering;
- unknown opcodes in unreachable code, negative/end/out-of-range jumps, loops,
  fallthrough past the code slice, inconsistent join stacks, kind confusion,
  over-deep stacks, and malformed halt shapes;
- writers that return zero with an error or a short count, and nil writers;
- compiler/evaluator agreement over generated well-typed programs.

The sealed reference tests implement representative members of this inventory.
This list makes no claim that a fuzz campaign or external adversarial review ran.
