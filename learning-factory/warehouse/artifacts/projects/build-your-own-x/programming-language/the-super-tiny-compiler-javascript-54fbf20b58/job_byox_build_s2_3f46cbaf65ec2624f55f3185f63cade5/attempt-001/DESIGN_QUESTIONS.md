# Design questions

Answer these after your implementation. Cite tests or small experiments rather than only preferences.

1. Why should a declaration's initializer be analyzed before the new name enters scope? What alternative behavior would recursive bindings require?
2. Which parser function establishes that multiplication binds tighter than addition? How would you add right-associative exponentiation?
3. Why does the generator need semantic binding IDs when Ripple identifiers already resemble JavaScript identifiers?
4. Which constant folds are unsafe because of short-circuiting, runtime exceptions, or non-finite values?
5. How do you prove `optimize(ast)` does not mutate nested input nodes?
6. Should `len` count UTF-16 code units, Unicode code points, or grapheme clusters? What compatibility and dependency costs follow each choice?
7. Where do interpreter and generated-code behavior risk drifting apart?
8. If user-defined functions were added, which AST, scope, arity, and runtime contracts would have to change?
9. What resource limits would be needed before compiling untrusted, multi-megabyte inputs in a service?
10. Which errors belong to scanning, parsing, analysis, and runtime respectively, and why?
