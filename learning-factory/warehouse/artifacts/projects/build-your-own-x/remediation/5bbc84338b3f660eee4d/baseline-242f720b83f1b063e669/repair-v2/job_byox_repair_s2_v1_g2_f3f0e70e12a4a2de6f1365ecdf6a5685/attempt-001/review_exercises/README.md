# Code-review exercises

Distribution boundary: this root is instructor-only, and this pack defines no learner reveal stage for
it. Exercise-local `sealed/` directories remain protected even within instructor workflows.

Review each candidate against the requirements and identify a minimal counterexample. Exercise answers
are stored only in that exercise's own `sealed/` directory.

- `truthiness/`: host truthiness leaks into Pebble.
- `tail_position/`: one recursive path still consumes the Python stack.
