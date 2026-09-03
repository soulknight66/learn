# Sealed alternatives

These are design alternatives, not extra learner requirements.

1. **Snapshot backend:** replace eager `cp -a` with reflink copies when the filesystem supports them,
   with a measured fallback. This retains a directory-per-container model but introduces capability
   detection and different space guarantees.
2. **Layer backend:** store immutable content-addressed rootfs layers and mount a writable overlay per
   container. This improves reuse but requires whiteout semantics, mount cleanup, reference counts,
   and safe extraction.
3. **SQLite controller:** store containers, attempts, transitions, runner ownership, and timestamps in
   tables with database-enforced transitions. Atomic claims use an explicit immediate transaction;
   recovery can distinguish live leases from durable completed attempts.
4. **Typed runner:** retain a small CLI controller but implement namespace setup in a systems
   language using syscalls directly. This removes the self-reexec stage and permits precise
   capability and file-descriptor handling.
5. **Supervisor model:** return a container ID immediately and let a daemon own workloads. This
   enables attach, logging, restart, and reconciliation but creates authentication and daemon-lifetime
   concerns absent from the synchronous exercise.

The reference uses eager copies and directory locks because they expose the target concepts with the
fewest hidden mechanisms. That choice is educational, not a performance recommendation.
