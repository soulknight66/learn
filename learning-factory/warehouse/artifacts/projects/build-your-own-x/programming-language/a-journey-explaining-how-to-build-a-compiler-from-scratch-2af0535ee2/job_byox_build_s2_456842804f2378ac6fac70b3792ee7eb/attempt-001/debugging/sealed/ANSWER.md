# Debugging answer

`left + right` itself has undefined behavior when the mathematical result is outside `int64_t`; later comparisons are therefore too late. The `sum > INT64_MAX` and `sum < INT64_MIN` comparisons are also tautologically false for an `int64_t` value.

A precondition check is safe:

```c
if ((right > 0 && left > INT64_MAX - right) ||
    (right < 0 && left < INT64_MIN - right)) {
    return 0;
}
*result = left + right;
return 1;
```

Cover `(MAX, 1)`, `(MAX, 0)`, `(MAX - 1, 1)`, `(MIN, -1)`, `(MIN, 0)`, `(MIN + 1, -1)`, mixed signs, and ordinary values. The subtraction in each guard is representable because its branch constrains the sign of `right`.
