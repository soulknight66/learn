# Answer: asymmetric-operator failure

The compiler pushes the left operand first and right operand second, so the top
of stack is the right operand. The fragment assigns the first pop to
`LeftValue`, reversing operands. Addition and multiplication are commutative and
mask the reversal; subtraction, division, remainder, and ordered comparisons do
not.

The minimal correction is:

```pascal
RightValue := Pop;
LeftValue := Pop;
```

Keep zero checks against `RightValue`. Regression cases should include both
directions of an ordering (`2 < 3` and `3 < 2`) plus asymmetric arithmetic such
as `20 - 5` and `20 / 5`. A chained case such as `100 / 5 / 2` also checks parser
associativity and VM order together.
