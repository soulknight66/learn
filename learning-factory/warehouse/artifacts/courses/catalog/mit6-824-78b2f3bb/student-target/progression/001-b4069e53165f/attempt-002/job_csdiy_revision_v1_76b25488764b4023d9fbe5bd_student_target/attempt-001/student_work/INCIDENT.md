# Unsafe-excerpt incident record

Validation label: **REPRODUCED LOCALLY / REPLACEMENT LOCALLY TESTED**. The four
tests below intentionally implement only the relevant ordering from the
manager-authored unsafe excerpt. A passing unsafe test means the hypothesized
defect was reproduced; it does not endorse that behavior.

## Reproduction command and result

Command run from `student_work/`:

```bash
python3 -m unittest -v test_lease_queue.UnsafeExcerptIncidentTests
```

Actual Python 3.6.8 summary:

```text
test_hypothesis_expiry_operators_disagree_at_boundary ... ok
test_hypothesis_higher_epoch_self_authorizes ... ok
test_hypothesis_history_after_transition_mutates_id_conflict ... ok
test_hypothesis_transition_before_fence_mutates_stale_command ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
```

## Cycle 1: transition before stale-fence rejection

**Hypothesis.** Calling `transition` before checking the installed epoch can
mutate a job and then misleadingly return `FENCED`.

**Experiment.** `test_hypothesis_transition_before_fence_mutates_stale_command`
starts the unsafe queue at active epoch 2 with a ready job. It delivers one
previously unseen `CLAIM` carrying epoch 1.

**Observation.** The returned response was `FENCED` and history remained empty,
yet the job became `CLAIMED:worker-a`. The response therefore concealed a real
state change.

**Revision.** `DurableQueue.apply` now performs history/payload checks and the
complete sink-side fence check before `_evaluate`. A fence rejection emits
equal `job_before` and `job_after`, `state_changed: false`, and
`history_changed: false`.

## Cycle 2: transition before history and no payload comparison

**Hypothesis.** Looking up an ID only after transition, while storing no payload,
can mutate a second job and return an unrelated historical response.

**Experiment.**
`test_hypothesis_history_after_transition_mutates_id_conflict` first accepts
command `same` claiming `job-1`, then reuses `same` to claim `job-2` for another
worker.

**Observation.** The second call returned the exact first `OK_CLAIMED` response,
but `job-2` also became claimed. History still had only the original entry, so
neither the response nor history disclosed the second mutation.

**Revision.** History now stores `(payload, response)`. Lookup and exact payload
comparison occur before authority or business logic. A mismatch returns
`ID_CONFLICT` without mutation or replacement; a match returns the saved
response object.

## Cycle 3: a forged higher epoch self-installs

**Hypothesis.** A check of only `presented_epoch < active_epoch` allows an
ordinary request carrying an invented higher epoch to authorize itself and
replace the fence.

**Experiment.** `test_hypothesis_higher_epoch_self_authorizes` initializes the
unsafe queue at epoch 2 and submits a new claim with owner `mallory`, epoch 99.

**Observation.** The unsafe queue returned `OK_CLAIMED`, changed the job, and
set its active epoch to 99. No coordinator grant occurred.

**Revision.** Ordinary requests can never advance the fence. For unseen IDs the
safe queue requires the presented `Lease` to equal the full installed value,
including owner and interval. Only the bound coordinator's install operation
can replace it, and installation requires exactly the next epoch.

## Cycle 4: inconsistent expiry operators

**Hypothesis.** `tick <= expires_tick` in grant and `tick > expires_tick` in a
node both treat the exact expiry tick as belonging to the old lease, contrary to
the required half-open interval.

**Experiment.**
`test_hypothesis_expiry_operators_disagree_at_boundary` evaluates both unsafe
predicates at tick 5 for lease `[0, 5)` and compares them with the specified
predicate.

**Observation.** At tick 5 the unsafe coordinator predicate denied a new grant
and the unsafe node predicate accepted old authority, while `0 <= 5 < 5` was
false.

**Revision.** Coordinator and queue share the half-open rule. The public
boundary trace proves a tick-4 grant is denied without consuming an epoch, a
tick-5 grant installs epoch 2, and an unseen request at expiry is fenced.

## Replacement trace: stale delayed delivery

I ran a focused standard-library script using `StructuredLog`, `EventRunner`,
and the safe model. It granted `old` epoch 1 for `[0,3)`, installed `new` epoch 2
at tick 3, and delivered `old`'s unseen claim at tick 4. The selected actual JSON
records were produced by this exact command from `student_work/`:

```bash
python3 - <<'PY'
import json
from lease_queue import Coordinator, DurableQueue, EventRunner, Node, Request, StructuredLog

log = StructuredLog()
queue = DurableQueue(("job-1",), log)
coordinator = Coordinator(queue)
nodes = {"old": Node("old", queue), "new": Node("new", queue)}
runner = EventRunner(coordinator, nodes)
runner.schedule_grant(0, "old", 3)
runner.schedule_pause(1, "old")
runner.schedule_grant(3, "new", 4)
runner.schedule_resume(4, "old")
runner.schedule_submit(4, "old", Request("late-1", "CLAIM", "job-1", "worker-a"))
runner.run()
keys = ("tick", "event", "command_id", "owner", "epoch", "active_owner",
        "active_epoch", "decision", "state_changed", "history_changed",
        "job_before", "job_after", "insertion_index")
for record in log.records:
    if record["event"] == "fence_install" or record.get("command_id") == "late-1":
        print(json.dumps({key: record.get(key) for key in keys}, sort_keys=True))
PY
```

Output:

```json
{"active_epoch": 1, "active_owner": "old", "command_id": null, "decision": "INSTALLED", "epoch": 1, "event": "fence_install", "history_changed": false, "insertion_index": 0, "job_after": null, "job_before": null, "owner": "old", "state_changed": false, "tick": 0}
{"active_epoch": 2, "active_owner": "new", "command_id": null, "decision": "INSTALLED", "epoch": 2, "event": "fence_install", "history_changed": false, "insertion_index": 2, "job_after": null, "job_before": null, "owner": "new", "state_changed": false, "tick": 3}
{"active_epoch": 2, "active_owner": "new", "command_id": "late-1", "decision": "RECEIVED", "epoch": 1, "event": "queue_attempt", "history_changed": false, "insertion_index": 4, "job_after": {"state": "READY", "worker_id": null}, "job_before": {"state": "READY", "worker_id": null}, "owner": "old", "state_changed": false, "tick": 4}
{"active_epoch": 2, "active_owner": "new", "command_id": "late-1", "decision": "FENCED", "epoch": 1, "event": "fence_rejection", "history_changed": false, "insertion_index": 4, "job_after": {"state": "READY", "worker_id": null}, "job_before": {"state": "READY", "worker_id": null}, "owner": "old", "state_changed": false, "tick": 4}
```

The trace distinguishes presented epoch 1 from active epoch 2 and shows no job
or history mutation. The executable assertion is
`test_paused_old_dispatcher_unseen_delayed_command_is_fenced`; the full clean
command is `python3 -m unittest -v test_lease_queue.py`.

## Remaining incident boundary

These experiments do not exercise real processes, clocks, networks, disks,
coordinator crashes, replicas, or hostile credentials. The model revision
addresses the deterministic contract only. No production or transfer
verification is claimed.
