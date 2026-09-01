# Answer: review exercise 01

The addition itself has undefined behavior when the mathematical sum is outside `int64_t`, so the
subsequent comparisons cannot repair it. An optimizer may reason that defined signed addition does
not overflow and transform or discard wraparound-dependent logic.

Check before adding:

```c
if ((b > 0 && a > INT64_MAX - b) ||
    (b < 0 && a < INT64_MIN - b)) {
    return 0;
}
*out = a + b;
return 1;
```

The subtractions in the guards are representable because their branch constrains the sign of `b`.
Tests should include `MAX+0`, `MAX+1`, `MAX+(-1)`, `MIN+0`, `MIN+(-1)`, `MIN+1`, `0+MIN`, and
`0+MAX`, plus both operand orders where the language preserves evaluation order.
