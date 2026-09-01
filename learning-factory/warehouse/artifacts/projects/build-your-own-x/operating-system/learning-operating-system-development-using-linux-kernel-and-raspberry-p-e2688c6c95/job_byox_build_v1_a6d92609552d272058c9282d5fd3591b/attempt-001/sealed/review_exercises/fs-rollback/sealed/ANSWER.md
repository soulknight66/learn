# Filesystem rollback review: sealed answer

The snippet destroys file contents before learning that the process has no free descriptor. It then returns `PEBBLE_ERR_NO_SPACE` despite having observably truncated a file, violating the global unchanged-on-error rule.

Before truncation, open must validate the kernel/process and live state, the bounded name, all flag bits and access-mode relationships, descriptor capacity, lookup result, file capacity for a create, and open-count overflow. Only after these checks can it create or truncate the file, initialize the descriptor, and increment the open count.

A regression test writes a recognizable payload, fills all process descriptor slots, snapshots the complete kernel, then attempts `WRITE | TRUNCATE`. It must assert `PEBBLE_ERR_NO_SPACE` and `memcmp(before, after, sizeof(kernel)) == 0`. For a missing name with `CREATE` and a full file table, the result is also `PEBBLE_ERR_NO_SPACE`; neither a file record nor a descriptor may change.
