# Code-review exercise

Review the following hypothetical VM pattern without running it:

```c
int64_t op = code[pc++];
if (op == OP_JZ) {
    int64_t target = code[pc++];
    if (stack[--sp] == 0) pc = (size_t)target;
}
```

Prepare a review comment that identifies every trust assumption in these four
lines.  Rank findings by memory-safety impact, then propose a validation order
that does not itself perform an invalid conversion or access.  Also discuss
whether a non-taken branch permits an invalid target.
