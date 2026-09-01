# Exercise 01 answer

The trapping pair is dividend `INT64_MIN` (`-9223372036854775808`) and divisor
`-1`. The mathematical quotient is `9223372036854775808`, which does not fit in a
signed 64-bit destination. On x86-64, `idivq` raises a divide exception for both
zero and quotient overflow. Mica instead specifies a wrapped quotient of
`INT64_MIN` and remainder zero.

Before `idivq`, test the divisor for zero, then test the exact pair:

```asm
testq %rcx, %rcx
je runtime_division_by_zero
movabsq $0x8000000000000000, %rdx
cmpq %rdx, %rax
jne ordinary_divide
cmpq $-1, %rcx
jne ordinary_divide
# quotient: leave %rax unchanged; remainder: use zero
```

Only `ordinary_divide` executes `cqto; idivq %rcx`. The interpreter must likewise
check the pair before evaluating C's `INT64_MIN / -1`, because that C expression
has undefined behavior even though Mica defines it.
