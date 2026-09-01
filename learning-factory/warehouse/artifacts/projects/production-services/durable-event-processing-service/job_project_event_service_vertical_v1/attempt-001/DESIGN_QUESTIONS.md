# Design questions

1. Which invariants belong in SQLite constraints, and which require a transaction?
2. Exactly where can a worker die between claim, side effect, and ack? Draw every resulting state.
3. If the side effect is an email provider, who owns the idempotency key and retention window?
4. Should attempt count increase on lease expiry, explicit failure, or both? Defend the policy.
5. How do clock skew and process pauses affect leases? What would a database-authoritative clock buy?
6. What should graceful shutdown do when a prefetched lease has too little time left to finish?
7. Which metrics distinguish a poison burst, database contention, and downstream slowness?
8. How would online schema migration and rollback work with old and new workers running together?
9. What information is safe in DLQ payloads and logs? Define redaction and retention policies.
10. At what scale would you replace or partition SQLite, and what evidence triggers that decision?
