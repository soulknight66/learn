# Review answer

The chosen `if` branch and final `do` expression are language tail positions, but both are executed by a
new host call. A user function whose final body expression is an `if` and whose selected branch calls
itself will add an evaluator frame on every iteration. The evaluator should instead maintain current form
and environment variables in a loop, replace them with the selected/final expression, and continue. The
condition and nonfinal `do` expressions are not tail positions and must complete before that replacement.
