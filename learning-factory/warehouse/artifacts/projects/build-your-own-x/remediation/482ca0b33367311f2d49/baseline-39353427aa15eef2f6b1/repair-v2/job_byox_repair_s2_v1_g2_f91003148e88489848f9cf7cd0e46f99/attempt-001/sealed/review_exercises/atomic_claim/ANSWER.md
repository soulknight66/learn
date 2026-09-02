# Evaluator answer: atomic claim review

Two callers can read `CREATED` and both launch before either update commits. Launch-before-state also
means a database failure can leave an unrecorded process. Moving an ordinary `SELECT` and `UPDATE`
into a deferred transaction is not a clear claim boundary and may produce timing-dependent lock
failures.

Begin with `BEGIN IMMEDIATE`, read and validate the row, then update with both ID and
`state = 'CREATED'` predicates. Require one changed row and commit `RUNNING` before launch. A transition
trigger defends the graph against other writers. The losing caller observes a non-created state and
does not launch.

There remains a crash window after commit and before `Popen`. A production design adds an attempt row
with owner, generation, lease expiry, and supervisor acknowledgement, then reconciles expired
unacknowledged claims. SQLite and process creation do not share an atomic transaction.
