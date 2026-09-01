# ParcelQ bounded revision submission

Outcome: the four artifacts missing from the prior staged attempt are now
present at this submission root and the declared test command succeeds in a
fresh local directory with `PYTHONPATH` removed.

Validation label: **SELF-VALIDATED — 17/17 LOCAL TESTS PASSED ON PYTHON 3.6.8**.
Independent worker-harness validation and transfer verification have not been
performed. Course completion is not claimed.

## Submitted artifacts

- `lease_queue.py` — deterministic lease, fence, history, job-state, audit, node,
  and event-runner implementation.
- `test_lease_queue.py` — 17 standard-library tests: six required traces, seven
  additional contract checks, and four unsafe-excerpt reproducers.
- `DESIGN.md` — explicit semantic contract, response table, trust boundary,
  atomicity mechanism, and non-goals; it ends with the required scope statement.
- `INCIDENT.md` — four preserved hypothesis/experiment/observation/revision
  cycles and actual structured replacement-trace records.
- `notes.md`, `debugging-log.md`, and `self-check.md` — fresh revision synthesis,
  concrete command history, and bounded self-assessment.
- `submission.md` — this inventory and handoff.

## Reproducible command

From a directory containing these submitted files:

```bash
python3 -m unittest -v test_lease_queue.py
```

Actual workspace run:

```text
Ran 17 tests in 0.003s

OK
```

I then copied the complete submitted file set into a newly created temporary
directory and ran:

```bash
env -u PYTHONPATH python3 -B -m unittest -v test_lease_queue.py
```

That clean-copy run exited 0:

```text
Ran 17 tests in 0.003s

OK
```

No test was skipped. The unresolved numeric user/group-name warnings printed by
shell startup were environmental diagnostics; the Python process exit status
was 0.

## Published gap → preserved evidence

| Published examiner observation | Revision evidence |
|---|---|
| Model file absent | `lease_queue.py` is present and importable without external paths. |
| Test module absent; clean run exited 1 | `test_lease_queue.py` is present; both direct and clean-copy runs exit 0. |
| Design claim had no submitted contract | `DESIGN.md` cites concrete types, ordering, rollback, responses, logs, and tests. |
| Incident hypotheses had no submitted reproducer | `INCIDENT.md` maps four cycles to executable `UnsafeExcerptIncidentTests`. |

## Behavioral evidence summary

The queue performs history and payload checks first. For unseen requests it then
requires the full presented lease to equal the installed fence and checks the
installed half-open interval before business evaluation. Tests assert stale
failover rejection, stable duplicate replay, payload conflict, replay after a
new fence, denial before/exact grant at expiry, and same-tick insertion order.
Additional tests cover forged lower/higher/wrong-owner/altered-interval tokens,
node rejection, historical nonmutating results, atomic installation rollback,
coordinator-only installation, all response codes, repeat determinism, and the
common structured-log schema.

## Claim boundary

This is locally authored standard-library code for one bounded deterministic
exercise. It has no real clocks, threads, processes, transport, disk recovery,
replicated coordinator, consensus, Byzantine defense, or cryptographic token.
The catalog target was not retrieved. Passing local tests does not establish
production correctness, official credit, whole-course completion, independent
validation, or transfer of learning.
