# Exercise 02 answer: binary associativity

With three equal-precedence operands, passing the operator's unchanged
precedence into the recursive call allows that call to consume the following
operator. The resulting tree is `left op (middle op right)`, which is
right-associative.

For left-associative operators, the right operand must be parsed at a strictly
higher minimum precedence:

```js
const operator = consume();
const operatorPrecedence = precedence(operator);
const right = parseExpression(operatorPrecedence + 1);
left = binary(operator, left, right);
```

The outer invocation can then consume another operator at the original level,
producing `(left op middle) op right`. Parentheses remain primary expressions,
and unary parsing remains the seed for the binary loop, so neither needs a
special case. If the language later gains a right-associative operator, encode
associativity in operator metadata and choose the right-hand minimum from that
metadata instead of reverting the fix globally.

Tests should assert the nested AST direction for subtraction and division,
observable results for equal-precedence chains, and mixed-precedence cases in
both directions. Parenthesized counterexamples prove that explicit grouping
still overrides the default.
