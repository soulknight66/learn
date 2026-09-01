# Code-review exercises

Each exercise presents a small plausible fragment rather than a full shell. Review it against the numbered requirements and identify correctness, race, safety, and observability problems. Canonical findings remain in that exercise's own `sealed/` directory.

- `child-boundary/`: review signal disposition, process-group timing, diagnostics, and post-fork exits around `execvp`.

A useful review names the triggering schedule or input and proposes a test that would fail before the repair.
