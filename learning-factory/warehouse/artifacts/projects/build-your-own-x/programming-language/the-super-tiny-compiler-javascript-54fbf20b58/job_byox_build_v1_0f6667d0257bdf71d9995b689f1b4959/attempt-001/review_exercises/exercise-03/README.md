# Exercise 03: trusting bytecode

The public `execute` function accepts a bytecode object and immediately
dispatches its instruction array:

```js
export function execute(code, options = {}) {
  const { constants, instructions } = code;
  const stack = [];
  let ip = 0;

  while (ip < instructions.length) {
    const instruction = instructions[ip++];
    switch (instruction.op) {
      case "CONSTANT": stack.push(constants[instruction.arg]); break;
      case "ADD": stack.push(stack.pop() + stack.pop()); break;
      case "JUMP": ip = instruction.arg; break;
      // remaining opcodes...
    }
  }
}
```

Review questions:

1. What happens for a missing instruction, unknown opcode, invalid operand, bad
   jump target, or stack underflow?
2. Which malformed programs can escape the source compiler but enter through
   this public API?
3. Should validation be eager, checked during dispatch, or both?
4. What must a bytecode format version and validator guarantee?
5. How should execution budgets interact with backward jumps?

Distinguish trusted compiler output from untrusted serialized bytecode when
assigning severity.
