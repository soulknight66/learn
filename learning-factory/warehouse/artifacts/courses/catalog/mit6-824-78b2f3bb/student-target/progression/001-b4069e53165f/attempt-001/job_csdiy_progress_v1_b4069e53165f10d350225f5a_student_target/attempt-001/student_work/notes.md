# Bounded study notes

Provenance: I studied only the staged learner-safe `UNIT_BRIEF.md`,
`LEARNING_TASK.md`, and `SELF_CHECK.md`. I did not open the catalog URL,
`JOB.md`, `.factory-workspace`, hidden checks, factory state, references, or any
other learner's files. Validation label: **LEARNER NOTES / LOCALLY CHECKED**;
these notes are not independent evidence of correctness.

## Contract distilled from the packet

- Authority is an exact immutable lease, not merely a large epoch. The queue
  must match owner, epoch, start, and expiry and must check trusted logical time.
- Lease validity is half-open. Tick `expires_tick` belongs to possible failover,
  not to the old owner.
- Granting authority and installing the sink fence form one atomic model action.
  A denied or failed grant must not consume an epoch or leave a misleading log.
- Request history precedes current-authority validation. Same ID plus the exact
  logical payload replays the saved response; a different payload conflicts.
  Authority metadata is not part of the payload.
- A fenced unseen request has not reached the state machine and leaves no
  history. An authorized nonmutating business result has reached the state
  machine and therefore is recorded.
- Same-tick determinism needs a stored monotonic insertion index; relying on
  incidental container or scheduler order would make failure traces ambiguous.

## Initial incident hypotheses

Before implementing the replacement, I recorded four testable hypotheses:

1. Transition-before-fence can mutate a job and still return `FENCED`.
2. Transition-before-history plus no payload comparison lets an ID conflict
   mutate a different job while replaying an unrelated response.
3. A `less than active` test lets a forged higher epoch install itself through
   ordinary request traffic.
4. `<=` in grant and `>` in node expiry disagree with `[start, expiry)` and
   allow use at exact expiry.

All four minimal reproducers are retained in `UnsafeExcerptIncidentTests`, and
the hypothesis → experiment → observation → revision details are in
`INCIDENT.md`.

## Implementation choices and tradeoffs

- Immutable `NamedTuple` values were used instead of `dataclass`. This keeps the
  model compatible with the actual default Python 3.6.8 while preserving value
  equality for exact lease matching.
- `DurableQueue` is the only business-state mutator. Nodes with a token defer
  apparent expiry to the queue; this costs a model call but keeps the
  authoritative reason observable and permits history-first replay through a
  stale node. A node with no token returns `NO_LEASE` early.
- The coordinator's private queue binding is deliberately modest. It prevents
  accidental installation through the public model API, but private Python
  access is not security. Real authorization was not smuggled into the claims.
- Grant rollback snapshots the two authority objects and the log boundary.
  Since event execution is single-process and non-interleaved, this models one
  atomic action without pretending to supply a distributed transaction.
- Every authorized business evaluation enters history, even `NOT_FOUND`,
  `INVALID`, or a state-dependent nonmutating result. This stabilizes retry
  answers if the job later changes.
- Unknown-job lookup precedes action validation; therefore an unsupported
  action against a missing job returns `NOT_FOUND`. This otherwise ambiguous
  precedence is explicit in `DESIGN.md`.
- Pause and resume are trace markers. Delivery, loss, delay, and duplication are
  represented by the submit events actually scheduled; the runner does not
  simulate threads or packet buffers.

## Evidence map

- `lease_queue.py`: semantic model, structured records, and event runner.
- `test_lease_queue.py`: six required public traces and eleven additional
  contract/incident tests.
- `DESIGN.md`: state, identity, fencing, atomicity, response codes, trust
  boundary, and non-goals.
- `INCIDENT.md`: four preserved unsafe-excerpt cycles and actual log excerpts.
- `debugging-log.md`: commands, environment mismatch, failed compile, revision,
  and observed test runs.
- `self-check.md`: answers to all sixteen staged challenge questions.

## Concise lessons

- A fence is effective only when the durable sink checks it before mutation.
- Deduplication is a map from identity to both payload and historical result,
  not just a set of IDs.
- Boundary operators (`<`, `<=`, `>`, `>=`) are protocol behavior and deserve a
  named exact-tick trace.
- Logging both presented and active authority turns a generic rejection into a
  replayable incident landmark.
- Determinism is designed into event identity and order; it cannot be recovered
  reliably from final state alone.

## Unavailable prerequisites and scope

No official course content, starter code, real lease service, replicated log,
durable database, network, concurrent-process harness, real-clock source, or
fault-injection cluster was available or needed for this bounded semantic model.
Accordingly, these artifacts do not demonstrate production correctness,
whole-course completion, course credit, or transfer of learning to an
independent task. No transfer verification was performed.
