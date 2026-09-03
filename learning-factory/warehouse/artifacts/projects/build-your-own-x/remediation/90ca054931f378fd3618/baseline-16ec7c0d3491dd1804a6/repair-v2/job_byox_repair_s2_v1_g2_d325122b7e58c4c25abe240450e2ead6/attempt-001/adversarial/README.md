# Adversarial test exercise

Design black-box cases for boundaries that friendly examples miss.  For each
case, state whether it must fail during lexing, compilation, or execution and
which invariant should remain intact.

Cover at least:

- literals exactly at and one beyond `INT64_MAX`;
- all checked-arithmetic boundaries, including minimum divided by negative one;
- comments ending at EOF and non-ASCII bytes;
- 63- and 64-byte identifiers;
- 256 and 257 simultaneously live locals, plus many sequential scopes;
- jumps or operand reads at the final bytecode word;
- stack and heap endpoints;
- short-circuited expressions whose right sides would fail;
- zero, one, and exhausted instruction budgets;
- output produced before a later fault.

Do not assume compiler output is the only bytecode a VM can encounter.
Zero is a valid budget and must reach execution, which fails before dispatching
the first opcode with a source-located runtime diagnostic.
