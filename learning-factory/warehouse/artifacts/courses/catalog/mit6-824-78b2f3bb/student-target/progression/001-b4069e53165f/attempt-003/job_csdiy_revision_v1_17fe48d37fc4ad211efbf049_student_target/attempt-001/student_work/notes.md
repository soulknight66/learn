# Bounded ParcelQ revision notes

Provenance: this revision uses only ASSIGNMENT, PRIOR_ATTEMPT, and the published
EXAMINER_FEEDBACK supplied in this attempt. I did not retrieve the catalog
locator, official course material, hidden checks, factory state, reference
solutions, or another learner's work. Validation label: **learner-authored and
locally checked; independent validation pending**.

## Concrete gap addressed

The prior examiner found only four narrative Markdown files in the staged
learner inventory. In particular, lease_queue.py, test_lease_queue.py,
DESIGN.md, and INCIDENT.md did not exist there. Its clean command therefore
exited 1 with ModuleNotFoundError: No module named test_lease_queue. Statements
in the prior narrative that those files existed were contradicted by the
artifact inventory.

This revision treats file presence and runnable behavior as evidence rather
than relying on a prose inventory. I created the four missing core artifacts
directly under student_work and retained the four requested revision records.

## What changed

- lease_queue.py now contains immutable authority and request values, the
  coordinator's atomic grant action, an exact-token authoritative queue,
  payload-aware request history, the job state machine, structured logging,
  nodes, and an explicit event runner.
- test_lease_queue.py contains 20 deterministic standard-library tests. Six
  implement the minimum public traces, ten challenge additional contract
  boundaries, and four preserve executable unsafe-excerpt experiments.
- DESIGN.md defines state, response precedence, half-open lease validity,
  history-first ordering, rollback, observability, the model trust boundary,
  and explicit non-goals.
- INCIDENT.md records four hypothesis → experiment → observation → revision
  cycles and an actual JSON contrast between stale replay and unseen stale
  rejection.
- These notes, submission.md, debugging-log.md, and self-check.md are newly
  written for the revision and refer to observable files and commands.

## Engineering decisions

NamedTuple supplies immutable records while remaining compatible with the
available Python 3.6.8 interpreter. For an unseen request, Lease equality
requires owner, epoch, start, and expiry to match the installed fence; checking
only whether an epoch is smaller would incorrectly trust an invented higher
epoch.

History lookup and payload comparison precede authority checks. This makes an
accepted request replayable through an old dispatcher while distinguishing it
from an unseen stale attempt, which is fenced without acquiring history. All
authorized business decisions, including nonmutating ones, are historical so a
later retry cannot change its response after unrelated job evolution.

Coordinator.grant is the one non-interleaved grant/install model action. It
restores coordinator state, queue fence, epoch, and the log boundary if
installation raises. The queue also binds the coordinator's object identity as
an API guard. This is explicitly a trusted in-process assumption, not
authentication or cryptographic enforcement.

EventRunner assigns a unique insertion index and orders only by
(tick, insertion_index). Node forwards expired-looking tokens so the sink can
apply history-first semantics and remain authoritative. Missing local authority
is the sole early NO_LEASE path.

## Local observations

The first compile and full test command after materializing the model and tests
was:

~~~bash
cd student_work
python3 -m py_compile lease_queue.py test_lease_queue.py
python3 -B -m unittest -v test_lease_queue.py
~~~

It exited 0 and reported:

~~~text
Ran 20 tests in 0.003s

OK
~~~

I then copied all eight submitted files by explicit name into a fresh directory
under the attempt root, listed that directory, and ran:

~~~bash
env -u PYTHONPATH python3 -B -m unittest -v test_lease_queue.py
~~~

The fresh-copy inventory showed all eight files and the command also exited 0
with 20 tests passing. This reproduces the prior examiner's import condition
locally; it does not predict or replace the orchestrator's independent staging.

The focused unsafe-excerpt command exited 0 and reported four tests in 0.000s.
In that suite, passing means the tests reproduced their asserted unsafe
effects, including mutation followed by FENCED and a duplicate entering the
transition twice. Exact command history and the prior published failure are in
debugging-log.md.

## Lessons and limits

A fence is useful only when the state-owning sink checks exact installed
authority before first-time mutation. A command ID is not enough for
deduplication; the saved logical payload and exact response are required.
Nonmutating state-machine decisions still need history for retry stability.
Final state alone is weak evidence: ordered logs and assertions on history,
response, active fence, before/after state, and insertion index expose defects
that a final-state check can miss.

This remains a deterministic, single-process, in-memory semantic model with
trusted integer ticks. It does not justify claims about real clocks,
concurrent processes, persistence, crash recovery, coordinator failover,
replication, consensus, production correctness, official credit, whole-course
completion, or transfer of learning.
