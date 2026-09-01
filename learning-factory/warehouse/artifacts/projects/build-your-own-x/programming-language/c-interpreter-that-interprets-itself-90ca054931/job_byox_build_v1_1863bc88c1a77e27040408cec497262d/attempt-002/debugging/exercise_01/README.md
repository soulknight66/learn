# Exercise 01: the disappearing left operand

A refactor changed call setup so the callee records its base as the current operand count, after
its arguments have been evaluated. Simple `print(id(42));` still works, but this program fails with
an operand-stack underflow at addition:

```text
int id(int x) { return x; }
int main() { print(1 + id(41)); return 0; }
```

The buggy setup is summarized below:

```text
base = value_count;
copy arguments from value_count - arity;
value_count = value_count - arity;
callee.base = base;
```

Trace operand indices across `CALL` and `RET`. Identify which values belong to the caller, define
the correct frame-base invariant, and propose a regression test involving both multiple arguments
and a preexisting left operand.
