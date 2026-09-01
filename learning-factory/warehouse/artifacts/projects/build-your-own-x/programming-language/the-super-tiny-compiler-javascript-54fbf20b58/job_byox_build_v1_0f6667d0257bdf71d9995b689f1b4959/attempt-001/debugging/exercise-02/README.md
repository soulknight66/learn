# Exercise 02: binary associativity

Subtraction and division are specified as left-associative, but the parser
groups a run of equal-precedence operators from the right. The relevant
precedence-climbing loop has been reduced to this pseudocode:

```js
function parseExpression(minPrecedence = 0) {
  let left = parseUnary();

  while (isBinary(peek()) && precedence(peek()) >= minPrecedence) {
    const operator = consume();
    const right = parseExpression(precedence(operator));
    left = binary(operator, left, right);
  }

  return left;
}
```

Tasks:

1. Draw the AST produced for three operands joined by the same non-associative
   arithmetic operator.
2. Identify the single recursive-call argument that controls grouping.
3. Repair left associativity while preserving the documented precedence
   ordering and unary-expression handling.
4. Design tests that inspect both the AST shape and observable evaluation.

Do not special-case subtraction or division; the repair should express the
associativity rule in the parser algorithm.
