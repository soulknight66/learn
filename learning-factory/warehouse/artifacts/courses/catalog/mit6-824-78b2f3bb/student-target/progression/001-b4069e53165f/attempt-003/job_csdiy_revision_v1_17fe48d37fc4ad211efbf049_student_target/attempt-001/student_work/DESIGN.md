# ParcelQ model design

Validation label: **locally authored design contract; independently unvalidated**.

## State and authority

Lease is an immutable NamedTuple with owner, epoch, start_tick, and
expires_tick. Coordinator.grant accepts a TTL only when its runtime type is
integer (not boolean) and it is greater than zero. A lease authorizes an unseen
request only when:

1. the presented Lease value equals the queue's installed Lease value,
2. therefore its owner, epoch, start, and expiry all match, and
3. start_tick <= tick < expires_tick.

Numeric epoch comparison is deliberately insufficient. Lower, higher,
wrong-owner, changed-start, changed-expiry, not-yet-valid, and expired tokens
all receive FENCED. That response does not mutate a job or history.

The coordinator denies a grant before the current expiry without advancing its
epoch, changing either authority object, or emitting a fence_install record. At
the expiry tick, it constructs the next epoch and invokes the queue's private
fence installation operation.

Grant plus installation is one non-interleaved action in this single-process
model. Coordinator.grant snapshots its epoch/current lease, the queue fence,
and the audit boundary. It installs the candidate fence, commits the same Lease
as coordinator current, and only then publishes the GRANTED and INSTALLED
records and returns. An exception restores both authority objects, the epoch,
and the log boundary. The injected-failure test exercises an exception after
the queue was mutated and proves that no partial fence or misleading
fence_install record remains.

## Jobs and responses

Every named job starts as (READY, null). JobState is immutable; the queue
replaces it only on a successful transition.

| Action and prior state | Condition | Response | New state |
|---|---|---|---|
| CLAIM / READY | any worker | OK_CLAIMED | CLAIMED(worker) |
| CLAIM / CLAIMED | same worker | ALREADY_CLAIMED | unchanged |
| CLAIM / CLAIMED | different worker | CLAIMED_BY_OTHER | unchanged |
| CLAIM / DONE | any worker | ALREADY_DONE | unchanged |
| COMPLETE / READY | any worker | NOT_CLAIMED | unchanged |
| COMPLETE / CLAIMED | same worker | OK_DONE | DONE(worker) |
| COMPLETE / CLAIMED | different worker | NOT_OWNER | unchanged |
| COMPLETE / DONE | any worker | ALREADY_DONE | unchanged |
| supported action / missing job | any worker | NOT_FOUND | no job created |
| unsupported action | any job identifier | INVALID | unchanged |

Action validity is checked before job existence, so a request that has both an
unsupported action and an unknown job is INVALID. This precedence is explicit
and tested.

## Logical identity and history

A Request contains command_id, action, job_id, and worker_id. Its payload
fingerprint is exactly (action, job_id, worker_id); dispatcher identity and
lease fields are authority metadata and are excluded.

DurableQueue.apply follows this order:

1. emit queue_attempt;
2. look up command_id;
3. if found, compare payload and either return the stored Response as REPLAY or
   return ID_CONFLICT;
4. for an unseen ID, validate the exact installed lease and half-open tick;
5. evaluate the business state machine; and
6. store payload plus the exact Response, including nonmutating business
   outcomes.

Thus an accepted operation retains the same response even if another command
later changes the job. A replay is history, not a renewed authorization
decision, and works after failover. By contrast, an unseen stale attempt is
FENCED and creates no history, so the same identity may later reach the state
machine through current authority. ID_CONFLICT never replaces the original
entry.

## Deterministic events

EventRunner assigns every scheduled grant or delivery a unique monotonically
increasing insertion_index. Its heap comparator uses only
(tick, insertion_index). The runner installs a successful grant on that
owner's Node before processing the next event. Delay, loss, duplication, and a
dispatcher pause are represented by which delivery events are scheduled and
at what tick; there is no real transport or scheduler.

Node rejects only a missing local lease with NO_LEASE. It deliberately forwards
expired-looking tokens to the queue so that history-first replay remains
possible and sink-side time and fence checks remain authoritative.

## Structured observability

Every record has the common keys tick, insertion_index, event, command_id,
owner, epoch, active_owner, active_epoch, decision, state_changed,
history_changed, job_before, job_after, response_code, payload, and presented
and active interval bounds. Inapplicable values are null. Additional fields,
such as original_payload on a conflict, remain structured.

The record kinds are grant_attempt, fence_install, node_rejection,
queue_attempt, replay, conflict, fence_rejection, and business_decision.
Presented owner/epoch are distinct from active owner/epoch. Responses and state
transitions never branch on record contents; records describe decisions after
they are made. The rollback code uses only an append boundary to remove a fact
about an installation that did not commit.

## Trust boundary and non-goals

DurableQueue binds one Coordinator object and rejects fence-install calls whose
caller identity differs. This is an API guard inside the semantic model. Python
object identity is not authentication, an unforgeable capability, or
cryptographic enforcement. The model assumes only that bound coordinator calls
the private installation method.

The trusted simulator supplies integer logical ticks. The model is
single-process and in-memory. It excludes wall-clock skew and jumps, sockets,
threads, multicore races, process and machine crashes, durable recovery,
coordinator failover, replication, consensus, partitions, storage corruption,
Byzantine behavior, credential theft, and token cryptography. Broader claims
would require a specified clock model, authenticated authority, transactional
durable state, a replicated linearizable grant/fence protocol, restart and
crash-consistency evidence, concurrent-process checking, and controlled
network/storage fault injection.

The reproducible local command from the submission directory is:

~~~bash
python3 -B -m unittest -v test_lease_queue.py
~~~

The catalog target was not retrieved. These local tests are self-validation,
not official credit, independent validation, production evidence, course
completion, or transfer verification.

> This submission models one locally authored epoch-fenced queue exercise. It does not implement a consensus protocol, establish production correctness, complete an official assignment, or claim course completion.
