# Adversarial cases

These learner-facing cases target semantic edges rather than undocumented
answers:

- `cases/arithmetic_edges.mica` exercises wraparound and the exceptional signed
  division pair.
- `cases/skipped_declaration.mica` checks the specified zero initialization of a
  slot whose declaration statement is skipped.
- `cases/runtime_error.mica` must fail without printing a numeric result for its
  expression.

Run a case through both modes, link with `cc -no-pie`, and compare exit status,
stdout, and the documented failure class. The stronger automated expectations
remain sealed.
