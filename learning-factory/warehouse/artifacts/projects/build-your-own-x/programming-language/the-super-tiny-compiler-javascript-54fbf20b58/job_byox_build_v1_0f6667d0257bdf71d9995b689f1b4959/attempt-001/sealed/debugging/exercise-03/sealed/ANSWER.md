# Exercise 03 answer: jump patching

Pebble jump operands are absolute, zero-based instruction indexes. The compiler
incorrectly stores a distance (`target - hole`) while the VM assigns that value
directly to `ip`. It can appear to work when `hole` is zero, but otherwise lands
too early. A loop back-edge must likewise store the absolute `loopStart`, not a
distance from the jump instruction.

One coherent repair is:

```js
function patchAbsolute(instructionIndex, targetIndex) {
  code[instructionIndex] = {
    ...code[instructionIndex],
    arg: targetIndex,
  };
}
```

Use that helper for conditional exits, the jump around an `else`, and loop
back-edges. VM dispatch then assigns the target to `ip`; it must not add the
target to the current instruction pointer.

The regression suite should make targets observable at block boundaries: empty
and single-instruction arms, a false `if` with no `else`, both outcomes of an
`if`/`else`, zero- and multi-iteration loops, and a body containing another
jump. A bytecode disassembly assertion complements behavioral tests by
verifying each computed target lies on an instruction boundary.
