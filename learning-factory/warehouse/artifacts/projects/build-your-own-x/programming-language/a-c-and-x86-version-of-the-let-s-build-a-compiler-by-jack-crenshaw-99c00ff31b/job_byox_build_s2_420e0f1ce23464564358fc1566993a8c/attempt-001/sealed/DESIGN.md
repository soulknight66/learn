# Sealed design answers

1. The loaded source buffer remains alive through parsing and resolution.
   Tokens borrow slices from it and store 1-based locations; AST identifiers
   are copied into an arena.
2. One recursive-descent function represents each precedence level. Loops at a
   level fold operators from the left, while unary and primary recurse.
3. Name resolution is a separate pass. Both execution backends therefore
   consume an AST whose variable nodes already contain numeric slots.
4. Fixed-size AST nodes and copied names use an arena. Statement-list vectors
   use `realloc` and are destroyed recursively before the arena is released.
5. The evaluator uses compiler overflow builtins before accepting signed
   arithmetic results. It guards zero divisors and `INT64_MIN / -1` before C
   division or remainder.
6. Expression emission leaves its result in `%rax` and has net-zero temporary
   stack use. A binary expression saves its left value with one push, emits the
   right value, then restores the left.
7. The prologue pushes `%rbp` and reserves a multiple of 16 bytes. Expression
   pushes are balanced before any libc call, so `%rsp` is aligned at call sites.
8. Before `idivq`, generated code rejects a zero divisor and the signed overflow
   pair. `cqto` then sign-extends `%rax` into `%rdx:%rax`.
9. A hidden stack slot begins at 1,000,000. Non-loop statements decrement it
   once; a loop decrements immediately before every condition evaluation.
10. Parsing and resolution finish before output is opened. Code generation
    writes an `mkstemp` sibling, flushes and syncs it, closes it, and renames it
    only on success.
11. Public cases establish only the CLI and representative semantics. Sealed
    tests cover boundary conditions, exact failure statuses, atomicity, and
    differential behavior.
12. A service still needs OS-level CPU, memory, file, syscall, and output
    limits. Language fuel alone does not sandbox the C compiler/linker or libc.
