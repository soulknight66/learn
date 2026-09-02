# Design questions

Write down your decisions before implementing each stage. These prompts do not
have a single required wording, but your implementation must still satisfy
`REQUIREMENTS.md`.

1. Which phase owns each error: invalid UTF-8, an out-of-range integer, an
   unknown built-in, and division by zero? Why?
2. What invariants should hold for every token span, including EOF and escaped
   strings?
3. How will the parser enforce a depth limit without confusing depth with total
   AST size?
4. What representation lets a type checker describe the polymorphic rules for
   `eq`, `if`, and `print` without pretending the language has full generics?
5. For every opcode, what values does it consume and produce? What must be true
   where two control-flow paths rejoin?
6. How will you patch forward jump targets while keeping disassembly stable?
7. What bytecode validation belongs in a preflight pass, and what can only be
   checked on an executed path?
8. How do you guarantee short-circuit behavior in both the interpreter and the
   compiler without duplicating side effects?
9. Should a failed `print` leave a value on the stack? What can callers observe?
10. Which pieces may be shared between interpreter and VM without weakening
    differential testing too much?
11. How would adding lexical variables change the AST, checker environment,
    instruction set, and maximum-stack calculation?
12. What compatibility promises would you make before persisting bytecode?
