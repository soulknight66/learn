# Code-review exercise: a non-atomic start claim

Instructor-gated prompt; no answer is stored here.

Review this lifecycle shape conceptually:

```text
open connection
SELECT state for id
if state is CREATED:
    perform process launch
    UPDATE state to RUNNING
commit
```

Identify concurrency, crash-ordering, and evidence problems. Specify a transaction boundary and an
update predicate that allow at most one launcher. Then explain why that improvement still cannot make
a database commit and `Popen` one atomic action.

The evaluator answer for this exercise is under `sealed/review_exercises/atomic_claim/`.
