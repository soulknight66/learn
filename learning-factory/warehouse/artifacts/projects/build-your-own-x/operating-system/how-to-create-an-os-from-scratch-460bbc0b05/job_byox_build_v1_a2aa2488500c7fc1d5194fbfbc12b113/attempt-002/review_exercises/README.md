# Code-review exercises

Review your implementation without consulting sealed material:

1. Trace every scheduler transition and identify which functions may change the current slot.
2. Audit page-number and offset arithmetic for overflow and out-of-range access.
3. Audit filesystem name handling for missing terminators and ambiguous names.
4. Mark every operation that promises failure atomicity and show where mutation begins.

Reference findings are isolated in `sealed/review_exercises/`.
