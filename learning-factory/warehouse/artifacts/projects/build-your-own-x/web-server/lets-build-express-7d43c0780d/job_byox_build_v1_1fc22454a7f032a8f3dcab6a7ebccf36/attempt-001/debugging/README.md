# Debugging exercises

These instructor exercises isolate small failures that commonly appear in a
middleware framework. They are intentionally independent of the reference
implementation, so changing exercise code cannot make the main contract tests
pass accidentally.

- `exercise-01` investigates re-entrant and repeated `next` calls.
- `exercise-02` investigates response framing for Unicode content and HEAD.

Run the reproduction command shown in each exercise README. The supplied code
is intentionally flawed, so a non-zero result before making a fix is expected.
Restore the exercise file before comparing alternative fixes. Explanations and
fixed examples live only under that exercise's `sealed/` directory.
