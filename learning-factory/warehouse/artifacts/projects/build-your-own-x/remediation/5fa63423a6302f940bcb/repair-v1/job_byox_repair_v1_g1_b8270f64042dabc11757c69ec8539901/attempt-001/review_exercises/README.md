# Code-review exercises

These excerpts are intentionally plausible rather than cartoonishly broken.
Review them against the public shell contract and Unix lifecycle rules.

For each exercise, submit a short review with this shape:

- finding and severity (`critical`, `high`, `medium`, or `low`);
- the exact input or event ordering that triggers it;
- the violated invariant;
- the smallest safe repair, including error cleanup;
- a regression test that would fail before the repair.

Do not merely rewrite the excerpt. A useful review explains why a change is
needed and distinguishes correctness failures from optional refactoring.

Exercises:

- `exercise_01_parser_ownership`: token bytes appear valid during parsing but
  do not survive the function boundary;
- `exercise_02_terminal_handoff`: a foreground pipeline is launched under
  adversarial scheduling;
- `exercise_03_builtin_context`: builtin dispatch interacts with pipelines,
  backgrounding, and redirection.

The sealed answer in each exercise is one possible review, not a substitute for
finding evidence yourself.

