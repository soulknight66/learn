# Debugging exercises

Each exercise contains a small, intentionally broken Bash component and a
focused reproducer. Work on a copy or edit the exercise's `broken.sh`, then run
its `test.sh`. A correct repair makes the test pass without weakening its
assertions.

The exercises are independent of the main starter implementation:

1. `01-argv-boundaries` — preserve exact argument boundaries through a wrapper.
2. `02-atomic-create` — make a same-name create claim atomic.
3. `03-exit-status` — restore lifecycle state without losing child status.

Some tests are expected to fail before repair. Reference explanations and
fixed examples are intentionally colocated under each exercise's own
`sealed/` directory. Do not expose those directories in a learner view.

