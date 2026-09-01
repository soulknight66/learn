# Expected review

**Blocker:** SELECT and UPDATE are not one claim transaction, and UPDATE has no `state='READY'`
guard. Two workers select one row, then both update and return ownership. That violates the core
lease invariant and permits concurrent side effects. Use `BEGIN IMMEDIATE`, select, and guarded
update with an asserted row count (or a single supported atomic statement).

**High:** returning `None` for every `sqlite3.Error` makes database outage indistinguishable from
an empty queue. The worker will look healthy while backlog grows. Surface a typed failure, emit
structured evidence, and apply bounded infrastructure retry outside claim semantics.

**High:** the hard-coded lease timestamp is not a duration from an authoritative/injected clock,
so it may already be expired or effectively permanent. Validate owner/duration and persist an
actual expiry. Also increment attempts and update audit timestamps in the same transaction.

Required tests: barrier-forced duplicate selection, guarded row-count loss, lock error visibility,
lease expiry/recovery, invalid owner, and rollback after injected update failure.
