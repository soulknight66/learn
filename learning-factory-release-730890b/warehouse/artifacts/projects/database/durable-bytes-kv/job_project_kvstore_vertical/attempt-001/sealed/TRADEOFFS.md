# Tradeoffs

The design favors auditability over throughput: JSON/base64 adds space, one lock limits
concurrency, replay is O(log size), and compaction pauses writers. In exchange, batches and
corruption policy are visible without custom tooling. A binary frame would reduce space;
immutable segments plus a manifest would bound recovery and compaction pauses; a B+ tree
would enable ordered range scans at greater update complexity.
