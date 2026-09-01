# Reference design answers

This is evaluator-only rationale for the questions in `DESIGN_QUESTIONS.md`.

1. An unclosed list points to its opening parenthesis. That location identifies the construct whose
   obligation was not fulfilled; end-of-input has no token to carry a stable position.
2. The parser passes an explicit depth through list and quote recursion and checks before descending.
   A final `RecursionError` translation is defense in depth, not the intended limit mechanism.
3. `nil` is Python `None`, while an empty Sprig list is `[]`. Truthiness tests identity with only
   `None` and `False`; it never calls Python `bool`.
4. Each special form validates its complete structural shell before evaluating children. In
   particular, `let` checks every pair and duplicate before any initializer can mutate state.
5. `fn` closes over the current environment object. `def` then mutates that same object, so the newly
   installed function can find its own name during recursive calls.
6. Environment lookup returns the environment/key pair. Assignment walks parent links and errors at
   the root; definition writes only to the current environment.
7. Each `_eval` entry and procedure application consumes a step. Builtins are finite loops over an
   already materialized argument list, so no builtin hides recursive evaluation.
8. User-call depth increments immediately before creating the call environment and decrements in a
   `finally` block, preserving the counter on every language error.
9. Equality tests `bool` and exact `int` explicitly before general data handling. Symbol is a wrapper,
   not a subclass of `str`, so symbol/string equality cannot collapse accidentally.
10. Division computes `abs(a) // abs(b)` and reapplies the sign. No float conversion or precision loss
    occurs, even for large integers.
11. `CONST`/`LOAD` push one value; `POP` removes one; conditional jump consumes its condition; `CALL n`
    replaces callee plus `n` arguments with one result; `RETURN` requires exactly one value.
12. Forward branches are emitted with `-1`, patched only after their target instruction index is
    known, and the compiler appends `RETURN`. The VM independently checks every target.
13. The VM validates instruction container, opcode, operand count/type, constant indexes, jump targets,
    and stack preconditions immediately before use, mapping failures to `VM_MALFORMED`.
14. The CLI creates one environment per source submission and one evaluator whose `evaluate` method
    resets counters for each top-level form. The REPL retains both across input lines.
15. Differential coverage emphasizes truthiness, untaken error branches, nested `do`, higher-order
    callee expressions, empty calls, data constants, arithmetic errors, and unbound loads.

## Module boundaries

`reader` produces only language values. `runtime` owns environments, builtin contracts, truthiness,
and structural equality. `evaluator` controls evaluation order. `compiler` knows instruction layout but
does not execute. `vm` treats bytecode as untrusted internal input. `cli` is the only source-file I/O
boundary.

The compiler subset is intentionally smaller than the evaluator. Supporting lexical closures in the
VM would require an explicit local-slot model, closure capture instructions, and call frames; silently
falling back to the evaluator would hide that design work and weaken differential testing.
