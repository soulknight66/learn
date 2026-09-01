# Self-check answers

Provenance: answers checked against the locally authored implementation, tests,
and logs derived only from the three staged learner-safe files. Validation label:
**SELF-CHECKED, NOT INDEPENDENTLY VALIDATED**.

## Authority and time

1. **Exact expiry authority.** The coordinator decides whether a grant may
   replace the current lease; the durable queue authoritatively decides whether
   a submitted command may mutate. Both use the same half-open predicate. In
   `test_denied_before_expiry_has_no_epoch_gap_and_exact_expiry_succeeds`, tick 4
   is denied and tick 5 installs epoch 2 for a lease expiring at 5. In the forged
   authority test, presenting the exact old installed lease at tick 3, its
   expiry, returns `FENCED` without history or job mutation.

2. **Denied grant effects.** No. The epoch changes only after queue installation;
   a valid-current denial returns before constructing/committing an epoch. The
   boundary test asserts epochs 1 then 2 with no gap and exactly two
   `fence_install` records despite three attempts. Invalid TTL and injected
   installation failure tests also assert unchanged coordinator/queue authority
   and no installation record.

3. **Wrong owner or invented higher epoch.** Both return `FENCED` for an unseen
   request. Equality covers the entire installed lease, so numeric ordering
   cannot self-authorize. `test_all_forged_or_out_of_interval_unseen_requests_are_fenced`
   checks lower, higher, wrong-owner, altered-interval, not-yet-valid, and expired
   variants and asserts unchanged state/history/fence.

4. **Action preventing partial installation.** One call to
   `Coordinator.grant` is the indivisible single-process model action. It
   prevalidates, installs the exact queue lease, commits coordinator current and
   epoch, and only then returns. Since events cannot interleave within the call,
   a dispatcher cannot observe a returned lease before its fence; exception
   rollback restores both objects.

## Identity and mutation

5. **Payload boundary.** Yes. `Request.payload` is exactly
   `(action, job_id, worker_id)` and excludes all lease fields. `HistoryEntry`
   saves that tuple and exact response. The conflict test changes job and worker
   under the same ID and gets `ID_CONFLICT` without replacing history.

6. **Fenced first attempt versus stale replay.** An unseen fenced attempt emits
   `queue_decision/FENCED`, has equal before/after state, and creates no history.
   A matching accepted ID emits `replay`, returns the saved `Response` object
   before lease validation, and also does not mutate. The post-failover replay
   test shows presented old epoch 1, active new epoch 2, a `REPLAY` decision, and
   preserved `DONE` state. The stale delayed unseen test with the same authority
   contrast emits `FENCED` and leaves the job `READY`.

7. **Mutation evidence by response path.** `business_decision` records expose
   `state_changed`, `history_changed`, and structured job snapshots. Authorized
   business decisions always show `history_changed: true`; only successful claim
   or complete may show `state_changed: true`. Replay, conflict, fence, and node
   rejection records show both flags false. Tests assert these flags along with
   actual job and history contents, so the log is corroborating evidence rather
   than the sole assertion.

8. **Stability of a nonmutating business result.** It cannot change on retry with
   the same ID/payload because the exact response is saved. The nonmutating
   history test first saves `NOT_CLAIMED`, later claims the job through another
   command, then asserts the original retry is the same response object and does
   not undo `CLAIMED` state.

## Determinism and debugging

9. **Same-tick order.** `EventRunner._schedule` assigns a unique monotonically
   increasing index; its heap orders `ScheduledEvent` by tick then that index.
   The same-tick test asserts the two business records' insertion indices and
   command IDs are `[first, second]`, with the first claim winning and the second
   returning `CLAIMED_BY_OTHER`.

10. **Clean replay command.** Yes. From the submitted directory,
    `python3 -m unittest -v test_lease_queue.UnsafeExcerptIncidentTests` replays
    all four incident hypotheses in a clean process. `INCIDENT.md` retains that
    exact command and observed output; the full suite is one similarly documented
    command.

11. **Presented and active authority.** Yes. Queue attempt/outcome records carry
    presented `owner`/`epoch` and installed `active_owner`/`active_epoch` as
    separate fields. Lease start/expiry and payload are additional structured
    values where useful. The JSON excerpt in `INCIDENT.md` needs no prose parsing
    to identify old epoch 1 versus active epoch 2.

12. **Logging independence.** State-machine and authority decisions never read
    record contents; `emit` only appends a completed fact. Replacing it with a
    compatible no-op emitter would leave responses and transitions unchanged.
    The only log-length use is cleanup of a partial install record during atomic
    rollback, not a decision input. This semantic claim does not assert survival
    of process-level failures such as memory exhaustion.

## Claim boundaries

13. **Excluded failures.** Real-clock skew and jumps, threads and multi-core
    races, cross-process interleavings, packet implementation, process or machine
    crashes, coordinator failover, disk persistence/corruption, recovery,
    Byzantine behavior, credential theft, and cryptographic forgery are outside
    this single-process trusted-logical-time model.

14. **Evidence needed for broader claims.** At minimum: explicit clock and lease
    assumptions; authenticated unforgeable authority; a replicated linearizable
    coordinator/fence protocol; transactional durable history/job storage;
    restart and crash-consistency tests; multi-process concurrency tests and
    model checking; and controlled delay, duplication, partition, failover, and
    storage-fault injection. None was available or attempted here.

15. **Catalog/course implications.** No sentence claims the catalog locator was
    retrieved or that these are official materials. The provenance records say
    the opposite. Nothing claims course credit, a pass, official-assignment
    completion, or whole-course completion.

16. **Failures and unresolved limits.** Yes. `debugging-log.md` retains the
    missing-`rg` observation, initial Python 3.6 compile failure, interpreter
    diagnosis, compatibility revision, actual test runs, and remaining model
    gaps. `INCIDENT.md` retains all four unsafe observations. There are no known
    red local tests, but no production or transfer verification is claimed.
