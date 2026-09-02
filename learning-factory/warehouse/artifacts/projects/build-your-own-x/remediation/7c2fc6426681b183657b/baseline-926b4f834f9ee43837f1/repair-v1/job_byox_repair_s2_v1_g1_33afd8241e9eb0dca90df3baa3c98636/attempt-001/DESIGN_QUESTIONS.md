# Design checkpoint questions

1. Which registers are caller-owned in your internal convention, and where is that convention
   documented?
2. How does the tokenizer distinguish a comment marker at a token boundary from `#` inside a token?
3. How will decimal conversion distinguish “not a number” from “numeric spelling that overflowed”?
4. When does a new dictionary entry become visible, and what state exists during its compilation?
5. What exactly is stored after a literal, call, unconditional branch, and conditional branch?
6. What invariant does each patch-stack entry represent before `else` and before `then`?
7. Are branch targets absolute addresses, arena-relative offsets, or instruction indexes? What does
   that choice imply for relocation and validation?
8. How do the CPU stack, data stack, VM return stack, and compiler patch stack remain independent?
9. Which operation can trigger the hardware's signed-division overflow case, and how is it checked?
10. How do you prevent a recursive definition from running forever or overwriting the return stack?
11. What is observable on stdout, stderr, and the exit status for every failure class?
12. Which tests exercise boundary values rather than just representative values?
