# Sealed design alternatives

Three reasonable implementations were considered:

1. **Indirect threaded code:** each cell points to an assembly routine and a NEXT routine advances
   the instruction pointer. This is close to classic Forth architecture and reduces opcode dispatch,
   but exposes raw code pointers and makes validation less direct.
2. **Arena-relative bytecode:** use compact byte opcodes and 32-bit relative operands. This improves
   density, relocation, and target checking at the cost of more decoding and alignment work.
3. **Native x86-64 emitter:** compile each word into machine instructions. This offers the richest
   compiler exercise but requires an encoding layer, relocation records, instruction-cache and W^X
   policy, and substantially more security review.

The reference chooses 64-bit opcode cells and absolute in-process targets because the representation
is easiest to inspect in a debugger. An advanced learner extension should prefer arena-relative
targets before adding persistence or PIE.
