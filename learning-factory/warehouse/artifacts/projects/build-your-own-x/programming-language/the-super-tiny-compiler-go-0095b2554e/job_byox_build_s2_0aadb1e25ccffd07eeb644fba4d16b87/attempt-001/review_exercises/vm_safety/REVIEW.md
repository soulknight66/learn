# Review: compact VM loop

```go
for {
    instruction := code[ip]
    switch instruction.Op {
    case ADD:
        right := stack[len(stack)-1]
        left := stack[len(stack)-2]
        stack = append(stack[:len(stack)-2], left+right)
        ip++
    case JUMP:
        ip = instruction.Target
    case HALT:
        return stack[len(stack)-1], nil
    }
}
```

Questions: Enumerate panic, hang, and silent-corruption cases. Which checks can
be preflighted? Which limits must remain dynamic? Describe a typed control-flow
verification strategy.
