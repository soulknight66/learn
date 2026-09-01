# Concepts behind Mica

## Lexing is boundary recognition

A lexer turns bytes into tokens while preserving source locations. The important
part is not recognizing `+`; it is deciding whether `!` is complete or begins
`!=`, whether `letter_2` is one identifier, and where an error belongs. Keep the
cursor invariant simple: it always identifies the next unread byte.

## Recursive descent mirrors precedence

Each expression precedence level can be one Pascal function. `ParseTerm` asks
`ParseFactor` for operands, so multiplication binds tighter than addition.
Loops implement left-associative binary operators; recursion implements
right-associative unary operators. The grammar is therefore executable design,
not merely documentation.

## Compilation can happen during parsing

Mica does not require an abstract syntax tree. Once a prefix expression or both
operands of an infix expression have been parsed, stack instructions can be
emitted directly. Structured control flow needs backpatching: emit a jump with a
placeholder, compile the body, then replace the placeholder with the known
instruction index.

An AST would make later optimization and richer diagnostics easier. Direct
emission keeps this challenge focused but makes source-level transformations
harder. Neither architecture changes the language contract.

## A stack VM makes order visible

For `2 + 3 * 4`, a compiler might emit:

```text
CONST 2
CONST 3
CONST 4
MUL
ADD
```

The VM pops the right operand after the left operand, performs the operation, and
pushes one result. Stating this convention prevents subtle reversal bugs in
subtraction, division, and comparison.

## Static and dynamic failures differ

An undeclared variable can be rejected without running the program, so it is a
compile error—even in unreachable code. Division by zero depends on values and is
a runtime error. Keeping these phases distinct improves testing and makes future
analysis passes possible.

## Language limits are semantics

The arithmetic domain and instruction budget are not incidental safety guards.
They make Mica portable across Pascal compiler settings and guarantee bounded
execution in a teaching harness. A language implementation is deterministic only
when edge cases are specified as carefully as happy paths.
