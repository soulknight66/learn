# Debugging exercises

Distribution boundary: this root is instructor-only, and this pack defines no learner reveal stage for
it. Exercise-local `sealed/` directories remain protected even within instructor workflows.

Each subdirectory contains an isolated faulty fragment and prompt. Diagnose before editing. The answer for
an exercise is kept in that exercise's own `sealed/` directory.

- `reader_cursor/`: a scanner reports the wrong location after an escape.
- `closure_parent/`: a function accidentally resolves against the caller.
