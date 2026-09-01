# ParcelQ revision self-check

Provenance and label: answers cite this submission's code, tests, and actual
local records. **Self-checked only; not independently or transfer validated.**

## Authority and time

1. **Exact expiry authority.** Coordinator decides whether a lease may be
   granted; DurableQueue decides whether an unseen request may affect durable
   model state. Both enforce a half-open interval. The public expiry test denies
   tick 4 for [0,5), keeps epoch 1, then installs epoch 2 at tick 5. The token
   boundary test fences the installed lease itself at tick 15 for [10,15).

2. **Denied-grant effects.** The expiry test sees grant decisions GRANTED,
   DENIED_CURRENT_LEASE, GRANTED but fence-install epochs only [1,2].
   Coordinator epoch/current and the queue fence remain the same object across
   the denial. Invalid TTL and injected failure also prove no epoch or partial
   fence is exposed.

3. **Wrong owner and invented higher epoch.** Both are FENCED for unseen IDs.
   One test covers lower, higher, wrong-owner, altered-start, altered-expiry,
   not-yet-valid, and expired presentations while asserting unchanged READY
   state, empty history, and the same installed Lease.

4. **Atomic model action.** Coordinator.grant is one non-interleaved call. It
   snapshots both authority states and the log boundary, installs, commits the
   matching coordinator state, then returns. The injected queue raises after
   mutating its fence and appending misleading evidence; rollback leaves epoch
   0, both leases null, and no fence_install record. A retry receives epoch 1.

## Identity and mutation

5. **Payload boundary.** Request.payload is exactly (action, job_id, worker_id).
   Lease and dispatcher metadata are absent. The conflict tests vary job and
   worker under one ID and assert ID_CONFLICT plus preservation of the original
   HistoryEntry and both job states.

6. **Fenced first attempt versus stale replay.** Both can present old/1 while
   new/2 is active. The unseen case emits fence_rejection, leaves READY, and
   creates no history. The accepted identity emits replay before authority
   checking, returns its stored OK_CLAIMED response, and preserves the current
   job. INCIDENT.md contains the two actual JSON records side by side.

7. **Mutation evidence by path.** Tests assert actual jobs and history as well
   as logs. business_decision has history_changed=true for every authorized
   evaluation and state_changed only for successful CLAIM/COMPLETE. Replay,
   conflict, fence_rejection, and node_rejection have both false. Queue attempts
   are receipt landmarks and do not mutate.

8. **Stable nonmutating outcomes.** A COMPLETE against READY stores
   NOT_CLAIMED. A different ID later claims the job; retrying the first ID
   returns the identical stored Response while leaving CLAIMED intact.

## Determinism and debugging

9. **Same-tick order.** EventRunner allocates a monotonically increasing index;
   _ScheduledEvent compares only (tick, insertion_index). The public same-tick
   test asserts the indices, responses, winning worker, history count, and
   ordered business-decision records.

10. **Clean replay command.** The full suite is run with:

    ~~~bash
    env -u PYTHONPATH python3 -B -m unittest -v test_lease_queue.py
    ~~~

    An explicit eight-file copy into .revision-cleancheck.Wbpgya listed all
    submitted artifacts and this command exited 0 with 20 tests passing. That
    locally tests the prior import failure condition. The incident subset
    command in INCIDENT.md runs all four hypotheses without network or external
    modules.

11. **Presented and active authority.** Every record carries owner/epoch and
    active_owner/active_epoch, plus both intervals. The incident JSON directly
    exposes old/1 versus new/2; no free-form message parsing is required.

12. **Logging independence.** Business branches read jobs, history, request,
    installed Lease, and tick, never log contents. Records are created after
    each decision. The only log-related transaction mechanism is truncating a
    partial installation fact during rollback. Repeat-determinism tests compare
    complete state, history, responses, and logs for identical event lists.

## Claim boundaries

13. **Excluded failures.** Real-clock skew/jumps, threads, multicore and
    cross-process races, actual packets, process/machine crashes, disk
    persistence/corruption, coordinator failover, replication, Byzantine
    behavior, credential theft, and cryptographic forgery are outside this
    trusted-logical-time model.

14. **Evidence needed for broader claims.** At minimum: explicit clock
    assumptions, authenticated authority, a replicated linearizable
    grant/fence protocol, transactional durable state/history, restart and
    crash-consistency tests, concurrent-process checking, and controlled
    partition, duplication, failover, and storage-fault injection.

15. **Catalog and course implications.** No submitted statement says the
    catalog target was retrieved or that this is official material. It was not
    retrieved. No pass, official credit, production correctness, whole-course
    completion, or transfer verification is claimed.

16. **Failures and unresolved limits.** debugging-log.md preserves the
    examiner's missing-file ModuleNotFoundError, the initially inconclusive rg
    inventory, shell identity warnings, and all model limits. The first new
    compile/full run had no red tests; this is stated rather than inventing or
    suppressing a local failure. Independent staging and validation remain
    unresolved until performed by the orchestrator.
