# Diagnosis: two running processes

The wake path must not directly make a process `RUNNING`. It changes `BLOCKED` to `READY`; only the
scheduler selects a running process. Likewise, scheduling must demote the old running slot to `READY`
before promoting the selected slot and updating `cursor` to that slot.

A compact regression spawns two processes, schedules one, blocks it, schedules the other, wakes the
first, and schedules repeatedly. After every operation, count the `RUNNING` slots; the count must
never exceed one. Immediately after a successful schedule, the returned PID must identify the one
`RUNNING` record and `cursor` must identify that record's slot.

`cursor` is scheduling history, not a current-process field. Blocking or exiting a running process
changes its record but deliberately leaves `cursor` unchanged, so zero `RUNNING` records may coexist
with a cursor that points at a blocked, exited, reaped, or subsequently reused slot.

The invariant is centralized ownership of the `READY` to `RUNNING` transition.
