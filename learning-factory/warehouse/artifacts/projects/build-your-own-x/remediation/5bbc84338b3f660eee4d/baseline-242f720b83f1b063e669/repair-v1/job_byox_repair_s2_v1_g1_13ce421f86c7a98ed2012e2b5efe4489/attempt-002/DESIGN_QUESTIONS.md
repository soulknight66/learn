# Design questions

Record your decisions before looking at failures. There is no answer material in this file.

1. What representation keeps symbols distinct from strings without scattering type checks everywhere?
2. Which component owns source positions, and what location should an end-of-input error report?
3. Why is `if` impossible to implement as an eager ordinary function?
4. Should `let` initializers see earlier bindings? What tests distinguish sequential and parallel rules?
5. Where should `def` bind when evaluated inside a function, and why?
6. How will a closure keep its definition environment after the creating call returns?
7. Enumerate every tail position in the required forms. Which superficially similar positions are not tail
   positions?
8. Where do you enforce arity so built-ins and user functions report consistent errors?
9. How do you keep Python's `True == 1` from leaking into language equality?
10. Which host exceptions can each built-in produce, and where should they become `EvalError`?
11. What state is persistent between calls to `eval_source` and between interactive input lines?
12. For a bytecode subset, what stack effect does every instruction have? How are jump targets validated?
13. Which unsupported forms should a compiler reject at compile time rather than defer to the VM?
14. What observable properties—not timing guesses—can differential tests compare across evaluator and VM?
