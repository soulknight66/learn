# Incident scenarios

- **Crash after charge, before ack:** expect lease expiry and replay; verify provider/local
  idempotency key suppressed a second charge before acknowledging.
- **Database locked:** preserve the first error, inspect transaction duration and competing
  writers, reduce pressure, and avoid deleting lock/journal files.
- **Disk full:** stop admission, retain the database and journal, create space outside the data
  path, then integrity-check and restore from a tested backup if needed.
- **DLQ surge:** group by redacted error and schema version, halt the bad producer if safe, fix,
  canary a small requeue, and watch repeat failures.
- **Lease-expiry surge:** investigate pauses, clock changes, slow handlers, and lease sizing;
  never interpret redelivery alone as duplicate side effects.
