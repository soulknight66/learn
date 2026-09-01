# Answer: permission predicate

The predicate rejects only when no requested bit overlaps. A read-only mapping therefore accepts a
request for `READ | WRITE`, despite lacking write access. The required subset predicate is:

```c
(mapping_flags & required_flags) == required_flags
```

A zero-bit request is satisfied by any present mapping, which also follows from that expression.
Unknown bits must be rejected before the subset test.
