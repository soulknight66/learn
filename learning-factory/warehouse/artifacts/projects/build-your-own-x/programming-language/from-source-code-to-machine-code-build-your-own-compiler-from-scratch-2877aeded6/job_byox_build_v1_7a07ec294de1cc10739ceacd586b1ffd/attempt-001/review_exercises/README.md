# Code-review exercises

Review these small changes as if they guarded untrusted bytecode. Describe the user-visible failure,
the violated requirement, a concrete reproducer, and the minimum safe redesign.

- `bytecode_validation/review.py` combines validation and execution.
- `scope_resolution/review.py` models nested lexical scopes with one dictionary.

Companion review notes are evaluator-only under `sealed/review_exercises/`.
