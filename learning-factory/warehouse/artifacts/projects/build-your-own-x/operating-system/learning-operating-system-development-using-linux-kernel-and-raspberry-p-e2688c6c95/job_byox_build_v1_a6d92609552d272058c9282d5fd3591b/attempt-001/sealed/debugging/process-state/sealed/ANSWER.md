# Process-state ghost: sealed answer

The invariant is that `current_slot == -1` or it names the sole `RUNNING` process. `block` changes that process to `BLOCKED` but leaves the redundant running pointer behind. The transition must clear `current_slot` when the blocked process occupies that slot; the scheduler should not be asked to repair stale state.

Regression checks should assert immediately after `block(pid)` that the process is `BLOCKED` and `current_slot == -1`, then assert that an idle `schedule()` returns `PEBBLE_ERR_NOT_FOUND`, increments `ticks`, and leaves `pebble_check()` successful. A second ready process is useful to prove the next schedule selects it without resurrecting the blocked one.
