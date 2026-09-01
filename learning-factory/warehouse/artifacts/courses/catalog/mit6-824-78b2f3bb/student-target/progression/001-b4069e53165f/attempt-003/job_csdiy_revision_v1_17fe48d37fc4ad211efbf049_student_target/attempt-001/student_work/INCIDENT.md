# Unsafe-excerpt incident record

Provenance: these are locally executable experiments against the
manager-authored unsafe ordering in the assignment packet. The small
_UnsafeExcerptQueue in test_lease_queue.py intentionally retains that ordering
only as incident evidence; production classes do not call it. Validation
label: **actual local experiments, not independent validation**.

All four experiments can be reproduced from a clean submitted directory with:

~~~bash
python3 -B -m unittest -v test_lease_queue.UnsafeExcerptIncidentTests
~~~

The observed local run reported four tests, all ok. Here ok means each
reproducer observed its asserted unsafe outcome; it does not certify the unsafe
implementation.

## Cycle 1: a stale request can mutate and then report FENCED

**Hypothesis.** Because transition(request) runs before the epoch comparison, a
previous primary's unseen CLAIM can change READY to CLAIMED even though the
method subsequently returns FENCED. The response would misleadingly imply
rejection.

**Experiment.** test_stale_command_mutates_before_fence_rejection starts at
active epoch 2 with one READY job and delivers a fresh command at epoch 1.

~~~bash
python3 -B -m unittest -v \
  test_lease_queue.UnsafeExcerptIncidentTests.test_stale_command_mutates_before_fence_rejection
~~~

**Observation.** The unsafe method returned FENCED, but the job was CLAIMED.
History stayed empty because the return occurred after mutation and before
history insertion.

**Revision.** DurableQueue.apply checks history, then exact installed authority,
then evaluates the state machine. Its corresponding safe trace asserts FENCED,
READY before and after, zero history entries, and state_changed=false.

## Cycle 2: duplicate delivery can execute transition twice

**Hypothesis.** Looking in history after transition allows a duplicate request
to re-enter state-machine or side-effect code even when it ultimately returns a
stable-looking saved response.

**Experiment.**
test_duplicate_reexecutes_transition_before_history_replay delivers one CLAIM
twice with the same ID and payload while counting transition invocations.

~~~bash
python3 -B -m unittest -v \
  test_lease_queue.UnsafeExcerptIncidentTests.test_duplicate_reexecutes_transition_before_history_replay
~~~

**Observation.** Both calls returned the same text and history had one entry,
but transition_calls was 2. A final-state-only assertion would miss the second
execution.

**Revision.** Existing history is now checked before authority and business
evaluation. The safe duplicate trace asserts one business_decision, one replay,
one history entry, one job transition, and identity with the stored Response.

## Cycle 3: ID-only deduplication hides a conflicting payload

**Hypothesis.** A command ID reused for another logical payload is not a
duplicate. The excerpt both fails to compare payload and evaluates the new
payload before returning the old response, so it can mutate the wrong job and
conceal that mutation.

**Experiment.**
test_conflicting_payload_mutates_before_id_only_history_replay first uses ID
same to claim job a, then uses ID same to claim job b for another worker.

~~~bash
python3 -B -m unittest -v \
  test_lease_queue.UnsafeExcerptIncidentTests.test_conflicting_payload_mutates_before_id_only_history_replay
~~~

**Observation.** The second call returned the response stored for job a, yet
both a and b became CLAIMED while history still contained one entry.

**Revision.** History stores the exact (action, job_id, worker_id) fingerprint.
A mismatch returns ID_CONFLICT before fence or state checks and preserves the
original entry and both job snapshots. Authority metadata is intentionally not
part of that fingerprint.

## Cycle 4: an invented higher epoch self-authorizes

**Hypothesis.** Rejecting only lease.epoch < active_epoch treats any invented
higher number as authority and lets a caller advance the queue's fence without
a coordinator grant.

**Experiment.**
test_invented_higher_epoch_self_authorizes_and_advances_fence starts with active
epoch 1 and submits a fresh CLAIM using epoch 99.

~~~bash
python3 -B -m unittest -v \
  test_lease_queue.UnsafeExcerptIncidentTests.test_invented_higher_epoch_self_authorizes_and_advances_fence
~~~

**Observation.** The command returned OK_CLAIMED, changed the job, and changed
active_epoch to 99.

**Revision.** An unseen request must present a Lease exactly equal to the
installed owner, epoch, and interval. Only the bound coordinator's installation
operation can change the active Lease in the model. The contract tests cover
lower, higher, wrong-owner, altered-start, altered-expiry, not-yet-valid, and
expired presentations.

## Safe replacement trace

I ran this deterministic trace from student_work after the implementation and
tests were materialized:

~~~bash
python3 -B -c 'import json; from lease_queue import Coordinator,DurableQueue,Node,Request; q=DurableQueue(["replay-job","stale-job"]); c=Coordinator(q); old=Node("old",q); old.install_lease(c.grant("old",0,3)); accepted=Request("accepted","CLAIM","replay-job","worker-a"); old.submit(accepted,1); c.grant("new",3,4); old.submit(accepted,4); old.submit(Request("delayed","CLAIM","stale-job","worker-b"),4); keys=("tick","event","command_id","owner","epoch","active_owner","active_epoch","decision","response_code","state_changed","history_changed","job_before","job_after"); print(json.dumps([{k:r[k] for k in keys} for r in q.audit.records if r["event"] in ("replay","fence_rejection")], indent=2, sort_keys=True))'
~~~

Relevant actual records:

~~~json
[
  {
    "active_epoch": 2,
    "active_owner": "new",
    "command_id": "accepted",
    "decision": "REPLAY",
    "epoch": 1,
    "event": "replay",
    "history_changed": false,
    "job_after": {"status": "CLAIMED", "worker_id": "worker-a"},
    "job_before": {"status": "CLAIMED", "worker_id": "worker-a"},
    "owner": "old",
    "response_code": "OK_CLAIMED",
    "state_changed": false,
    "tick": 4
  },
  {
    "active_epoch": 2,
    "active_owner": "new",
    "command_id": "delayed",
    "decision": "FENCED",
    "epoch": 1,
    "event": "fence_rejection",
    "history_changed": false,
    "job_after": {"status": "READY", "worker_id": null},
    "job_before": {"status": "READY", "worker_id": null},
    "owner": "old",
    "response_code": "FENCED",
    "state_changed": false,
    "tick": 4
  }
]
~~~

The contrast is observable without prose parsing: the stale accepted identity
is replayed before authority checking, while the unseen stale identity is
fenced with no state or history change. The exact-expiry public trace separately
shows that a tick-4 grant under [0,5) is denied and tick 5 installs epoch 2
without an epoch gap.

The published prior examination failed earlier at packaging: the executable
module and tests were absent, so its clean command raised ModuleNotFoundError.
That failure remains part of the revision record; these new local observations
do not retroactively replace it or establish independent validation.
