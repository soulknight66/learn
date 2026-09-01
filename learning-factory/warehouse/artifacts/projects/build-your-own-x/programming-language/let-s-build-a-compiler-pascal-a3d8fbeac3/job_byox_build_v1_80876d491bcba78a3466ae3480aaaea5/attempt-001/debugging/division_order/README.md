# Exercise: the asymmetric-operator failure

A VM passes tests for addition and multiplication but reports:

```text
print 20 / 5;   # observed 0 instead of 4
print 20 - 5;   # observed -15 instead of 15
```

Inspect `broken_vm_fragment.pas`. Identify the invariant it violates, explain why
symmetric operators hid the bug, and propose the smallest correction. Then name
two comparison tests that would prevent regression. Do not consult sealed answer
material while doing the exercise.
