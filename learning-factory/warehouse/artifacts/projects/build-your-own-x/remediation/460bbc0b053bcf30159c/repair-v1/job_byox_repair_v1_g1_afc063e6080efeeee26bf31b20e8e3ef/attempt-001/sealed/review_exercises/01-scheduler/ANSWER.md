# Scheduler review findings

All state-changing entry points validate the requested transition before mutation. Only scheduling
promotes `READY` to `RUNNING`; blocking or exiting a process changes only that process record, and
reaping returns an exited slot to `UNUSED`. Initialization seeds `cursor` with the slot immediately
before slot 0; afterward, only a successful scheduling decision updates it. It records the slot
selected by that decision and is not cleared by block, exit, or reap. Therefore the scheduler may
have no `RUNNING` record while `cursor` still points to a blocked, exited, unused, or reused slot.
Round-robin selection starts after this historical cursor and is deterministic even when table slots
are reused. The state invariant is at most one `RUNNING` record, not an equivalence between `cursor`
and a current process.

The bounded PID scheme deliberately permits PID reuse. A production design would need generations or
a wider monotonic identifier to keep a stale PID from referring to a later process.
