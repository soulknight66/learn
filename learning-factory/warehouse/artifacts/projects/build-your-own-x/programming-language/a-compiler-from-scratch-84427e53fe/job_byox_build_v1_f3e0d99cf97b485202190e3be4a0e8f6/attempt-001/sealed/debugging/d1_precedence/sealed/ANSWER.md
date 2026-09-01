# D1 answer

Multiplication must be parsed by `factor`, and addition must call `factor` for each operand. If `factor` calls `term` or `term` folds `*`, the precedence direction is inverted. The AST root for `2 + 3 * 4` is `PLUS`, with literal `2` on the left and a `STAR(3, 4)` node on the right. Also test `10 - 3 - 2` as `(10 - 3) - 2` to catch right-folding.
