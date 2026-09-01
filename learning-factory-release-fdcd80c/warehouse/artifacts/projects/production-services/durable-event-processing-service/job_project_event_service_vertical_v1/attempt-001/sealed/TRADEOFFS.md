# Tradeoffs

SQLite provides a crisp transactional laboratory and durable single-host queue, but writers
serialize. `journal_mode=DELETE` favors broad filesystem compatibility over WAL concurrency.
Application-clock leases are testable yet vulnerable to wall-clock anomalies. Releasing
owned work improves shutdown latency but can reorder deliveries. Resetting attempts on
explicit DLQ requeue gives operators a fresh budget while retaining a separate audit record.
These are choices to debate, not universal defaults.
