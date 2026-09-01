# Operator runbook

1. Check process health, filesystem free bytes/inodes, SQLite errors, queue counts, oldest
   READY age, retry rate, lease-expiry rate, and DLQ growth.
2. If backlog grows, first distinguish ingress surge, database contention, and slow downstream.
   Do not raise worker concurrency blindly: SQLite writers serialize and downstream may worsen.
3. For a poison spike, sample redacted error classes and message types; pause/reject the faulty
   producer if authorized; quarantine rather than infinite retry.
4. For shutdown, stop ingress/claims, drain within the termination budget, release owned
   work, verify no owned leases remain, then stop. Recovery waits for any abandoned lease.
5. Requeue DLQ entries only after correcting the root cause and recording operator/change IDs.
