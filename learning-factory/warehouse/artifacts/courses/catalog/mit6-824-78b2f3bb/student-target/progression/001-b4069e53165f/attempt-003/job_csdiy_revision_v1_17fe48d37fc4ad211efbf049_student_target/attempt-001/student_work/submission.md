# ParcelQ bounded revision submission

Outcome: the executable artifacts that the published examiner found missing
are now present at the student_work root. The declared unittest target imports
and passes locally.

Validation label: **SELF-VALIDATED LOCALLY — 20/20 TESTS PASSED ON PYTHON
3.6.8**. This label is not worker-harness validation, independent examination,
course completion, or transfer verification.

## Submitted artifact inventory

- lease_queue.py — deterministic lease/fence/history/job model and event runner.
- test_lease_queue.py — 20 standard-library unittests, including all six public
  traces and four executable unsafe-excerpt reproducers.
- DESIGN.md — state and response contract, atomicity, trust boundary,
  observability, deterministic ordering, and non-goals.
- INCIDENT.md — four documented incident cycles with exact commands and
  structured safe-model evidence.
- notes.md — revision synthesis, decisions, observations, lessons, and limits.
- debugging-log.md — concrete command chronology, actual outputs, the prior
  published failure, and remaining diagnostic boundary.
- self-check.md — evidence-based answers to all sixteen supplied questions.
- submission.md — this artifact inventory and bounded handoff.

## Reproducible command

From a directory containing the submitted files:

~~~bash
env -u PYTHONPATH python3 -B -m unittest -v test_lease_queue.py
~~~

The direct student_work run exited 0:

~~~text
Ran 20 tests in 0.003s

OK
~~~

For a local packaging reproduction, I created a fresh directory within the
writable attempt, copied these eight files by explicit name, and listed its
top-level regular files. The listing was:

~~~text
DESIGN.md
INCIDENT.md
debugging-log.md
lease_queue.py
notes.md
self-check.md
submission.md
test_lease_queue.py
~~~

From that fresh directory, the command shown above exited 0 and again reported
20 tests in 0.003s, OK. This is a local clean-copy check, not a claim that the
orchestrator has staged or validated the files.

No test was skipped. The unresolved numeric user/group-name messages printed by
the shell environment were unrelated startup diagnostics; the Python exit
status was 0.

## Published gap to observable evidence

| Published observation | Evidence in this revision |
|---|---|
| lease_queue.py absent | The file is present and compiles on the local Python 3.6.8 interpreter. |
| test_lease_queue.py absent; clean import exited 1 | The module is present; direct and fresh-copy 20-test runs exit 0. |
| No submitted design contract | DESIGN.md defines concrete authority, identity, transitions, logs, rollback, and boundaries. |
| No submitted incident artifact | INCIDENT.md maps four unsafe hypotheses to named executable tests and actual observations. |
| Prior prose contradicted staged inventory | This handoff is paired with an explicit final filesystem inventory and fresh-copy check recorded in debugging-log.md. |

## Behavioral evidence summary

For existing IDs, the queue compares the exact logical payload before checking
current authority and returns either the stored response or ID_CONFLICT. For
unseen IDs, it requires the complete presented Lease to equal the installed
Lease and enforces its half-open interval before business evaluation. Fenced,
conflicting, and early NO_LEASE paths create no new history.

Tests assert stale failover rejection, one-transition duplicate replay, payload
conflict, replay after a newer fence, no epoch gap at exact expiry, and same-tick
insertion order. Additional tests cover forged and altered tokens, retry after a
fenced first delivery, stable historical nonmutating results, history/fence
precedence, injected post-install rollback, coordinator-only installation,
every documented business response, repeat determinism, and the common log
schema.

## Claim boundary

This is locally authored standard-library code for one bounded semantic
exercise. The catalog target was not retrieved. The work has no real clocks,
process concurrency, transport, disk recovery, replicated coordinator,
consensus, Byzantine defense, or cryptographic lease token. A local passing run
does not establish staging success by the orchestrator, production correctness,
official credit, whole-course completion, independent validation, or transfer.
