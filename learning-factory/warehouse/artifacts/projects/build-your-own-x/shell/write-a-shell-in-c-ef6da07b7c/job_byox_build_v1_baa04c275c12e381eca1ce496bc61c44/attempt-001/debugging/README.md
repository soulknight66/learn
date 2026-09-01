# Debugging exercises

These evaluator-curated exercises isolate failure modes that are easy to miss in a small shell. Each exercise provides broken code and observations. Its diagnosis and repair are stored only in that exercise's own `sealed/` directory.

- `pipe-eof/`: a reader never observes EOF even though the writer child exits.

Use bounded commands such as `timeout 2 ...` when investigating a suspected hang. A timed-out process is evidence to inspect, not a reason to remove the timeout.
