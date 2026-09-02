# Review answer: signed division

Besides zero, x86-64 `idiv` traps for `INT64_MIN / -1` because the mathematical positive quotient is
not representable. For all other inputs, quotient truncates toward zero and remainder has the
dividend's sign. Verify both operands and trap cases before mutating stack depth; replace the lower
operand and decrement depth only after `idiv` succeeds.
