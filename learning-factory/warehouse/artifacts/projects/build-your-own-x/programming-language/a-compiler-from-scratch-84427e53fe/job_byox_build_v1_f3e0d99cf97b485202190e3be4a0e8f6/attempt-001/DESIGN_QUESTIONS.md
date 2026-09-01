# Design questions

Answer these after the public suite passes. Support each answer with a concrete Pebble program or bytecode sequence.

1. Why does name resolution belong in the compiler here rather than the parser or VM?
2. What stack effect does every opcode have, and what invariant should hold at each statement boundary?
3. Why must `let x = ...` add `x` only after compiling its initializer?
4. Which malformed bytecode can a pre-execution verifier reject, and which failures remain dynamic?
5. How would short-circuit `and` and `or` change the grammar and emitted control flow?
6. What changes are required to add functions with recursion and lexical capture?
7. Would you reuse local slots after leaving a scope? Discuss deterministic output, memory, debugging, and data-flow verification.
8. Where should source spans live so runtime errors can point back to source without changing the public instruction shape?
9. Which tests distinguish truncation-toward-zero division from floor division?
10. How would you bound source size, parser depth, stack growth, and loop execution in a service accepting hostile input?
