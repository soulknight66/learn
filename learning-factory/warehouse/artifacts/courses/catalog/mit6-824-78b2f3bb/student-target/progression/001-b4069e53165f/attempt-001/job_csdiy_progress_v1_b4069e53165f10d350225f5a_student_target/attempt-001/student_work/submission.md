# ParcelQ bounded submission

Validation label: **SELF-VALIDATED — 17/17 local tests passed** on Python 3.6.8
and again on the available Python 3.11.5. Independent worker-harness validation,
production validation, and transfer verification have not been performed.

Provenance: all artifacts were locally authored from only `UNIT_BRIEF.md`,
`LEARNING_TASK.md`, and `SELF_CHECK.md`. The linked catalog target was not
opened, and no official material, hidden check, reference answer, external
repository, factory state, or other learner work was consulted.

## Delivered artifacts

- `lease_queue.py` — immutable leases/requests/responses, coordinator grant and
  rollback, durable queue, history-first request handling, job state machine,
  structured logging, nodes, and deterministic event runner.
- `test_lease_queue.py` — six required public traces, seven additional contract
  tests, and four executable unsafe-excerpt incident reproducers.
- `DESIGN.md` — explicit lease, fence, identity, state, atomicity, logging, trust,
  response-code, and non-goal contract, ending with the required scope statement.
- `INCIDENT.md` — four hypothesis → experiment → observation → revision cycles,
  exact commands, actual test output, and structured-log excerpts.
- `notes.md`, `debugging-log.md`, and `self-check.md` — bounded study synthesis,
  preserved failure/revision history, and answers to all staged self-checks.

## Run command and actual result

From a clean copy of this `student_work` directory:

```bash
python3 -m unittest -v test_lease_queue.py
```

Actual default-interpreter summary:

```text
Ran 17 tests in 0.004s

OK
```

No test was skipped. The first development compile did fail on Python 3.6-only
syntax compatibility; that output and the `NamedTuple` revision are retained in
`debugging-log.md` rather than erased.

## Requirement evidence

| Contract area | Implementation | Deterministic evidence |
|---|---|---|
| Half-open lease and failover fence | exact immutable `Lease`; queue-installed fence; coordinator rollback | before-expiry denial/exact-expiry grant test; forged/out-of-interval test |
| Paused stale dispatcher | delayed old-node event reaches authoritative queue after epoch 2 | `test_paused_old_dispatcher_unseen_delayed_command_is_fenced` |
| Retry identity | history stores exact `(action, job_id, worker_id)` and `Response`; lookup precedes fence | duplicate, ID-conflict, and post-failover replay tests |
| Business state | explicit `READY -> CLAIMED(w) -> DONE(w)` transitions and stable descriptive codes | public traces plus nonmutating-business-history test |
| Atomic grant | prevalidation, one non-interleaved action, state/log rollback on exception | invalid-TTL and injected-installation-failure test |
| Determinism | heap ordered by unique `(tick, insertion_index)` | same-tick winner assertions and repeat-run equality test |
| Observability | common structured fields plus payload, response, history-change, and insertion index | required-field test and exact JSON excerpts in `INCIDENT.md` |
| Trust boundary | one bound coordinator may call private fence install | unauthorized-installer test and explicit design caveat |

The queue checks history and payload before authority. For an unseen request, it
then requires the whole presented lease to equal the installed fence and checks
the installed half-open interval before any business transition. Consequently,
`FENCED`, `NO_LEASE`, and `ID_CONFLICT` create no history; every authorized
business result does, even if it leaves the job unchanged.

## Honest boundary

This is a deterministic single-process logical-time semantic model. Real clocks,
threads, process races, network protocols, coordinator failover, persistent
storage/recovery, Byzantine behavior, and cryptographic tokens were unavailable
and are not implemented. The private coordinator binding is a model convention,
not a security boundary. These artifacts do not establish production
correctness, official credit, whole-course completion, or transfer of learning.
