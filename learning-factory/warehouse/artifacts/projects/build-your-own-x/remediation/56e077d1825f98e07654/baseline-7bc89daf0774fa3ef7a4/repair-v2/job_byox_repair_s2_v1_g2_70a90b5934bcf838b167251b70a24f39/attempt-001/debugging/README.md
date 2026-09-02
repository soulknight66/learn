# Debugging exercises

Each exercise presents a symptom and a deliberately defective isolated fixture.
The answer is kept in that exercise's own `sealed/` directory. The deterministic
post-attempt view is defined by
`environment/post_attempt_view_policy.json`; it selects the fixture and prose
file-by-file and excludes the answer. Never copy this directory recursively into
a learner view.

- `scheduler-stall/`: a valid two-task table repeatedly chooses one task.

The fixture is not linked into either starter or reference builds. No observed
debugging result is promoted to a manifest validation label.
