# Answer: exercise 01

Immediately before the call, the stack is `[1, 41]`: index 0 is the caller's unfinished addition,
and index 1 is the one argument. The callee must own the argument range beginning at
`value_count - arity`, so its base is 1, not the current count 2.

With the buggy base, return sets `value_count` to 2 and pushes the result at index 2. The next add
pops indices 2 and 1, using stale argument storage instead of the caller's index 0. Depending on
cleanup details, this can produce a wrong value or a later underflow. The invariant is:

```text
callee.base = stack count immediately below the first argument
return: stack count = callee.base; push(return_value)
```

Compute `base = value_count - arity`, copy arguments from `base`, set `value_count = base`, and
record that same base. A useful regression is `print(5 + pair(20, 17));`, where `pair(a,b)` returns
`a+b`; the expected sole output is `42`.
