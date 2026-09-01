# Productionization review — PARTIAL

This candidate is **not a production-ready event service**. It is the validated local baseline
under `production/implementation/`, retained so future work can evolve behind the same tests.
The correct label is `PARTIAL`, never `PRODUCTIONIZED`.

Before shipment, add an authenticated ingress/admin boundary; tenant quotas; secret and PII
handling; log redaction; an external metrics exporter and alerts; disk/inode monitoring;
backup, restore, and corruption drills; online expand/migrate/contract compatibility; process
supervision; multi-process and long-soak testing; downstream timeouts/circuit breaking; an
explicit remote idempotency agreement; load shedding; SLOs; capacity evidence; dependency and
platform patch policy; and a security/threat review. Decide whether SQLite's serialized writer
is acceptable from measured peak and recovery demand, not fashion.
