# Adversarial evaluation stage

This stage probes behavior that ordinary examples often miss. It is a test
protocol, not a list of hidden cases or expected results. Reveal it after the
core parser, tree-walking interpreter, compiler, and virtual machine are
working.

## What an evaluator should probe

Run each applicable program through both execution paths and compare their
observable behavior:

- token boundaries involving whitespace, keyword-shaped identifier prefixes,
  multi-character operators, and end of input;
- precedence, left associativity, nested parentheses, and chained unary
  operators;
- `if` branches that must not evaluate the unselected arm, including a false
  conditional with no optional `else`;
- `while` loops with zero iterations, several iterations, and nested control
  flow;
- declaration and assignment errors, especially a `set` of an undeclared
  name;
- malformed source at several truncation points;
- bytecode jumps at the beginning and end of a block;
- deterministic exhaustion of a deliberately small step budget; and
- agreement between the tree and VM backends on emitted values and error
  categories.

Do not accept “both backends crashed” as parity. A comparison should distinguish
successful completion, a Pebble syntax/name/runtime error, and an unexpected
host-language exception. It should also require termination within the chosen
budget.

## Suggested reveal sequence

1. **Scanner/parser gate:** run token-boundary and malformed-source probes.
2. **Semantics gate:** run state, branch, loop, and error probes on the tree
   interpreter.
3. **Compiler gate:** require the same observations from both backends.
4. **Resource gate:** run only the explicit budget probes, with an outer process
   timeout as a last-resort guard.

Exact programs, expected observations, and the evaluator harness are sealed so
that this file does not turn the stage into a collection of answers.
