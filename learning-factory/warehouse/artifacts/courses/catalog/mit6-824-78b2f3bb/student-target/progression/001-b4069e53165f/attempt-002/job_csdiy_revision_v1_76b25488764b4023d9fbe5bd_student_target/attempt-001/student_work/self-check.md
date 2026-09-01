# Revision self-check

Provenance: answers below cite the submitted implementation, deterministic
tests, and actual local logs. Validation label: **SELF-CHECKED, NOT
INDEPENDENTLY OR TRANSFER VALIDATED**.

## Authority and time

1. **Exact expiry authority.** The coordinator authoritatively decides whether
   a new lease may be granted, and the queue authoritatively decides whether an
   unseen command may mutate. Both use `[start_tick, expires_tick)`. In
   `test_denied_before_expiry_has_no_gap_and_exact_expiry_succeeds`, a tick-4
   grant is denied under lease `[0,5)` and tick 5 installs epoch 2. The forged
   and interval test separately proves an unseen old request at expiry is
   `FENCED`.

2. **Denied-grant effects.** It cannot consume an epoch or alter either
   authority object. The boundary test sees installed epochs `[1, 2]` across
   three grant attempts and exactly two `fence_install` records. The denied
   decision at tick 4 reports active epoch 1. Invalid-TTL and injected-failure
   assertions likewise show epoch 0 and no active/current lease or installation
   record.

3. **Wrong owner or invented higher epoch.** Both are `FENCED` for an unseen
   request. Exact `Lease` equality prevents numeric ordering from authorizing a
   caller. `test_all_forged_or_out_of_interval_unseen_requests_are_fenced`
   covers lower, higher, wrong-owner, altered-start, altered-expiry,
   not-yet-valid, and expired presentations while asserting empty history,
   unchanged `READY`, and an unchanged installed fence.

4. **Action preventing partial installation.** One call to
   `Coordinator.grant` is the non-interleaved model action. It snapshots both
   authority objects, installs the exact queue fence, commits coordinator
   current/epoch, and only then returns. Exception rollback restores all
   snapshots. `test_invalid_ttl_and_failed_install_are_atomic` injects an error
   after queue installation and proves no partial state or install log remains.

## Identity and mutation

5. **Payload boundary.** `Request.payload` is exactly `(action, job_id,
   worker_id)` and excludes lease fields. `HistoryEntry` stores that tuple with
   the exact `Response`. The conflict trace changes both job and worker under
   one ID, receives `ID_CONFLICT`, and retains the original entry and both job
   outcomes.

6. **Fenced first attempt versus stale replay.** An unseen stale command emits
   `fence_rejection/FENCED`, creates no history, and has equal before/after job
   snapshots. A matching historical command emits `replay/REPLAY` and returns
   its saved response before authority checking. The post-failover replay trace
   shows presented epoch 1 versus active epoch 2 while preserving the newer
   `DONE` state; the unseen delayed trace with the same authority contrast is
   fenced and stays `READY`.

7. **Mutation evidence for each response path.** `business_decision` records
   label `state_changed` and `history_changed` and include structured job
   snapshots. Every authorized business response creates history; only
   successful claim/complete changes a job. Replay, conflict, fence, and node
   rejection records label both changes false. Tests also assert actual queue
   state and history, so logs are corroboration rather than the only evidence.

8. **Stability of nonmutating business results.** The exact response is stored,
   so it cannot change on a same-ID/same-payload retry. The nonmutating-history
   test saves `NOT_CLAIMED`, later changes the job to `CLAIMED`, then verifies
   the old command returns the identical response object without reverting the
   job.

## Determinism and debugging

9. **Same-tick order.** `EventRunner._schedule` assigns a unique monotonic
   insertion index and `ScheduledEvent` orders by tick then that index. The
   same-tick public trace asserts the first command and its index precede the
   second, the first worker wins, and structured business records retain that
   exact order.

10. **Clean incident replay.** From a submitted copy,
    `python3 -m unittest -v test_lease_queue.UnsafeExcerptIncidentTests`
    reproduces all four hypotheses. The full command
    `python3 -m unittest -v test_lease_queue.py` runs all 17 tests without files
    outside the submission. Both actual summaries are in `debugging-log.md`.

11. **Presented versus active authority.** Queue records have presented
    `owner`/`epoch` and separate `active_owner`/`active_epoch`, plus both
    intervals. The JSON in `INCIDENT.md` directly shows old/1 versus new/2 at
    tick 4; no prose parsing is needed.

12. **Logging independence.** Responses and transitions never inspect record
    contents. A compatible no-op collector retaining the same append/length
    interface would leave ordinary responses and states unchanged; the grant
    rollback uses only a log-length boundary to remove a partial installation
    fact. Deleting the interface calls without replacing them would of course
    require a code edit. The repeat-run test confirms identical decisions and
    records for identical event lists.

## Claim boundaries

13. **Excluded failures.** Real-clock skew/jumps, threads, multi-core and
    cross-process races, actual packet transport, process or machine crashes,
    disk persistence/corruption, coordinator failover, replication, Byzantine
    behavior, credential theft, and cryptographic forgery are excluded by this
    trusted-logical-time in-memory model.

14. **Evidence needed for broader claims.** At minimum: explicit real-clock
    assumptions; authenticated authority; a replicated linearizable grant/fence
    protocol; transactional durable state/history; restart and crash-consistency
    tests; concurrent-process stress/model checking; and controlled partition,
    delay, duplication, failover, and storage-fault injection. None was supplied
    or attempted.

15. **Catalog and course implications.** No artifact says the catalog target
    was retrieved or that this is official material. The provenance says it was
    not retrieved. No pass, credit, official-assignment completion, whole-course
    completion, production correctness, or transfer verification is claimed.

16. **Failures and unresolved limits.** The prior examiner's published
    `ModuleNotFoundError` and missing-artifact failure are preserved in
    `debugging-log.md` and `submission.md`. This revision had no red compile or
    test run; that fact is stated rather than inventing a failure. The
    inconclusive first inventory, shell identity warnings, unsafe observations,
    clean-copy commands, and all remaining model limits are retained. Only a
    future independent harness can determine whether staging and behavioral
    validation now succeed.
