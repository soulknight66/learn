# Code-review stage

Review the excerpts as if they were proposed changes to Pebble. Do not limit the
review to style: trace language semantics, public API behavior, malformed
inputs, and denial-of-service boundaries.

1. [Exercise 01: inconsistent work budgets](exercise-01/README.md)
2. [Exercise 02: environment membership](exercise-02/README.md)
3. [Exercise 03: trusting bytecode](exercise-03/README.md)

For every finding, record the triggering precondition, user-visible impact,
severity, and the smallest test that would prevent a regression. Suggested
repairs belong in the reviewer response, not in the prompt tree.
