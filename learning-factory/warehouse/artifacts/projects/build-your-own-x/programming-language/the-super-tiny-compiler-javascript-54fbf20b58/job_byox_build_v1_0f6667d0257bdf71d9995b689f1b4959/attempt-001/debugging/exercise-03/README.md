# Exercise 03: jump patching

Simple straight-line bytecode works, but a false `if` condition jumps to an
unrelated instruction when the conditional does not start at bytecode index
zero. Loop back-edges show the same location-dependent drift.

The compiler and VM use these conventions:

```js
// compiler
const hole = emit({ op: "JUMP_IF_FALSE", arg: -1 });
compileBlock(node.thenBranch);
patchArg(hole, code.length - hole);

// virtual machine
const instruction = code[ip];
if (instruction.op === "JUMP_IF_FALSE") {
  ip = pop() ? ip + 1 : instruction.arg;
}
```

Tasks:

1. Put absolute instruction indexes on a minimal conditional and trace the
   instruction pointer before and after the jump.
2. Compare the patched value with the bytecode contract for jump operands.
3. Make emission, patching, and execution share the absolute-target definition.
4. Add tests for an empty block, a one-instruction block, an `if` without
   `else`, an `if`/`else`, and a loop back-edge.

A repair that happens to fix only conditionals at bytecode index zero is
incomplete.
