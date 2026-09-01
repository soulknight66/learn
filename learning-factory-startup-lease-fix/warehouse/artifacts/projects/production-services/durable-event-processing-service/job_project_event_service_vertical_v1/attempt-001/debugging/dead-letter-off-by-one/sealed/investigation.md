# Investigation

Reproduce with a manual clock, inspect persisted `attempt_count`, and map it to when increments
occur. Query the message and DLQ in the same observation. Avoid changing backoff or test timing:
the invariant fails immediately at the second explicit failure. After patching, test attempt 1,
equality at attempt 2, explicit DLQ requeue, and restart persistence.
