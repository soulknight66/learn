# Unsafe-excerpt incident record

Provenance: local experiments derived only from the intentionally unsafe excerpt
in `LEARNING_TASK.md`. No catalog link, official material, external repository,
or other learner work was used. Validation label: **REPRODUCED LOCALLY** on the
workspace's default Python 3.6.8; independent validation is not claimed.

The four hypotheses below were captured before writing the replacement model.
`UnsafeExcerptIncidentTests` is a minimal executable rendering of the excerpt.
These are passing regression tests because they assert that each unsafe behavior
really occurs; `ok` means the defect was reproduced, not that the excerpt is
safe.

## Reproduction command and result

Command, run from `student_work/`:

```bash
python3 -m unittest -v test_lease_queue.UnsafeExcerptIncidentTests
```

Observed output:

```text
test_unsafe_conflicting_id_mutates_second_job_and_returns_old_response (test_lease_queue.UnsafeExcerptIncidentTests) ... ok
test_unsafe_forged_higher_epoch_is_accepted_and_advances_fence (test_lease_queue.UnsafeExcerptIncidentTests) ... ok
test_unsafe_node_accepts_exact_expiry_and_queue_does_not_check_time (test_lease_queue.UnsafeExcerptIncidentTests) ... ok
test_unsafe_stale_request_mutates_before_fence_rejection (test_lease_queue.UnsafeExcerptIncidentTests) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK
```

## Cycle 1: mutation precedes stale-authority rejection

**Hypothesis.** Because `transition(request)` runs before the history and epoch
checks, a previously unseen stale command can mutate a job and then return
`FENCED`, falsely suggesting that nothing happened.

**Small experiment.** Start one `READY` job with queue epoch 2. Apply `CLAIM`
command `stale` using old epoch 1 at tick 3. The exact reproducer is
`test_unsafe_stale_request_mutates_before_fence_rejection` under the command
above.

**Observation.** The response was `FENCED` and history stayed empty, but the job
became `CLAIMED:worker-old`. A retry therefore sees a state that contradicts the
first response.

**Revision.** For unseen IDs, perform the complete sink-side fence check before
calling the state machine. A fenced result must return with identical before and
after job snapshots and `history_changed: false`.

## Cycle 2: a conflicting ID mutates an unrelated job

**Hypothesis.** The excerpt checks only whether an ID exists, not whether its
payload matches. Since transition happens first, reusing an accepted ID with a
different job can change the second job and then return the first job's saved
response.

**Small experiment.** Accept `same = CLAIM(one, worker-a)`, then apply
`same = CLAIM(two, worker-b)` under the same valid lease. The exact reproducer is
`test_unsafe_conflicting_id_mutates_second_job_and_returns_old_response`.

**Observation.** Both jobs became claimed, history still had one entry, and the
second call returned the first call's exact `OK_CLAIMED` response. It neither
reported a conflict nor described the mutation it performed.

**Revision.** Store `(payload, response)` and compare the exact payload tuple
before authority or business evaluation. Equal payload replays the saved object;
different payload returns `ID_CONFLICT` with no state or history change.

## Cycle 3: invented higher epochs self-authorize

**Hypothesis.** The check `lease.epoch < active_epoch` rejects only lower epochs.
An uninstalled higher number, wrong owner, and arbitrary interval can be accepted
and can permanently advance `active_epoch`.

**Small experiment.** Begin at active epoch 1 and apply an unseen claim with
`Lease("attacker", 99, 100, 101)` at tick 1. The interval is not valid at that
tick, making acceptance unambiguously wrong. The exact reproducer is
`test_unsafe_forged_higher_epoch_is_accepted_and_advances_fence`.

**Observation.** The response was `OK_CLAIMED`, the job changed, and the queue
advanced itself to epoch 99. A legitimate epoch-1 caller would then appear
stale.

**Revision.** Only the coordinator installs a full immutable fence. Application
requires exact owner, epoch, start, and expiry equality with that installed
lease; request traffic never advances authority.

## Cycle 4: inconsistent expiry boundary

**Hypothesis.** `Coordinator.grant` uses `tick <= expires_tick`, while the node
uses `tick > expires_tick`; both treat the exact expiry tick as still occupied or
usable, contrary to the required half-open interval. The queue performs no time
check to correct the node.

**Small experiment.** Give a node `Lease("dispatcher", 1, 0, 2)` and submit at
tick 2. The exact reproducer is
`test_unsafe_node_accepts_exact_expiry_and_queue_does_not_check_time`.

**Observation.** The node's `tick > expires_tick` test was false and the queue
returned `OK_CLAIMED`. Thus a command was accepted outside `[0, 2)`.

**Revision.** Use one `Lease.valid_at` predicate implementing
`start <= tick < expires`. A grant at tick 2 may install the next epoch; an
unseen command under the old lease at tick 2 is `FENCED` at the queue.

## Replacement-model log landmark

The following exact command was used to exercise the revised stale-delivery
path and print only fence and rejection landmarks:

```bash
python3 - <<'PY'
import json
from lease_queue import Coordinator, DurableQueue, EventRunner, Node, Request, StructuredLog
log = StructuredLog()
queue = DurableQueue(('job',), log)
coordinator = Coordinator(queue)
old = Node('old', queue)
new = Node('new', queue)
runner = EventRunner(coordinator)
runner.schedule_grant(0, old, 3)
runner.schedule_grant(3, new, 4)
runner.schedule_submit(4, old, Request('delayed', 'CLAIM', 'job', 'worker-old'))
runner.run()
for record in log.records:
    if record['event'] in ('fence_install', 'queue_decision'):
        print(json.dumps(record, sort_keys=True))
PY
```

Relevant observed records:

```json
{"active_epoch": 1, "active_owner": "old", "command_id": null, "decision": "INSTALLED", "epoch": 1, "event": "fence_install", "expires_tick": 3, "history_changed": false, "insertion_index": 0, "job_after": null, "job_before": null, "owner": "old", "start_tick": 0, "state_changed": true, "tick": 0}
{"active_epoch": 2, "active_owner": "new", "command_id": null, "decision": "INSTALLED", "epoch": 2, "event": "fence_install", "expires_tick": 7, "history_changed": false, "insertion_index": 1, "job_after": null, "job_before": null, "owner": "new", "start_tick": 3, "state_changed": true, "tick": 3}
{"active_epoch": 2, "active_owner": "new", "command_id": "delayed", "decision": "FENCED", "epoch": 1, "event": "queue_decision", "history_changed": false, "insertion_index": 2, "job_after": {"status": "READY", "worker_id": null}, "job_before": {"status": "READY", "worker_id": null}, "owner": "old", "payload": ["CLAIM", "job", "worker-old"], "response_code": "FENCED", "state_changed": false, "tick": 4}
```

The last record exposes presented epoch 1 and active epoch 2, and directly shows
unchanged job state and history. It is bounded semantic-model evidence only.
