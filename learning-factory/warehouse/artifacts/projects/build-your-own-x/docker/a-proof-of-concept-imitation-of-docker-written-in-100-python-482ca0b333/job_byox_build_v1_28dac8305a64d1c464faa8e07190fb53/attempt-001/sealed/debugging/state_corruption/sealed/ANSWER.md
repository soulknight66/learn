# Answer: duplicate RUNNING claims

The first `SELECT` is only an observation. Once its transaction/connection ends, both workers hold stale facts and neither owns the transition.

Begin `BEGIN IMMEDIATE` before reading. Within that same transaction, read the durable state, compare it with the caller's `expected=CREATED`, update to `RUNNING`, and commit. The second claimant waits for the writer and then observes `RUNNING`, so it raises a state-conflict error without updating.

A transition-table trigger independently rejects graph edges not in the allowed set. Insert the event in the same transaction as the state update—ideally from an `AFTER UPDATE` trigger—so rollback removes both or neither. Tests should accept either thread as the winner but require exactly one success and one durable RUNNING event.
