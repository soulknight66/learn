# Design questions

Answer these before looking at implementation details.

1. Where will token locations live, and which phase owns source bytes?
2. How will the parser enforce left associativity without flattening all
   expressions into one precedence level?
3. Should declaration checking happen while parsing or in a separate pass?
   What becomes harder under each choice?
4. Which AST allocations can share an arena, and which resizable containers
   still need explicit destruction?
5. How will interpreter arithmetic avoid C signed-overflow undefined behavior?
6. What invariant will each expression code generator promise about `%rax` and
   temporary stack pushes?
7. How will generated code maintain 16-byte stack alignment at every libc call?
8. Which branches are required before `idivq`, and why?
9. How can the compiled loop use exactly the same step accounting as `eval`?
10. When compilation fails after opening its destination, what prevents a
    partial assembly file from being mistaken for success?
11. Which cases belong in public smoke tests, and which require adversarial or
    differential validation?
12. What additional sandboxing would be required before accepting arbitrary
    Pebble input in a service?
