# Sealed reference tests

The executable suite here checks the reference compiler’s observable API,
diagnostics, evaluation, class loading, deterministic output, short-circuit
behavior, source locations, path-sensitive declarations, and limits. It is
intentionally stored outside the learner view.

`./sealed/run-reference-tests.sh` compiles these tests together with only the
sealed reference implementation and runs with assertions enabled.

