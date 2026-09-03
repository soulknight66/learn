# Exercise: scope lifetime

A learner implementation passes global binding tests but fails this parity observation:

```text
let x = 1; { let x = 2; x; } x;
```

The tree backend returns `1`; the VM either reports `x` undefined or returns `2`. Trace the scope
stack at every block instruction. Identify one invariant that would catch the defect earlier, then
write a regression covering both shadowing and outer assignment.
