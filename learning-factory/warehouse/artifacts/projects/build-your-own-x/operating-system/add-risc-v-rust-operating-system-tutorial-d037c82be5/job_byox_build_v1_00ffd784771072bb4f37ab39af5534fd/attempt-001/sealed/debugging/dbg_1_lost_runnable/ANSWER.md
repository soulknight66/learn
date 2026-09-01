# DBG-1 answer

The old runner must be made ready and enqueued as one transition before the
selection. If `pop_front()?` executes while the ready queue is empty, it returns
from `schedule` after changing the state to `Ready` but before indexing that
process in the queue; `validate` then reports `ReadyMissingFromQueue` and future
schedules remain idle. With another process ready, appending after selection
also gives publication steps an unnecessary inconsistent window.

The minimal black-box case is one process: spawn it, schedule it twice, and
expect the same PID both times plus `validate() == Ok(())`. The correct order is
take the current PID, change it to `Ready`, push it to the back, pop the oldest
ready PID, change that PID to `Running`, and set `current`.
