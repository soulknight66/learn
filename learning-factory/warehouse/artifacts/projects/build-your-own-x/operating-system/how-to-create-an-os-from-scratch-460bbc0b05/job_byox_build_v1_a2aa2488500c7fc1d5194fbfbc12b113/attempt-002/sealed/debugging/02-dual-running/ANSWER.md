# Diagnosis: two running processes

The wake path must not directly make a process `RUNNING`. It changes `BLOCKED` to `READY`; only the
scheduler selects a running process. Likewise, scheduling must demote the old running slot to `READY`
before promoting the selected slot and updating `current`.

A compact regression spawns two processes, schedules one, blocks it, schedules the other, wakes the
first, and schedules repeatedly. After every operation, count `RUNNING` slots and cross-check the
`current` slot. The count must be zero or one, and it is one exactly when `current` names that slot.

The invariant is centralized ownership of the `READY` to `RUNNING` transition.
