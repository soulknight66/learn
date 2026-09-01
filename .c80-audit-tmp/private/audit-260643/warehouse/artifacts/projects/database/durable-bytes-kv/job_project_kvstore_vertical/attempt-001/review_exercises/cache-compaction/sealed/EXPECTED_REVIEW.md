# Expected review

Blocking: reads and cache writes occur outside the store lock, so the dictionary races with
invalidation; delete never invalidates and can return stale authorization/session-like data.
Blocking: the non-daemon infinite thread has no cancellation or join, preventing graceful
shutdown and potentially calling compact after close. Design concern: unbounded cache memory
and negative-result caching lack policy. Request deterministic stale-read, close/shutdown,
compaction overlap, and memory-bound tests plus workload measurements.
