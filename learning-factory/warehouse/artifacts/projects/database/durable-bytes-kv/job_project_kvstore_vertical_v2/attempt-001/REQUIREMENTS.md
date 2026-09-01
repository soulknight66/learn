# Requirements

Implement `KVStore(path, *, sync=True)` with `set`, `get`, `delete`, `batch`, `keys`,
`compact`, `close`, and context-manager support. Keys and values are bytes.

Correctness requirements:

- acknowledged mutations survive close and reopen when synchronization is enabled;
- every batch is all-or-nothing during replay because it occupies one checksummed record;
- a truncated final record is treated as an interrupted append, not invented data;
- corruption in any complete record is reported rather than silently ignored;
- delete of a missing key returns false and does not append a record;
- compaction preserves logical contents and atomically replaces the old log;
- public methods remain safe under concurrent threads and reject use after close;
- keys and values are bounded so untrusted input cannot force unbounded single records.

The implementation must use only the Python standard library. Do not modify authoritative
tests to obtain a pass. Record design tradeoffs and measurements rather than fabricating them.
