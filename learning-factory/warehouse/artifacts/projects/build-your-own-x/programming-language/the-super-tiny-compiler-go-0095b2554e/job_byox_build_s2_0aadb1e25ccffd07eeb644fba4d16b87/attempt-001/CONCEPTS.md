# Concepts to master

## Tokens are a lossless boundary

A lexer classifies characters before the parser assigns structure. Source spans
make this boundary observable: every later diagnostic can point back to original
text rather than a reconstructed approximation. Decide carefully whether the
lexer or parser owns numeric range checks and string unescaping.

## Recursive syntax, bounded resources

Prefix calls map naturally to a recursive AST because parentheses expose the
tree directly. Natural recursion is not automatically safe recursion. Track
nesting explicitly and distinguish an unexpected closer from an opener that
never closes.

## Static meaning versus runtime behavior

Parsing answers “what shape is this?” Type checking answers “is this operation
meaningful?” Runtime evaluation handles facts static analysis cannot settle,
such as a zero divisor. Keeping the phases separate makes failures reproducible
and easier to test.

## Compilation as stack accounting

Post-order traversal turns expression trees into stack operations. Every
instruction has a stack effect. Branches add a control-flow constraint: all
paths reaching a join must agree on stack shape as well as value type.

## Laziness is observable

`if`, `and`, and `or` do not merely compute values; they decide which effects or
errors can occur. An eager implementation can return the right answer on simple
inputs while still printing too much or evaluating a forbidden division.

## Two semantics, one language

A direct interpreter and a bytecode VM are separate implementations of the same
language. Comparing their values, output, and failures is a strong test oracle,
provided they do not accidentally share all the same decision-making code.

## Hostile bytecode

The compiler may be trusted by the VM in a toy demonstration, but the required
API makes bytecode public. Defensive execution validates opcodes, operands,
jumps, stack effects, and resource limits instead of assuming its caller was the
compiler.
