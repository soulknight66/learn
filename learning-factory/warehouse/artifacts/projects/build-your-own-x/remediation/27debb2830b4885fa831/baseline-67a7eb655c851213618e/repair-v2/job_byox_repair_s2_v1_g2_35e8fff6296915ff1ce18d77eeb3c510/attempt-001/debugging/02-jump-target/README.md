# Exercise: jump target

An implementation evaluates true-branch conditionals correctly, but a false condition without an
`else` causes stack underflow at `HALT`. Draw the emitted instruction indexes for:

```text
if (false) { 7; }
```

Mark the stack depth on each control-flow edge. Determine what value every statement must leave and
where a forward jump should land.
