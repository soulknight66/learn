# Debugging exercises

Each subdirectory contains an isolated faulty fragment and prompt. Diagnose before editing. The answer for
an exercise is kept in that exercise's own `sealed/` directory.

- `reader_cursor/`: a scanner reports the wrong location after an escape.
- `closure_parent/`: a function accidentally resolves against the caller.
