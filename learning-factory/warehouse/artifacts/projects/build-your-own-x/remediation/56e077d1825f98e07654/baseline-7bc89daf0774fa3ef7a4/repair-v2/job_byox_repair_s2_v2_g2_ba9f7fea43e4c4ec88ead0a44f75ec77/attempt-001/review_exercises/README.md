# Code-review exercises

Each candidate fragment is intentionally small enough to review without running
the full kernel. Findings and repaired reasoning live under that exercise's own
`sealed/` directory. The deterministic post-attempt view is defined by
`environment/post_attempt_view_policy.json`; it selects each candidate and its
prompt exactly and excludes the nested answer. Never copy this directory
recursively into a learner view.

- `vm-boundary/`: review permission and output-publication order in translation.

Exercise fragments are not compiled into the starter or reference. They are
unvalidated review inputs, not production code.
