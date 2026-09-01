# Bounded revision notes

Provenance: this revision uses the staged assignment packet, the prior attempt,
and the published examiner feedback supplied for this bounded attempt. I did
not retrieve the catalog link, official material, hidden checks, reference
solutions, factory state, or another learner's work. Validation label:
**LEARNER NOTES / LOCALLY CHECKED**.

## What the external evidence changed

The prior attempt's supporting Markdown described four central artifacts, but
the examiner found that `lease_queue.py`, `test_lease_queue.py`, `DESIGN.md`, and
`INCIDENT.md` were absent. Its clean-directory command consequently failed with
`ModuleNotFoundError`. The concrete revision priority was therefore not more
assertive prose; it was to create and preserve the implementation, executable
tests, design contract, and incident evidence at the submission root.

This revision now contains all four. I also copied the complete submitted set
into a fresh temporary directory, removed `PYTHONPATH`, and ran the declared
test module there. The run exited 0 with 17 tests passing. This is local
reproduction of the staging condition, not independent or transfer validation.

## Contract distilled and implemented

- Authority is the exact immutable tuple `(owner, epoch, start_tick,
  expires_tick)`, not a comparison that merely rejects smaller epochs.
- Lease validity is half-open. At `expires_tick`, a new grant may install the
  next epoch and an unseen command using the old lease is fenced.
- Installing the queue fence and publishing the coordinator lease are one
  non-interleaved model action. A denied or failed grant consumes no epoch and
  leaves no installation record.
- The queue checks existing history and exact logical payload before current
  authority. Same ID and payload returns the saved response; different payload
  returns `ID_CONFLICT`.
- Authority metadata is excluded from logical identity, allowing an accepted
  operation to replay after failover. An unseen fenced request creates no
  history and can later be retried with valid authority.
- Every authorized business decision is historical, including `NOT_FOUND`,
  `INVALID`, and state-dependent nonmutating results. This makes retry output
  stable if later commands change the job.
- Event order is the stored tuple `(tick, insertion_index)`. Same-tick results
  do not depend on mappings, sets, object identity, wall clocks, or a scheduler.

## Engineering choices

- `typing.NamedTuple` supplies immutable value records while remaining
  compatible with the workspace's default Python 3.6.8.
- `DurableQueue` alone mutates jobs, history, and the active fence. `Node`
  rejects only a missing lease; the authoritative sink sees expired or stale
  tokens so history-first replay remains possible.
- The coordinator receives an identity token when bound to the queue. This
  prevents accidental use through the model API but is explicitly not a Python
  security or cryptographic boundary.
- Grant installation snapshots both authority objects and the log boundary.
  An injected post-install exception test verifies rollback of fence, epoch,
  current lease, and misleading installation evidence.
- Pause and resume are trace markers. Delay, loss, and duplication are modeled
  by which deterministic delivery events are scheduled.

## Evidence map

- `lease_queue.py`: model, state machine, history, atomic grant, structured log,
  nodes, and deterministic runner.
- `test_lease_queue.py`: six required public traces, seven contract checks, and
  four unsafe-excerpt reproducers.
- `DESIGN.md`: authority, identity, response, atomicity, observability, trust,
  and non-goal contract.
- `INCIDENT.md`: four hypothesis → experiment → observation → revision cycles
  plus actual structured stale-delivery records.
- `debugging-log.md`: exact local commands and outcomes, including the
  clean-directory reproduction.
- `self-check.md`: evidence-based answers to all sixteen staged questions.

## Lessons and boundary

A fence protects state only when the durable sink validates it before mutation.
Deduplication needs both payload and saved result; a set of command IDs is not
enough. Boundary operators are protocol behavior, so exact-expiry tests matter.
Logs are most useful when they expose presented and active authority as distinct
fields and label both job and history mutation.

The evidence remains limited to a deterministic, single-process, in-memory
model with trusted logical ticks. It does not justify claims about real clocks,
concurrent processes, crash recovery, durable storage, consensus, production
correctness, course completion, or transfer of learning.
