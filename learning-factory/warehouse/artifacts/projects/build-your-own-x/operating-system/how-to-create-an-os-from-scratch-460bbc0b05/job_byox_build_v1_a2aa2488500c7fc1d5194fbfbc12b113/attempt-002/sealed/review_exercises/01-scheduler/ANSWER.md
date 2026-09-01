# Scheduler review findings

All state-changing entry points validate the requested transition before mutation. Only scheduling
promotes `READY` to `RUNNING`; blocking or exiting the current process clears `current`; reaping alone
returns a zombie slot to `UNUSED`. Round-robin selection starts after the prior cursor and is therefore
deterministic even when table slots are reused.

The bounded PID scheme deliberately permits PID reuse. A production design would need generations or
a wider monotonic identifier to keep a stale PID from referring to a later process.
