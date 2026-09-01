# Answer

The handler mutates the stack before proving that two operands exist, so depth zero or one can read
outside live stack state and a failure can partially change depth. It also omits the sole signed
idiv overflow case: -9223372036854775808 divided by -1 raises a processor exception instead of the
language's status-7 diagnostic.

First require depth at least two without changing it. Load the top cell as divisor, reject zero, then
load the next cell as dividend. Compare the pair against signed-minimum and -1 and report arithmetic
overflow if equal. Only then execute cqo/idiv, replace the lower cell with the quotient, and decrease
depth by one. Tests should cover both missing-depth cases, zero, the overflow pair, and all four sign
combinations to confirm truncation toward zero.

